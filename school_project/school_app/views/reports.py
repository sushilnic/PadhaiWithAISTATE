"""
Report views.
"""
from .utils import *
from .utils import _get_user_district
from .hierarchy import get_user_hierarchy, get_user_schools


@login_required
@rate_limit(max_calls=15, period=60)
def test_results_analysis(request):
    from django.db.models import Count, Avg, Case, When, F, ExpressionWrapper, FloatField

    schools = get_user_schools(request.user)

    selected_block_id = request.GET.get('block', None)
    if selected_block_id:
        try:
            selected_block_id = int(selected_block_id)
        except (ValueError, TypeError):
            selected_block_id = None
    if selected_block_id:
        schools = schools.filter(block_id=selected_block_id)

    selected_test_numbers = request.GET.getlist('test', [])
    selected_test_numbers = [t for t in selected_test_numbers if t]

    # ── Single aggregated query replaces thousands of individual queries ──
    marks_qs = Marks.objects.filter(student__school__in=schools)
    if selected_test_numbers:
        marks_qs = marks_qs.filter(test__test_number__in=selected_test_numbers)

    rows = marks_qs.values(
        'student__school__id',
        'student__school__name',
        'student__school__block__name_english',
        'test__test_name',
        'test__test_number',
        'test__max_marks',
    ).annotate(
        appeared=Count('id'),
        avg_marks=Avg('marks'),
        cat_0_33=Count(Case(When(marks__lt=F('test__max_marks') * 0.33, then=1))),
        cat_33_60=Count(Case(When(
            marks__gte=F('test__max_marks') * 0.33,
            marks__lt=F('test__max_marks') * 0.60, then=1))),
        cat_60_80=Count(Case(When(
            marks__gte=F('test__max_marks') * 0.60,
            marks__lt=F('test__max_marks') * 0.80, then=1))),
        cat_80_90=Count(Case(When(
            marks__gte=F('test__max_marks') * 0.80,
            marks__lt=F('test__max_marks') * 0.90, then=1))),
        cat_90_100=Count(Case(When(
            marks__gte=F('test__max_marks') * 0.90,
            marks__lt=F('test__max_marks'), then=1))),
        cat_100=Count(Case(When(marks=F('test__max_marks'), then=1))),
    ).order_by('student__school__name', 'test__test_number')

    # Restructure flat rows into school → tests nested structure
    def fmt(n, appeared):
        return f"{n}/{appeared} ({n / appeared * 100:.1f}%)" if appeared > 0 else "N/A"

    school_map = {}
    for row in rows:
        sid = row['student__school__id']
        if sid not in school_map:
            school_map[sid] = {
                'school_name': row['student__school__name'],
                'block_name': row['student__school__block__name_english'] or 'N/A',
                'tests': [],
            }
        appeared = row['appeared']
        max_marks = float(row['test__max_marks'] or 1)
        avg_marks = float(row['avg_marks'] or 0)
        avg_pct = round(avg_marks / max_marks * 100, 1) if max_marks > 0 else 0
        school_map[sid]['tests'].append({
            'test_name': row['test__test_name'],
            'appeared': appeared,
            'avg_percentage': avg_pct,
            'category_0_33':   fmt(row['cat_0_33'],   appeared),
            'category_33_60':  fmt(row['cat_33_60'],  appeared),
            'category_60_80':  fmt(row['cat_60_80'],  appeared),
            'category_80_90':  fmt(row['cat_80_90'],  appeared),
            'category_90_100': fmt(row['cat_90_100'], appeared),
            'category_100':    fmt(row['cat_100'],    appeared),
        })

    results = list(school_map.values())

    # ── Block-wise summary: each student counted ONCE by their avg % across all tests ──
    student_avg_rows = marks_qs.values(
        'student__id',
        'student__school__block__name_english',
        'student__school__id',
    ).annotate(
        student_avg_pct=Avg(
            ExpressionWrapper(
                F('marks') * 100.0 / F('test__max_marks'),
                output_field=FloatField()
            )
        )
    )

    from collections import defaultdict
    block_agg = defaultdict(lambda: {
        'schools': set(), 'total': 0,
        'excellence': 0, 'good': 0, 'average': 0, 'below': 0,
    })
    for row in student_avg_rows:
        bname = row['student__school__block__name_english'] or 'N/A'
        pct   = float(row['student_avg_pct'] or 0)
        block_agg[bname]['schools'].add(row['student__school__id'])
        block_agg[bname]['total'] += 1
        if   pct >= 90: block_agg[bname]['excellence'] += 1
        elif pct >= 80: block_agg[bname]['good']       += 1
        elif pct >= 60: block_agg[bname]['average']    += 1
        else:           block_agg[bname]['below']      += 1

    block_stats = []
    for bname in sorted(block_agg):
        d = block_agg[bname]
        total = d['total']
        block_stats.append({
            'block_name':     bname,
            'total_schools':  len(d['schools']),
            'total_students': total,
            'excellence':     d['excellence'],
            'good':           d['good'],
            'average':        d['average'],
            'below_avg':      d['below'],
            'excellence_pct': round(d['excellence'] / total * 100, 1) if total else 0,
            'good_pct':       round(d['good']       / total * 100, 1) if total else 0,
            'average_pct':    round(d['average']    / total * 100, 1) if total else 0,
            'below_pct':      round(d['below']      / total * 100, 1) if total else 0,
        })

    hierarchy = get_user_hierarchy(request.user)
    blocks = hierarchy.get('blocks', Block.objects.none())
    tests = Test.objects.filter(
        marks__student__school__in=schools
    ).distinct().order_by('test_number').only('test_number', 'test_name', 'subject_name')

    return render(request, 'school_app/marks/test_results_analysis.html', {
        'results': results,
        'block_stats': block_stats,
        'blocks': blocks,
        'tests': tests,
        'selected_block_id': selected_block_id,
        'selected_test_numbers': selected_test_numbers,
    })


