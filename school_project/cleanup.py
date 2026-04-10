import os, sys, shutil
sys.stdout.reconfigure(encoding='utf-8')

base = 'D:/LiveCode/PadhaiWithAIWithclaude03022026/school_project'

# Find and delete all corrupted files/dirs (contain private-use unicode chars)
def clean_dir(path):
    try:
        entries = os.listdir(path)
    except Exception as e:
        print(f'Cannot list {path}: {e}')
        return
    for entry in entries:
        full = os.path.join(path, entry)
        # Check for private-use unicode chars (U+E000–U+F8FF) or very long names
        if any(ord(c) > 0xE000 for c in entry) or len(entry) > 100:
            print(f'CORRUPT: {repr(entry[:60])}...')
            try:
                # Use short path via os.scandir for Windows
                with os.scandir(path) as it:
                    for item in it:
                        if item.name == entry:
                            if item.is_dir(follow_symlinks=False):
                                shutil.rmtree(item.path, ignore_errors=True)
                            else:
                                os.unlink(item.path)
                            print(f'  Deleted.')
                            break
            except Exception as e:
                print(f'  FAIL: {e}')
        elif os.path.isdir(full):
            clean_dir(full)

clean_dir(base)
print('\nDone cleaning.')

# Fix render paths in views
fixes = {
    'school_app/math_tools.html': 'school_app/math/math_tools.html',
    'school_app/school_list.html': 'school_app/admin_tools/school_list.html',
    'error_page.html': 'school_app/errors/403.html',
    'block_attendance_report.html': 'school_app/attendance/block_attendance_report.html',
    'school_daily_attendance_summary.html': 'school_app/attendance/school_daily_attendance_summary.html',
}

views_dir = base + '/school_app/views'
for fname in os.listdir(views_dir):
    if not fname.endswith('.py'):
        continue
    fpath = os.path.join(views_dir, fname)
    with open(fpath, encoding='utf-8') as f:
        content = f.read()
    new_content = content
    for old, new in fixes.items():
        new_content = new_content.replace(f"'{old}'", f"'{new}'")
        new_content = new_content.replace(f'"{old}"', f'"{new}"')
    if new_content != content:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Fixed paths in: {fname}')

print('All done.')
