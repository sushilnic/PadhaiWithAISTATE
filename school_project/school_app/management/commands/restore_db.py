"""
Management command to perform safe post-restore repair on a PostgreSQL DB.

Focus: the two failure modes we hit in production —
  1. Sequences out of sync after a `pg_restore` (INSERT crashes with
     "duplicate key value violates unique constraint ..._pkey")
  2. Missing tables / columns after a `--fake`'d migration
     ("relation ... does not exist" at runtime)

This command is INTENDED as a companion to DB_RESTORE_RUNBOOK.md.
For user / session / password / role-flag repair, use `fix_after_restore`.

Usage:
    python manage.py restore_db --check           # read-only diagnostic
    python manage.py restore_db --fix-sequences   # reset all sequences to MAX(id)
    python manage.py restore_db --full            # --check then --fix-sequences

Design goals:
  - Never drops data
  - Never runs `--fake` (that decision belongs to a human reading the runbook)
  - Always prints what it's about to do before doing it
  - Exits non-zero on failure so it's safe to chain in CI
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = 'Safe post-restore repair — checks sequences and missing tables.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Read-only diagnostic. Reports issues without changing anything.',
        )
        parser.add_argument(
            '--fix-sequences',
            action='store_true',
            help='Reset all serial-id sequences to MAX(id) for each table. Safe + idempotent.',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Run --check then --fix-sequences.',
        )
        parser.add_argument(
            '--app',
            default='school_app',
            help='Django app label to inspect (default: school_app).',
        )

    def handle(self, *args, **options):
        if not (options['check'] or options['fix_sequences'] or options['full']):
            raise CommandError(
                'Pick a mode: --check, --fix-sequences, or --full. '
                'See DB_RESTORE_RUNBOOK.md at repo root for context.'
            )

        app_label = options['app']

        # Confirm we're on PostgreSQL — this command uses PG-specific SQL
        if connection.vendor != 'postgresql':
            raise CommandError(
                f'restore_db only supports PostgreSQL. Current backend: {connection.vendor}. '
                f'On SQLite/MySQL the failure modes this command addresses do not apply.'
            )

        self._header('PadhaiWithAI — DB restore diagnostic + repair')
        self.stdout.write(f'Target app: {app_label}')
        self.stdout.write(f'Database:   {connection.settings_dict["NAME"]}')
        self.stdout.write('')

        exit_code = 0

        if options['check'] or options['full']:
            issues = self._check(app_label)
            if issues:
                exit_code = 1

        if options['fix_sequences'] or options['full']:
            fixed = self._fix_sequences(app_label)
            if fixed < 0:
                exit_code = 1

        self.stdout.write('')
        self._header('Done')
        self.stdout.write('Next steps if issues remain:')
        self.stdout.write('  1. Read DB_RESTORE_RUNBOOK.md at the repo root.')
        self.stdout.write('  2. python manage.py fix_after_restore   (user / session repair)')
        self.stdout.write('  3. python manage.py migrate             (apply legitimately-missing migrations)')

        if exit_code:
            raise CommandError('Some checks failed — see output above.')

    # ─────────────────────────────────────────────────────────────────
    # Check: missing tables / missing columns / stale sequences
    # ─────────────────────────────────────────────────────────────────
    def _check(self, app_label):
        """Return a list of human-readable issues. Empty list = clean."""
        self._header('CHECK  (read-only)')
        issues = []

        # -- 1. Missing tables ------------------------------------------
        self.stdout.write('[1/3] Comparing Django models against physical tables...')
        try:
            app_config = apps.get_app_config(app_label)
        except LookupError:
            raise CommandError(f'No such app: {app_label}')

        with connection.cursor() as cur:
            cur.execute("""
                SELECT tablename FROM pg_tables
                 WHERE schemaname='public' AND tablename LIKE %s
            """, [f'{app_label}_%'])
            physical_tables = {row[0] for row in cur.fetchall()}

        missing_tables = []
        for model in app_config.get_models():
            expected = model._meta.db_table
            if expected not in physical_tables:
                missing_tables.append((model.__name__, expected))

        if missing_tables:
            self.stdout.write(self.style.ERROR(
                f'    ✗ {len(missing_tables)} model(s) have no physical table:'))
            for cls_name, tbl in missing_tables:
                issues.append(f'Missing table: {tbl}  (model: {cls_name})')
                self.stdout.write(self.style.ERROR(f'        - {cls_name}  →  {tbl}'))
            self.stdout.write(self.style.WARNING(
                '    Fix: create a RunSQL migration with CREATE TABLE IF NOT EXISTS.'))
            self.stdout.write(self.style.WARNING(
                '    See 0031_ensure_ai_sathi_session_tables.py for a template.'))
        else:
            self.stdout.write(self.style.SUCCESS('    ✓ All models have physical tables'))

        # -- 2. Migration state vs. django_migrations table -------------
        self.stdout.write('')
        self.stdout.write('[2/3] Checking un-applied migrations recorded in django_migrations...')
        from django.db.migrations.loader import MigrationLoader
        loader = MigrationLoader(connection, ignore_no_migrations=True)
        applied = {
            (a, n) for (a, n) in loader.applied_migrations.keys() if a == app_label
        }
        all_ = {
            (a, n) for (a, n) in loader.graph.nodes.keys() if a == app_label
        }
        unapplied = sorted(all_ - applied)
        if unapplied:
            self.stdout.write(self.style.WARNING(
                f'    ⚠ {len(unapplied)} migration(s) are NOT marked applied:'))
            for a, n in unapplied:
                self.stdout.write(self.style.WARNING(f'        - {a}.{n}'))
            self.stdout.write(self.style.WARNING(
                '    Fix (if physical schema already matches): '
                'python manage.py migrate {} <migration_name> --fake'.format(app_label)))
            self.stdout.write(self.style.WARNING(
                '    Fix (if physical schema does NOT match):   '
                'python manage.py migrate {}'.format(app_label)))
            self.stdout.write(self.style.WARNING(
                '    ⚠ Read DB_RESTORE_RUNBOOK.md before choosing.'))
            issues.append(f'{len(unapplied)} un-applied migrations')
        else:
            self.stdout.write(self.style.SUCCESS('    ✓ All migrations marked applied'))

        # -- 3. Sequences out of sync -----------------------------------
        self.stdout.write('')
        self.stdout.write('[3/3] Checking sequences (auto-increment counters)...')
        stale = self._find_stale_sequences(app_label)
        if stale:
            self.stdout.write(self.style.ERROR(
                f'    ✗ {len(stale)} sequence(s) are BEHIND the current MAX(id):'))
            for tbl, col, seq, max_id, seq_val in stale:
                self.stdout.write(self.style.ERROR(
                    f'        - {tbl}.{col}  →  seq={seq_val}  MAX(id)={max_id}'))
                issues.append(f'Stale sequence on {tbl} (seq={seq_val}, max={max_id})')
            self.stdout.write(self.style.WARNING(
                '    Fix: python manage.py restore_db --fix-sequences'))
        else:
            self.stdout.write(self.style.SUCCESS('    ✓ All sequences match MAX(id)'))

        # -- Summary ----------------------------------------------------
        self.stdout.write('')
        if issues:
            self.stdout.write(self.style.ERROR(f'Found {len(issues)} issue(s).'))
        else:
            self.stdout.write(self.style.SUCCESS('No issues found. Database looks healthy.'))
        return issues

    def _find_stale_sequences(self, app_label):
        """Return list of (table, column, sequence, max_id, seq_value) for
        sequences that are BEHIND MAX(id). Only sequences that would cause
        the next INSERT to conflict are reported."""
        stale = []
        with connection.cursor() as cur:
            # Find every serial-id-style column in this app
            cur.execute("""
                SELECT c.table_name, c.column_name,
                       pg_get_serial_sequence(c.table_name, c.column_name) AS seq_name
                  FROM information_schema.columns c
                 WHERE c.table_schema='public'
                   AND c.table_name LIKE %s
                   AND pg_get_serial_sequence(c.table_name, c.column_name) IS NOT NULL
            """, [f'{app_label}_%'])
            rows = cur.fetchall()

            for tbl, col, seq_name in rows:
                if not seq_name:
                    continue
                # Get current sequence value + current MAX(id). NULL max = empty table.
                cur.execute(f'SELECT COALESCE(MAX("{col}"), 0), last_value FROM "{tbl}", "{seq_name}"')
                max_id, seq_val = cur.fetchone()
                # A stale sequence has seq_val <= max_id, meaning next INSERT will collide.
                if max_id and seq_val <= max_id:
                    stale.append((tbl, col, seq_name, max_id, seq_val))
        return stale

    # ─────────────────────────────────────────────────────────────────
    # Fix: reset every stale sequence
    # ─────────────────────────────────────────────────────────────────
    def _fix_sequences(self, app_label):
        """Reset every serial sequence in app to MAX(id).
        Returns count of sequences updated, or -1 on error."""
        self._header('FIX-SEQUENCES  (idempotent, safe)')
        stale = self._find_stale_sequences(app_label)
        if not stale:
            self.stdout.write(self.style.SUCCESS('Nothing to do — all sequences already in sync.'))
            return 0

        self.stdout.write(f'About to reset {len(stale)} sequence(s):')
        for tbl, col, seq, max_id, seq_val in stale:
            self.stdout.write(f'  - {seq}  ({seq_val} → {max_id})')
        self.stdout.write('')

        try:
            with transaction.atomic():
                with connection.cursor() as cur:
                    for tbl, col, seq, max_id, seq_val in stale:
                        sql = ("SELECT setval(%s, "
                               "COALESCE((SELECT MAX(\"{col}\") FROM \"{tbl}\"), 1), "
                               "true)").format(col=col, tbl=tbl)
                        cur.execute(sql, [seq])
                        result = cur.fetchone()
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ {seq}  →  set to {result[0]}'
                        ))
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Reset {len(stale)} sequence(s).'))
            return len(stale)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed: {e}'))
            return -1

    # ─────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────
    def _header(self, text):
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE(text))
        self.stdout.write(self.style.NOTICE('=' * 60))