@login_required
@rate_limit(max_calls=15, period=60)
def test_wise_average_marks(request):
    from django.db.models import Avg, F, ExpressionWrapper, FloatField
    from django.db.models import Count, Case, When, IntegerField

    if request.user.is_district_user:
        district = get_object_or_404(District, admin=request.user)
        qs = Test.objects.filter(marks__student__school__block__district=district)
    elif request.user.is_block_user:
        block = get_object_or_404(Block, admin=request.user)
        qs = Test.objects.filter(marks__student__school__block=block)
    elif request.user.is_school_user:
        school = get_object_or_404(School, admin=request.user)
        qs = Test.objects.filter(marks__student__school=school)
    else:
        qs = Test.objects.all()

    data = (
        qs.annotate(
            avg_marks=Avg('marks__marks'),
            percentage=ExpressionWrapper(
                F('avg_marks') * 100 / F('max_marks'),
                output_field=FloatField()),
            total_students=Count('marks', distinct=True),
            category_0_and_less=Count(Case(When(marks__marks__lte=0, then=1), output_field=IntegerField())),
            category_0_33=Count(Case(When(marks__marks__gte=F('max_marks') * 0.01, marks__marks__lt=F('max_marks') * 0.33, then=1), output_field=IntegerField())),
            category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks') * 0.60, then=1), output_field=IntegerField())),
            category_60_80=Count(Case(When(marks__marks__gte=F('max_marks') * 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1), output_field=IntegerField())),
            category_80_90=Count(Case(When(marks__marks__gte=F('max_marks') * 0.80, marks__marks__lt=F('max_marks') * 0.90, then=1), output_field=IntegerField())),
            category_90_100=Count(Case(When(marks__marks__gte=F('max_marks') * 0.90, marks__marks__lt=F('max_marks'), then=1), output_field=IntegerField())),
            category_100=Count(Case(When(marks__marks=F('max_marks'), then=1), output_field=IntegerField()))
        )
        .values('test_name', 'avg_marks', 'percentage', 'total_students', 'category_0_and_less',
                'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
        .order_by('test_number')
    )

    context = {'data': data}
    return render(request, 'school_app/tests/test_wise_average.html', context)


@login_required
def historical_analysis(request):
    """Test-wise analysis from archived year-suffix tables (e.g. school_app_test_2025)."""
    from django.db import connection

    # Discover available years from pg_tables
    with connection.cursor() as cur:
        cur.execute("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
              AND tablename ~ '^school_app_test_[0-9]{4}$'
            ORDER BY tablename DESC
        """)
        available_years = [r[0].replace('school_app_test_', '') for r in cur.fetchall()]

    selected_year = request.GET.get('year', available_years[0] if available_years else None)
    if selected_year not in available_years:
        selected_year = available_years[0] if available_years else None

    data = []
    if selected_year:
        t_tbl = f'school_app_test_{selected_year}'
        m_tbl = f'school_app_marks_{selected_year}'
        s_tbl = f'school_app_student_{selected_year}'
        sch_tbl = f'school_app_school_{selected_year}'
        b_tbl = f'school_app_block_{selected_year}'

        join_sql = ''
        where_sql = ''
        params = []

        try:
            if request.user.is_district_user:
                district = get_object_or_404(District, admin=request.user)
                join_sql = f'JOIN {s_tbl} s ON m.student_id=s.id JOIN {sch_tbl} sch ON s.school_id=sch.id JOIN {b_tbl} b ON sch.block_id=b.id'
                where_sql = 'WHERE b.district_id = %s'
                params = [district.id]
            elif request.user.is_block_user:
                block = get_object_or_404(Block, admin=request.user)
                join_sql = f'JOIN {s_tbl} s ON m.student_id=s.id JOIN {sch_tbl} sch ON s.school_id=sch.id'
                where_sql = 'WHERE sch.block_id = %s'
                params = [block.id]
            elif request.user.is_school_user:
                school = get_object_or_404(School, admin=request.user)
                join_sql = f'JOIN {s_tbl} s ON m.student_id=s.id'
                where_sql = 'WHERE s.school_id = %s'
                params = [school.id]
        except Exception:
            pass

        sql = f"""
            SELECT
                t.test_name, t.test_number, t.max_marks,
                COUNT(m.id)                                                         AS total_students,
                COALESCE(AVG(m.marks), 0)                                           AS avg_marks,
                CASE WHEN t.max_marks > 0
                     THEN COALESCE(AVG(m.marks), 0) * 100.0 / t.max_marks
                     ELSE 0 END                                                     AS percentage,
                COUNT(CASE WHEN m.marks <= 0                                              THEN 1 END) AS category_0_and_less,
                COUNT(CASE WHEN m.marks >= t.max_marks*0.01 AND m.marks < t.max_marks*0.33 THEN 1 END) AS category_0_33,
                COUNT(CASE WHEN m.marks >= t.max_marks*0.33 AND m.marks < t.max_marks*0.60 THEN 1 END) AS category_33_60,
                COUNT(CASE WHEN m.marks >= t.max_marks*0.60 AND m.marks < t.max_marks*0.80 THEN 1 END) AS category_60_80,
                COUNT(CASE WHEN m.marks >= t.max_marks*0.80 AND m.marks < t.max_marks*0.90 THEN 1 END) AS category_80_90,
                COUNT(CASE WHEN m.marks >= t.max_marks*0.90 AND m.marks < t.max_marks      THEN 1 END) AS category_90_100,
                COUNT(CASE WHEN m.marks = t.max_marks                                      THEN 1 END) AS category_100
            FROM {t_tbl} t
            JOIN {m_tbl} m ON m.test_id = t.test_number
            {join_sql}
            {where_sql}
            GROUP BY t.test_name, t.test_number, t.max_marks
            ORDER BY t.test_number
        """
        with connection.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            data = [dict(zip(cols, row)) for row in cur.fetchall()]

    return render(request, 'school_app/tests/historical_analysis.html', {
        'data': data,
        'available_years': available_years,
        'selected_year': selected_year,
    })


@login_required
@rate_limit(max_calls=15, period=60)
def school_average_marks(request):
    """School average marks with hierarchy-based filtering."""
    schools = get_user_schools(request.user)
    _district = _get_user_district(request)
    tests = (Test.objects.filter(district=_district) if _district else Test.objects.all()).order_by('test_number')
    tests_list = list(tests)
    n_tests = len(tests_list)

    # Single aggregated query — replaces N+1 (schools × tests individual queries)
    rows = (
        Marks.objects.filter(student__school__in=schools)
        .values(
            'student__school__id',
            'student__school__name',
            'student__school__block__name_english',
            'test__test_number',
            'test__subject_name',
            'test__max_marks',
        )
        .annotate(avg_marks=Avg('marks'))
        .order_by('student__school__name', 'test__test_number')
    )

    school_map = {}
    for row in rows:
        sid = row['student__school__id']
        if sid not in school_map:
            school_map[sid] = {
                'school_name': row['student__school__name'],
                'block_name': row['student__school__block__name_english'] or 'N/A',
                'test_averages': [],
                'total_avg_marks': 0.0,
                'total_max_marks': 0.0,
            }
        avg = float(row['avg_marks'] or 0)
        max_m = float(row['test__max_marks'] or 100)
        school_map[sid]['test_averages'].append({
            'test_name': row['test__subject_name'],
            'average_marks': avg,
            'percentage': round((avg / max_m) * 100 if max_m else 0, 2),
        })
        school_map[sid]['total_avg_marks'] += avg
        school_map[sid]['total_max_marks'] += max_m

    results = []
    for sd in school_map.values():
        sd['school_average'] = sd['total_avg_marks'] / n_tests if n_tests else 0
        sd['school_percentage'] = (sd['total_avg_marks'] / sd['total_max_marks']) * 100 if sd['total_max_marks'] else 0
        results.append(sd)

    results.sort(key=lambda x: x['school_percentage'], reverse=True)

    context = {'results': results, 'tests': tests_list}
    log_activity(request, 'EDIT', f'Report accessed: School Average Marks ({len(results)} schools)')
    return render(request, 'school_app/reports/school_average.html', context)


@login_required
def top_students(request):
    """Get top performing students based on user hierarchy."""
    # Get selected test numbers (default: all tests)
    selected_test_numbers = request.GET.getlist('test', [])
    selected_test_numbers = [test for test in selected_test_numbers if test]

    # Filter students based on user hierarchy
    schools = get_user_schools(request.user)

    # Determine total available tests scoped to the user's accessible schools
    if selected_test_numbers:
        total_tests_count = len(selected_test_numbers)
    else:
        total_tests_count = Test.objects.filter(
            marks__student__school__in=schools
        ).values('test_number').distinct().count()

    # Base query (filtered by user hierarchy)
    queryset = Marks.objects.filter(student__school__in=schools)
    if selected_test_numbers:
        queryset = queryset.filter(test__test_number__in=selected_test_numbers)

    # Aggregate data
    data = (
        queryset
        .values('student__name', 'student__school__name', 'student__school__block__name_english')
        .annotate(
            total_marks=Sum(F('marks')),
            total_max_marks=Sum(F('test__max_marks')),
            test_attempted=Count('test', distinct=True),  # Count distinct tests attempted
            percentage=ExpressionWrapper(
                (Sum(F('marks')) * 100.0) / Sum(F('test__max_marks')),
                output_field=FloatField()
            )
        )
        .filter(
            total_marks=F('total_max_marks'),  # Ensure full marks
            test_attempted=total_tests_count  # Ensure student attempted all tests
        )
        .order_by('-percentage')
    )

    # Get total maximum marks for selected tests (for percentage calculation)
    selected_tests_max_marks = Test.objects.filter(test_number__in=selected_test_numbers).aggregate(
        total_max_marks=Sum('max_marks')
    )['total_max_marks'] if selected_test_numbers else Test.objects.aggregate(
        total_max_marks=Sum('max_marks')
    )['total_max_marks']

    # Get tests for dropdown scoped to user's district
    _district = _get_user_district(request)
    tests = Test.objects.filter(district=_district) if _district else Test.objects.all()

    context = {
        'data': data,
        'tests': tests,
        'selected_test_numbers': selected_test_numbers,
        'selected_tests_max_marks': selected_tests_max_marks
    }

    log_activity(request, 'EDIT', f'Report accessed: Top Students')
    return render(request, 'school_app/reports/top_students.html', context)


@login_required
def weakest_students(request):
    """Get weakest performing students based on user hierarchy."""
    # Get selected test numbers (default: all tests)
    selected_test_numbers = request.GET.getlist('test', [])
    selected_test_numbers = [test for test in selected_test_numbers if test]

    # Filter students based on user hierarchy
    schools = get_user_schools(request.user)

    # Determine total available tests scoped to the user's accessible schools
    if selected_test_numbers:
        total_tests_count = len(selected_test_numbers)
    else:
        total_tests_count = Test.objects.filter(
            marks__student__school__in=schools
        ).values('test_number').distinct().count()

    # Base query (filtered by user hierarchy)
    queryset = Marks.objects.filter(student__school__in=schools)
    if selected_test_numbers:
        queryset = queryset.filter(test__test_number__in=selected_test_numbers)

    # Aggregate data
    data = (
        queryset
        .values('student__name', 'student__school__name', 'student__school__block__name_english')
        .annotate(
            total_marks=Sum(F('marks')),
            total_max_marks=Sum(F('test__max_marks')),
            test_attempted=Count('test', distinct=True),  # Count distinct tests attempted
            percentage=ExpressionWrapper(
                (Sum(F('marks')) * 100.0) / Sum(F('test__max_marks')),
                output_field=FloatField()
            )
        )
        .filter(
            percentage__lt=33,  # Students scoring less than 33%
            test_attempted=total_tests_count  # Ensure student attempted all tests
        )
        .order_by('student__school__block__name_english','percentage')  # Weakest students first
    )

    # Get total maximum marks for selected tests (for percentage calculation)
    selected_tests_max_marks = Test.objects.filter(test_number__in=selected_test_numbers).aggregate(
        total_max_marks=Sum('max_marks')
    )['total_max_marks'] if selected_test_numbers else Test.objects.aggregate(
        total_max_marks=Sum('max_marks')
    )['total_max_marks']

    # Get tests for dropdown — scoped to user's district
    district = _get_user_district(request)
    if district:
        tests = Test.objects.filter(district=district)
    else:
        tests = Test.objects.all()

    context = {
        'data': data,
        'tests': tests,
        'selected_test_numbers': selected_test_numbers,
        'selected_tests_max_marks': selected_tests_max_marks
    }

    log_activity(request, 'EDIT', f'Report accessed: Weakest Students')
    return render(request, 'school_app/reports/weakest_students.html', context)


@login_required
def schools_without_students(request):
    # Filter based on user role — scope strictly to caller's district / block / own school
    user = request.user
    if user.is_district_user:
        try:
            district = District.objects.get(admin=user)
            schools = School.objects.filter(block__district=district)
        except District.DoesNotExist:
            schools = School.objects.none()
    elif user.is_block_user:
        try:
            block = Block.objects.get(admin=user)
            schools = School.objects.filter(block=block)
        except Block.DoesNotExist:
            schools = School.objects.none()
    else:  # School user (or anyone else) — only their own school
        schools = School.objects.filter(admin=user)

    schools = schools.annotate(student_count=Count('students')).filter(student_count=0)
    context = {'schools': schools}
    return render(request, 'school_app/reports/schools_without_students.html', context)


@login_required
def inactive_schools(request):
    today = timezone.now().date()  # Get today's date
    user = request.user  # Logged-in user

    # Base QuerySet: Schools where admin has logged in at least once but NOT today
    schools = School.objects.filter(
        admin__last_login__isnull=False  # Admin must have logged in at least once
    ).exclude(
        admin__last_login__date=today  # Exclude admins who logged in today
    ).select_related('admin', 'block').annotate(
        last_login_date=F('admin__last_login')  # Get last login date
    ).order_by(F('last_login_date').asc(nulls_last=True))

    # Apply filters based on user role
    if user.is_district_user:
        # District user sees only inactive schools within their own district
        try:
            district = District.objects.get(admin=user)
            schools = schools.filter(block__district=district)
        except District.DoesNotExist:
            schools = schools.none()
        schools = schools.values('id', 'name', 'admin__email', 'block__name_english', 'last_login_date')

    elif user.is_block_user:
        # Block user sees only schools in their own block
        try:
            block = Block.objects.get(admin=user)
            schools = schools.filter(block=block)
        except Block.DoesNotExist:
            schools = schools.none()
        schools = schools.values('id', 'name', 'admin__email', 'block__name_english', 'last_login_date')

    else:
        # School user should only see their own school (if applicable)
        schools = schools.filter(admin=user).values('id', 'name', 'admin__email', 'block__name_english', 'last_login_date')

    context = {'schools': schools}
    return render(request, 'school_app/reports/inactive_schools.html', context)


@login_required
def schools_with_test_counts(request):
    # Retrieve tests scoped to user's district
    _district = _get_user_district(request)
    tests = Test.objects.filter(district=_district) if _district else Test.objects.all()

    # Get selected test ID from query parameters
    selected_test = request.GET.get('test_id')

    # Determine the user role and filter schools accordingly — scope strictly
    # to caller's district / block / own school. Missing records fall back to
    # an empty queryset (safer than a 404 / 500).
    user = request.user
    if user.is_district_user:
        try:
            district = District.objects.get(admin=user)
            schools = School.objects.filter(block__district=district).select_related('block')
        except District.DoesNotExist:
            schools = School.objects.none()
    elif user.is_block_user:
        try:
            block = Block.objects.get(admin=user)
            schools = School.objects.filter(block=block)
        except Block.DoesNotExist:
            schools = School.objects.none()
    else:
        # School user (or anyone else) — only their own school
        schools = School.objects.filter(admin=user)

    # Base query for schools, counting total students per school
    schools = schools.annotate(
        total_students=Count('students', distinct=True),  # Total students per school
    )

    # If a specific test is selected, calculate test count per school for that test
    if selected_test:
        # Count the distinct tests attempted for the selected test
        schools = schools.annotate(
            test_count=Count('students__marks_records', filter=Q(students__marks_records__test_id=selected_test), distinct=True),  # Count test attempts for selected test
        )
        # Get the name of the selected test
        try:
            selected_test_name = Test.objects.get(test_number=selected_test).test_name
        except Test.DoesNotExist:
            selected_test = None
            selected_test_name = None
    else:
        # If no specific test is selected, calculate total test attempts across all tests
        schools = schools.annotate(
            test_count=Count('students__marks_records__test', distinct=True),  # Count all tests attempted
        )
        selected_test_name = None
    # Calculate the difference between total students and test count (e.g., number of students not attempting a test)
    schools = schools.annotate(
        difference=F('total_students') - F('test_count')  # Difference between total students and tests attempted
    ).order_by('-total_students')  # Ordering by the total number of students

    # Compute overall totals for all schools
    total_students_all = sum(school.total_students for school in schools)
    total_tests_all = sum(school.test_count for school in schools)
    total_difference_all = total_students_all - total_tests_all

    # Add "All Schools" row to show overall data
    all_schools_row = {
        'name': 'All Schools',
        'total_students': total_students_all,
        'test_count': total_tests_all,
        'difference': total_difference_all
    }

    # Add "All Schools" data at the end of the list
    schools = list(schools) + [all_schools_row]

    context = {
        'schools': schools,
        'tests': tests,
        'selected_test': selected_test,
        'selected_test_name': selected_test_name,
        'is_district_user': request.user.is_district_user,
    }

    return render(request, 'school_app/reports/schools_with_test_counts.html', context)


@login_required
def schools_without_tests(request):
    # Filter based on user role — scope strictly to caller's district / block / own school
    user = request.user
    if user.is_district_user:
        try:
            district = District.objects.get(admin=user)
            schools = School.objects.filter(block__district=district)
        except District.DoesNotExist:
            schools = School.objects.none()
    elif user.is_block_user:
        try:
            block = Block.objects.get(admin=user)
            schools = School.objects.filter(block=block)
        except Block.DoesNotExist:
            schools = School.objects.none()
    else:  # School user (or anyone else) — only their own school
        schools = School.objects.filter(admin=user)

    schools = schools.annotate(test_count=Count('students__marks_records__test')).filter(test_count=0)
    context = {'schools': schools}
    return render(request, 'school_app/reports/schools_without_tests.html', context)


@login_required
def schools_with_student_counts(request):
    # Filter based on user role — scope strictly to caller's district / block / own school
    user = request.user
    if user.is_district_user:
        try:
            district = District.objects.get(admin=user)
            schools = School.objects.filter(block__district=district)
        except District.DoesNotExist:
            schools = School.objects.none()
    elif user.is_block_user:
        try:
            block = Block.objects.get(admin=user)
            schools = School.objects.filter(block=block)
        except Block.DoesNotExist:
            schools = School.objects.none()
    else:  # School user (or anyone else) — only their own school
        schools = School.objects.filter(admin=user)

    schools = schools.annotate(student_count=Count('students')).order_by('-student_count')

    # Calculate total students
    total_students = sum(school.student_count for school in schools)

    context = {
        'schools': schools,
        'total_students': total_students
    }
    return render(request, 'school_app/reports/schools_with_student_counts.html', context)


@login_required
def block_wise_summary(request):
    """District-admin report: per-block totals of schools and students.

    Rows: one per block in the caller's district.
    Columns: Block name, total schools, total students.
    Also shows a grand total across the district.
    """
    if not request.user.is_district_user:
        return render(request, 'school_app/errors/403.html', status=403)

    try:
        district = District.objects.get(admin=request.user)
    except District.DoesNotExist:
        messages.error(request, 'No district associated with your account.')
        return redirect('dashboard')

    # One query — count schools and students in one pass per block.
    # Reverse-relation name on Block → School is `block_schools`, and
    # the Block model has `name_english` / `name_hindi` (no plain `name`).
    blocks = (Block.objects
              .filter(district=district)
              .annotate(
                  total_schools=Count('block_schools', distinct=True),
                  total_students=Count('block_schools__students', distinct=True),
              )
              .order_by('name_english'))

    grand_total_schools  = sum(b.total_schools  for b in blocks)
    grand_total_students = sum(b.total_students for b in blocks)

    return render(request, 'school_app/reports/block_wise_summary.html', {
        'district':             district,
        'blocks':               blocks,
        'grand_total_schools':  grand_total_schools,
        'grand_total_students': grand_total_students,
    })


@login_required
def activity_logs(request):
    """Display activity logs for district admin only."""
    if not request.user.is_district_user:
        return render(request, 'school_app/errors/403.html', status=403)

    district = get_object_or_404(District, admin=request.user)
    logs = ActivityLog.objects.filter(district=district)

    # Apply filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    action_type = request.GET.get('action_type')

    if date_from:
        try:
            logs = logs.filter(timestamp__date__gte=parse_date(date_from))
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            logs = logs.filter(timestamp__date__lte=parse_date(date_to))
        except (ValueError, TypeError):
            pass
    if action_type:
        logs = logs.filter(action_type=action_type)

    from django.core.paginator import Paginator
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'district': district,
        'page_obj': page_obj,
        'action_types': ActivityLog.ACTION_TYPES,
        'date_from': date_from or '',
        'date_to': date_to or '',
        'action_type': action_type or '',
    }
    return render(request, 'school_app/reports/activity_logs.html', context)
