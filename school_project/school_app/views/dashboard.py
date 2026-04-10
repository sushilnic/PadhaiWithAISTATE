"""
Dashboard views for all user roles.
"""
from .utils import *
from .hierarchy import get_user_hierarchy, get_user_schools
from .auth import is_system_admin


@login_required
def dashboard(request):
    """School dashboard - redirects non-school users to their appropriate dashboards."""
    from django.db.models import Count, F, ExpressionWrapper, FloatField, Case, When

    # Redirect users to their appropriate dashboards based on role
    if request.user.is_system_admin:
        return redirect('system_admin_dashboard')
    if request.user.is_state_user:
        return redirect('state_dashboard')
    if request.user.is_district_user:
        return redirect('collector_dashboard')
    if request.user.is_block_user:
        return redirect('block_dashboard')

    try:
        school = School.objects.get(admin=request.user)
        school_district = school.block.district
        active_tests = Test.objects.filter(is_active=True, district=school_district)
        # Get test statistics filtered by current school
        data = list(
            Test.objects.filter(marks__student__school=school)
            .annotate(
                avg_marks=Avg('marks__marks', filter=Q(marks__student__school=school)),
                percentage=ExpressionWrapper(
                    Avg('marks__marks', filter=Q(marks__student__school=school)) * 100 / F('max_marks'),
                    output_field=FloatField()),
                category_0_33=Count(Case(When(marks__marks__lt=F('max_marks') * 0.33, marks__student__school=school, then=1), output_field=IntegerField())),
                category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks')* 0.60, marks__student__school=school, then=1), output_field=IntegerField())),
                category_60_80=Count(Case(When(marks__marks__gte=F('max_marks')* 0.60, marks__marks__lt=F('max_marks') * 0.80, marks__student__school=school, then=1), output_field=IntegerField())),
                category_80_90=Count(Case(When(marks__marks__gte=F('max_marks')* 0.80, marks__marks__lt=F('max_marks')* 0.90, marks__student__school=school, then=1), output_field=IntegerField())),
                category_90_100=Count(Case(When(marks__marks__gte=F('max_marks')* 0.90, marks__marks__lt=F('max_marks'), marks__student__school=school, then=1), output_field=IntegerField())),
                category_100=Count(Case(When(marks__marks=F('max_marks'), marks__student__school=school, then=1), output_field=IntegerField()))
            )
            .values('test_number', 'test_name', 'subject_name', 'avg_marks', 'percentage', 'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
            .order_by('-test_number')
            .distinct()
        )
        # Aggregate category counts for pie chart
        for entry in data:
            entry['categories'] = [
                entry['category_0_33'],
                entry['category_33_60'],
                entry['category_60_80'],
                entry['category_80_90'],
                entry['category_90_100'],
                entry['category_100']
            ]
        # Count distinct students with marks in this school
        total_students = Marks.objects.filter(student__school_id=school.id).values('student_id').distinct().count()
        total_students = max(total_students, 1)  # Avoid division by zero

        # Convert to list to allow multiple iterations
        result = list(Marks.objects
            .filter(student__school_id=school.id)
            .values('test__test_name', 'test__subject_name', 'test__max_marks')
            .annotate(
                avg_marks=Avg('marks'),
                percentage=ExpressionWrapper(Avg('marks') / F('test__max_marks') * 100, output_field=FloatField()),
                category_0_33_1=Count(Case(When(marks__lt=F('test__max_marks') * 0.33, then=1))),
                category_33_60_1=Count(Case(When(marks__gte=F('test__max_marks') * 0.33, marks__lt=F('test__max_marks') * 0.60, then=1))),
                category_60_80_1=Count(Case(When(marks__gte=F('test__max_marks') * 0.60, marks__lt=F('test__max_marks') * 0.80, then=1))),
                category_80_90_1=Count(Case(When(marks__gte=F('test__max_marks') * 0.80, marks__lt=F('test__max_marks') * 0.90, then=1))),
                category_90_100_1=Count(Case(When(marks__gte=F('test__max_marks') * 0.90, marks__lt=F('test__max_marks'), then=1))),
                category_100_1=Count(Case(When(marks=F('test__max_marks'), then=1))),
            )
            .order_by('-test__test_number')
        )

        # Extract chart data from result list and calculate percentages
        labels = [item['test__test_name'] for item in result]
        percentages = [item['percentage'] for item in result]
        category_0_33 = [item['category_0_33_1'] for item in result]
        category_33_60 = [item['category_33_60_1'] for item in result]
        category_60_80 = [item['category_60_80_1'] for item in result]
        category_80_90 = [item['category_80_90_1'] for item in result]
        category_90_100 = [item['category_90_100_1'] for item in result]
        category_100 = [item['category_100_1'] for item in result]
        # Calculate percentages in Python instead of in the query
        category_0_33_percent = [round(item['category_0_33_1'] / total_students * 100, 2) for item in result]
        category_33_60_percent = [round(item['category_33_60_1'] / total_students * 100, 2) for item in result]
        category_60_80_percent = [round(item['category_60_80_1'] / total_students * 100, 2) for item in result]
        category_80_90_percent = [round(item['category_80_90_1'] / total_students * 100, 2) for item in result]
        category_90_100_percent = [round(item['category_90_100_1'] / total_students * 100, 2) for item in result]
        category_100_percent = [round(item['category_100_1'] / total_students * 100, 2) for item in result]

        query = """ SELECT se.school_name_with_nic_code, s.nic_code, se.school_nic_code, se.session_year, se.total_students, se.passed_students,
        se.first_division_students, se.overall_exam_result, se.math_exam_result, se.math_above_80, se.math_above_90, se.math_100_percent,
        se.below33,se.maths_33_60,se.maths_60_80,se.maths_80_90,se.maths_90_100,se.maths_100 FROM student_exam_results se INNER JOIN school_app_school s
        ON se.school_nic_code = s.nic_code  WHERE s.nic_code =%s  order by se.session_year asc"""
        with connection.cursor() as cursor:
         cursor.execute(query,[school.nic_code])
         result = cursor.fetchall()
        # Convert result to a list of dictionaries
        results_dict = [
        {
            'school_name_with_nic_code': row[0],
            'nic_code': row[1],
            'school_nic_code': row[2],
            'session_year': row[3],
            'total_students': row[4],
            'passed_students': row[5],
            'first_division_students': row[6],
            'overall_exam_result': row[7],
            'math_exam_result': row[8],
            'math_above_80': row[9],
            'math_above_90': row[10],
            'math_100_percent': row[11],
            'below33': row[12],
            'maths_33_60': row[13],
            'maths_60_80': row[14],
            'maths_80_90': row[15],
            'maths_90_100': row[16],
            'maths_100': row[17],
        }
        for row in result
    ]

        context = {
            'school': school,
            'student_count': Student.objects.filter(school=school).count(),
            'active_tests': active_tests,
            'data': data,
            'labels': labels,
            'percentages': percentages,
            'category_0_33': category_0_33,
            'category_33_60': category_33_60,
            'category_60_80': category_60_80,
            'category_80_90': category_80_90,
            'category_90_100': category_90_100,
            'category_100': category_100,
            'results': results_dict,
            'category_0_33_percent': category_0_33_percent,
            'category_33_60_percent': category_33_60_percent,
            'category_60_80_percent': category_60_80_percent,
            'category_80_90_percent': category_80_90_percent,
            'category_90_100_percent': category_90_100_percent,
            'category_100_percent': category_100_percent
        }
    except School.DoesNotExist:
        messages.error(request, "No school found for the current user.")
        return redirect('login')

    return render(request, 'school_app/dashboards/system_admin_dashboard.html', context)


@login_required
def report_dashboard(request):
    return render(request,'school_app/dashboards/report_dashboard.html')


@login_required
def school_report(request):
    # Filter based on user role
    if request.user.is_district_user:
        base_schools = School.objects.all()
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        base_schools = School.objects.filter(block=block)
    else:  # School user
        base_schools = School.objects.filter(admin=request.user)

    # 1. Schools without student entries
    schools_without_students = base_schools.annotate(student_count=Count('students')).filter(student_count=0)

    # 2. Schools that haven't logged in (Assuming each school has a User associated)

    #inactive_schools = CustomUser.objects.filter(last_login__isnull=True, groups__name='School')
    inactive_schools = CustomUser.objects.filter(
          # Users linked to a School
        last_login__isnull=True
    )
    inactive_schools = base_schools.filter(
        admin__last_login__isnull=True
    ).values('name', 'admin__email')

    # 3. Count of test entries per school
    schools_with_test_counts = base_schools.annotate(test_count=Count('students__marks_records__test')).order_by('-test_count')

    # 4. Schools without test entries
    schools_without_tests = base_schools.annotate(test_count=Count('students__marks_records__test')).filter(test_count=0)

    # 5. Schools with student count
    schools_with_student_counts = base_schools.annotate(student_count=Count('students')).order_by('-student_count')

    context = {
        'schools_without_students': schools_without_students,
        'inactive_schools': inactive_schools,
        'schools_with_test_counts': schools_with_test_counts,
        'schools_without_tests': schools_without_tests,
        'schools_with_student_counts': schools_with_student_counts,
    }
    return render(request, 'school_app/reports/school_report.html', context)


def block_dashboard(request):
    """Block dashboard with hierarchy-based filtering."""
    if not request.user.is_block_user:
        return render(request, 'school_app/errors/403.html')

    # Get hierarchy data
    hierarchy = get_user_hierarchy(request.user)

    try:
        block = Block.objects.get(admin=request.user)
        schools = hierarchy['schools']
        students = hierarchy['students']
        tests = Test.objects.filter(district=block.district)
    except Block.DoesNotExist:
        return render(request, 'school_app/errors/403.html')
    data = get_block_data(block)  # Assume `block` is an instance of the Block model


# Aggregate category counts for pie chart

    # SECURITY AUDIT: Raw SQL uses parameterized query (%s with [block.id]) — safe from SQL injection
    sql_query = """    WITH school_avg_marks AS (    SELECT        sch.id AS school_id,        sch.block_id,  -- Add block_id to the selection
        t.test_number, t.test_name,        t.subject_name,        t.max_marks,        AVG(m.marks) AS avg_marks    FROM public.school_app_marks m    JOIN public.school_app_student s ON m.student_id = s.id
    JOIN public.school_app_school sch ON s.school_id = sch.id    JOIN public.school_app_test t ON m.test_id = t.test_number    GROUP BY sch.id, sch.block_id,  t.test_number, t.subject_name, t.max_marks  -- Include block_id in the group by
)SELECT     sam.test_name,    sam.subject_name,
    COUNT(DISTINCT CASE WHEN sam.avg_marks < sam.max_marks * 0.33 THEN sam.school_id END) AS category_0_33,
    COUNT(DISTINCT CASE WHEN sam.avg_marks >= sam.max_marks * 0.33 AND sam.avg_marks < sam.max_marks * 0.60 THEN sam.school_id END) AS category_33_60,
    COUNT(DISTINCT CASE WHEN sam.avg_marks >= sam.max_marks * 0.60 AND sam.avg_marks < sam.max_marks * 0.80 THEN sam.school_id END) AS category_60_80,
    COUNT(DISTINCT CASE WHEN sam.avg_marks >= sam.max_marks * 0.80 AND sam.avg_marks < sam.max_marks * 0.90 THEN sam.school_id END) AS category_80_90,
    COUNT(DISTINCT CASE WHEN sam.avg_marks >= sam.max_marks * 0.90 AND sam.avg_marks < sam.max_marks THEN sam.school_id END) AS category_90_100,
    COUNT(DISTINCT CASE WHEN sam.avg_marks = sam.max_marks THEN sam.school_id END) AS category_100,sam.test_number FROM school_avg_marks sam where sam.block_id = %s GROUP BY sam.block_id,sam.test_number, sam.test_name, sam.subject_name
    ORDER BY sam.block_id, sam.test_number;  """

    # Execute the query
    with connection.cursor() as cursor:
        cursor.execute(sql_query, [block.id])
        result = cursor.fetchall()

    # Convert the result into a list of dictionaries for easy access
    result_data = []
    for row in result:
        result_data.append({
            'test_name': row[0],
            'subject_name': row[1],
            'category_0_33': row[2],
            'category_33_60': row[3],
            'category_60_80': row[4],
            'category_80_90': row[5],
            'category_90_100': row[6],
            'category_100': row[7]
        })
    return render(request, 'school_app/dashboards/block_dashboard.html',{
        'data': data,
        'result': result_data,
        'total_schools': schools.count(),
        'total_students': students.count(),
        'total_tests': tests.count(),
        'tests': tests,
        'schools': schools,
        'Block_name': block.name_english,
        'results': get_previous_year_data(block),
        # 'chart_data': json.dumps(get_dataforbarchart(request))
        })


def get_dataforbarchart(request):
    """
    Get data for bar chart visualization comparing test results across categories.
    Uses parameterized queries to prevent SQL injection.
    """
    block_id = None
    query_params = []

    if request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        block_id = block.id
        block_filter = "WHERE sc.block_id = %s"
        query_params = [block_id]
    elif request.user.is_district_user:
        block_filter = "WHERE 1=1"  # Always true condition for consistent SQL structure
        query_params = []
    else:
        block_filter = "WHERE 1=1"
        query_params = []

    sql_query = f"""
    WITH student_marks AS (
        SELECT m.student_id, t.test_number, t.test_name, t.subject_name, t.max_marks,
               COALESCE(m.marks, 0) AS marks, sc.block_id
        FROM school_app_marks m
        JOIN school_app_test t ON m.test_id = t.test_number
        JOIN school_app_student s ON m.student_id = s.id
        JOIN school_app_school sc ON s.school_id = sc.id
        {block_filter} AND t.test_number IN (2, 6)
    ),
    aggregated_marks AS (
        SELECT test_number, COUNT(*) AS total_students,
            SUM(CASE WHEN marks < max_marks * 0.33 THEN 1 ELSE 0 END) AS category_0_33,
            SUM(CASE WHEN marks >= max_marks * 0.33 AND marks < max_marks * 0.60 THEN 1 ELSE 0 END) AS category_33_60,
            SUM(CASE WHEN marks >= max_marks * 0.60 AND marks < max_marks * 0.80 THEN 1 ELSE 0 END) AS category_60_80,
            SUM(CASE WHEN marks >= max_marks * 0.80 AND marks < max_marks * 0.90 THEN 1 ELSE 0 END) AS category_80_90,
            SUM(CASE WHEN marks >= max_marks * 0.90 AND marks < max_marks THEN 1 ELSE 0 END) AS category_90_100,
            SUM(CASE WHEN marks = max_marks THEN 1 ELSE 0 END) AS category_100
        FROM student_marks
        GROUP BY test_number
    )
    SELECT test_number, total_students, '' as ss,
           (category_0_33 * 100.0) / total_students AS below_33_perc,
           (category_33_60 * 100.0) / total_students AS maths_33_60_perc,
           (category_60_80 * 100.0) / total_students AS maths_60_80_perc,
           (category_80_90 * 100.0) / total_students AS maths_80_90_perc,
           (category_90_100 * 100.0) / total_students AS maths_90_100_perc,
           (category_100 * 100.0) / total_students AS maths_100_perc
    FROM aggregated_marks
    ORDER BY test_number;
    """

    with connection.cursor() as cursor:
        cursor.execute(sql_query, query_params)
        test_results = cursor.fetchall()

    # Process the first and fifth test data
    first_test = {}
    fifth_test = {}

    for row in test_results:
        test_data = {
            "below_33": row[3], "maths_33_60": row[4], "maths_60_80": row[5],
            "maths_80_90": row[6], "maths_90_100": row[7], "maths_100": row[8]
        }
        if row[0] == 2:  # First test
            first_test = test_data
        elif row[0] == 6:  # Fifth test
            fifth_test = test_data

    # Second query for previous year data
    if request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        year_block_filter = "WHERE block_id = %s"
        year_query_params = [block.id]
    else:
        year_block_filter = "WHERE 1=1"
        year_query_params = []

    query = f"""
    WITH student_count AS (
        SELECT session_year,
               SUM(total_students) AS total_students,
               SUM(below33) AS below_33,
               SUM(maths_33_60) AS maths_33_60,
               SUM(maths_60_80) AS maths_60_80,
               SUM(maths_80_90) AS maths_80_90,
               SUM(maths_90_100) AS maths_90_100,
               SUM(maths_100) AS maths_100
        FROM student_exam_results
        {year_block_filter}
        GROUP BY session_year
    )
    SELECT session_year,
           (below_33 * 100.0) / total_students AS below_33_perc,
           (maths_33_60 * 100.0) / total_students AS maths_33_60_perc,
           (maths_60_80 * 100.0) / total_students AS maths_60_80_perc,
           (maths_80_90 * 100.0) / total_students AS maths_80_90_perc,
           (maths_90_100 * 100.0) / total_students AS maths_90_100_perc,
           (maths_100 * 100.0) / total_students AS maths_100_perc
    FROM student_count
    ORDER BY session_year;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, year_query_params)
        result = cursor.fetchall()

    # Convert SQL result to dictionary
    previous_year_data = {
        row[0]: {
            "below_33": row[1], "maths_33_60": row[2], "maths_60_80": row[3],
            "maths_80_90": row[4], "maths_90_100": row[5], "maths_100": row[6]
        } for row in result
    }

    # Convert to JSON format for Chart.js
    chart_data = {
        "categories": ["Below 33%", "33-60%", "60-80%", "80-90%", "90-100%", "100%"],
        "data_2023": [float(previous_year_data.get("2022-23", {}).get(cat, 0)) for cat in first_test.keys()],
        "data_2024": [float(previous_year_data.get("2023-24", {}).get(cat, 0)) for cat in first_test.keys()],
        "first_test": [float(first_test.get(cat, 0)) for cat in first_test.keys()] if first_test else [],
        "fifth_test": [float(fifth_test.get(cat, 0)) for cat in first_test.keys()] if first_test else []
    }
    return chart_data


def get_previous_year_data(block):
    """Get previous year exam results data for a specific block."""
    query = """
        SELECT session_year, SUM(total_students) AS total_students,
               SUM(below33) AS below_33, SUM(maths_33_60) AS maths_33_60,
               SUM(maths_60_80) AS maths_60_80, SUM(maths_80_90) AS maths_80_90,
               SUM(maths_90_100) AS maths_90_100, SUM(maths_100) AS maths_100
        FROM student_exam_results
        WHERE block_id = %s
        GROUP BY session_year, block_name
        ORDER BY session_year, block_name;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [block.id])
        result = cursor.fetchall()

    return [
        {
            'session_year': row[0],
            'total_students': row[1],
            'below33': row[2],
            'maths_33_60': row[3],
            'maths_60_80': row[4],
            'maths_80_90': row[5],
            'maths_90_100': row[6],
            'maths_100': row[7],
        }
        for row in result
    ]


def get_block_data(block):
    block_sql_query = """
    WITH student_marks AS (
        SELECT
            m.student_id, t.test_number, t.test_name, t.subject_name, t.max_marks,
            COALESCE(m.marks, 0) AS marks, sc.block_id
        FROM school_app_marks m
        JOIN school_app_test t ON m.test_id = t.test_number
        JOIN school_app_student s ON m.student_id = s.id
        JOIN school_app_school sc ON s.school_id = sc.id
        JOIN school_app_block b ON sc.block_id = b.id
        WHERE b.id = %s
    ),
    aggregated_marks AS (
        SELECT
            sm.block_id, sm.test_name, sm.subject_name, sm.max_marks,sm.test_number,
            AVG(sm.marks) AS avg_marks,
            (AVG(sm.marks) * 100.0) / sm.max_marks AS percentage,
            SUM(CASE WHEN sm.marks < sm.max_marks * 0.33 THEN 1 ELSE 0 END) AS category_0_33,
            SUM(CASE WHEN sm.marks >= sm.max_marks * 0.33 AND sm.marks < sm.max_marks * 0.60 THEN 1 ELSE 0 END) AS category_33_60,
            SUM(CASE WHEN sm.marks >= sm.max_marks * 0.60 AND sm.marks < sm.max_marks * 0.80 THEN 1 ELSE 0 END) AS category_60_80,
            SUM(CASE WHEN sm.marks >= sm.max_marks * 0.80 AND sm.marks < sm.max_marks * 0.90 THEN 1 ELSE 0 END) AS category_80_90,
            SUM(CASE WHEN sm.marks >= sm.max_marks * 0.90 AND sm.marks < sm.max_marks THEN 1 ELSE 0 END) AS category_90_100,
            SUM(CASE WHEN sm.marks = sm.max_marks THEN 1 ELSE 0 END) AS category_100
        FROM student_marks sm
        GROUP BY sm.block_id, sm.test_number,sm.test_name, sm.subject_name, sm.max_marks
    )
    SELECT
        am.block_id,am.test_number, am.test_name, am.subject_name, am.avg_marks, am.percentage,
        am.category_0_33, am.category_33_60, am.category_60_80, am.category_80_90,
        am.category_90_100, am.category_100
    FROM aggregated_marks am
    ORDER BY am.block_id, am.test_number, am.percentage DESC;
    """
    # Execute the query safely with block.id as a parameter
    with connection.cursor() as cursor:
        cursor.execute(block_sql_query, [block.id])  # Pass the block ID safely as a parameter
        result = cursor.fetchall()

    # Convert the result into a list of dictionaries for easy access
    data = []
    for row in result:
        data.append({
            'test_name': row[2],
            'subject_name': row[3],
            'category_0_33': row[6],
            'category_33_60': row[7],
            'category_60_80': row[8],
            'category_80_90': row[9],
            'category_90_100': row[10],
            'category_100': row[11],
            'categories': [row[6], row[7], row[8], row[9], row[10], row[11]]
        })

    return data


# State Dashboard - Top-level state user view
@login_required
def state_dashboard(request):
    """Dashboard for state-level users showing all districts, blocks, and schools."""
    user = request.user

    # Verify state user access
    if not user.is_state_user and not user.is_system_admin:
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Get the state for this user
    try:
        state = State.objects.get(admin=user)
        state_name = state.name_english
    except State.DoesNotExist:
        # System admin can view all data
        if user.is_system_admin:
            state = None
            state_name = "All States"
        else:
            return render(request, 'school_app/errors/403.html', {'message': 'State not found for this user.'})

    # Get all data based on state
    if state:
        districts = District.objects.filter(state=state)
        blocks = Block.objects.filter(district__in=districts)
        schools = School.objects.filter(block__in=blocks)
        students = Student.objects.filter(school__in=schools)
    else:
        districts = District.objects.all()
        blocks = Block.objects.all()
        schools = School.objects.all()
        students = Student.objects.all()

    # Get test statistics
    tests = Test.objects.all()
    active_tests = tests.filter(is_active=True)

    # Get live sessions count
    live_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    # District-wise statistics for chart
    district_stats = []
    for district in districts:
        dist_blocks = blocks.filter(district=district)
        dist_schools = schools.filter(block__in=dist_blocks)
        dist_students = students.filter(school__in=dist_schools)

        # Calculate average marks for this district
        avg_marks = Marks.objects.filter(
            student__school__in=dist_schools
        ).aggregate(avg=Avg('marks'))['avg'] or 0

        district_stats.append({
            'id': district.id,
            'name': district.name_english,
            'name_hindi': district.name_hindi,
            'blocks_count': dist_blocks.count(),
            'schools_count': dist_schools.count(),
            'students_count': dist_students.count(),
            'avg_marks': round(float(avg_marks), 2) if avg_marks else 0
        })

    # Test-wise performance data for state
    if state:
        school_ids = list(schools.values_list('id', flat=True))
    else:
        school_ids = list(School.objects.values_list('id', flat=True))

    test_performance = []
    if school_ids:
        test_data = list(
            Test.objects.filter(marks__student__school_id__in=school_ids)
            .annotate(
                total_students=Count('marks__student', distinct=True),
                avg_marks=Avg('marks__marks'),
                percentage=Case(
                    When(max_marks=0, then=Value(0)),
                    default=Avg('marks__marks') * 100 / F('max_marks'),
                    output_field=FloatField()
                ),
                category_0_33=Count(Case(When(marks__marks__lt=F('max_marks') * 0.33, then=1))),
                category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks') * 0.60, then=1))),
                category_60_80=Count(Case(When(marks__marks__gte=F('max_marks') * 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1))),
                category_80_90=Count(Case(When(marks__marks__gte=F('max_marks') * 0.80, marks__marks__lt=F('max_marks') * 0.90, then=1))),
                category_90_100=Count(Case(When(marks__marks__gte=F('max_marks') * 0.90, marks__marks__lt=F('max_marks'), then=1))),
                category_100=Count(Case(When(marks__marks=F('max_marks'), then=1)))
            )
            .values('test_number', 'test_name', 'subject_name', 'total_students', 'avg_marks',
                    'percentage', 'category_0_33', 'category_33_60', 'category_60_80',
                    'category_80_90', 'category_90_100', 'category_100')
            .order_by('-test_number')
        )

        for entry in test_data:
            entry['categories'] = [
                entry['category_0_33'],
                entry['category_33_60'],
                entry['category_60_80'],
                entry['category_80_90'],
                entry['category_90_100'],
                entry['category_100']
            ]
        test_performance = test_data

    # Today's attendance summary
    today = date.today()
    today_attendance = Attendance.objects.filter(
        date=today,
        student__school__in=schools
    ).aggregate(
        present=Count('id', filter=Q(is_present=True)),
        total=Count('id')
    )

    attendance_percentage = 0
    if today_attendance['total'] > 0:
        attendance_percentage = round((today_attendance['present'] / today_attendance['total']) * 100, 2)

    context = {
        'state_name': state_name,
        'total_districts': districts.count(),
        'total_blocks': blocks.count(),
        'total_schools': schools.count(),
        'total_students': students.count(),
        'total_tests': tests.count(),
        'active_tests': active_tests.count(),
        'active_users': live_sessions.count(),
        'districts': districts,
        'district_stats': district_stats,
        'test_performance': test_performance,
        'today_present': today_attendance['present'] or 0,
        'today_total': today_attendance['total'] or 0,
        'attendance_percentage': attendance_percentage,
    }

    return render(request, 'school_app/dashboards/state_dashboard.html', context)


# Writtern by Sushil
@login_required
def collector_dashboard(request):
    """District (Collector) dashboard with hierarchy-based filtering."""
    from django.db.models import Avg, Count, Case, When, F, Value, IntegerField
    from django.db import connection
    results_dict = []

    # Get hierarchy data
    hierarchy = get_user_hierarchy(request.user)

    # Check access - allow state, district users, system admin, or Collector group
    allowed_roles = ['state', 'district', 'system_admin']
    is_collector_group = request.user.groups.filter(name='Collector').exists()

    if hierarchy['role'] not in allowed_roles and not is_collector_group:
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Determine which district to show
    district_id = request.GET.get('district_id')
    district = None
    available_districts = []

    if hierarchy['role'] == 'state' or hierarchy['role'] == 'system_admin':
        # State user or system admin - can view any district
        available_districts = list(hierarchy['districts'])
        if district_id:
            try:
                district = District.objects.get(id=district_id)
                # Verify district is in user's hierarchy
                if hierarchy['role'] == 'state' and district not in available_districts:
                    return HttpResponseForbidden("District not in your state.")
            except District.DoesNotExist:
                district = available_districts[0] if available_districts else None
        else:
            district = available_districts[0] if available_districts else None
    else:
        # District user
        try:
            district = District.objects.get(admin=request.user)
        except District.DoesNotExist:
            return render(request, 'school_app/errors/403.html')

    if not district:
        return render(request, 'school_app/errors/403.html', {'message': 'No district found.'})

    district_name = district.name_english
    blocks = Block.objects.filter(district=district)
    schools = School.objects.filter(block__in=blocks).select_related('block', 'admin')
    students = Student.objects.filter(school__in=schools)

    # District-scoped tests: new tests linked via FK; fallback OR keeps old unscoped tests with marks from this district visible
    tests = Test.objects.filter(
        Q(district=district) | Q(marks__student__school__in=schools, district__isnull=True)
    ).distinct().order_by('test_number')
    live_sessions = Session.objects.filter(expire_date__gte=timezone.now())

    data = list(
        Test.objects.filter(marks__student__school__in=schools)
        .annotate(
            avg_marks=Avg('marks__marks'),
            percentage=ExpressionWrapper(
                F('avg_marks') * 100 / F('max_marks'),
                output_field=FloatField()),
            category_0_33=Count(Case(When(marks__marks__lt=F('max_marks') * 0.33, then=1), output_field=IntegerField())),
            category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks')* 0.60, then=1), output_field=IntegerField())),
            category_60_80=Count(Case(When(marks__marks__gte=F('max_marks')* 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1), output_field=IntegerField())),
            category_80_90=Count(Case(When(marks__marks__gte=F('max_marks')* 0.80, marks__marks__lt=F('max_marks')* 0.90, then=1), output_field=IntegerField())),
            category_90_100=Count(Case(When(marks__marks__gte=F('max_marks')* 0.90, marks__marks__lt=F('max_marks'), then=1), output_field=IntegerField())),
            category_100=Count(Case(When(marks__marks=F('max_marks'), then=1), output_field=IntegerField()))
        )
        .values('test_number', 'test_name', 'subject_name', 'avg_marks', 'percentage', 'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
        .order_by('-test_number')
        .distinct()
    )
    # Aggregate category counts for pie chart
    for entry in data:
        entry['categories'] = [
            entry['category_0_33'],
            entry['category_33_60'],
            entry['category_60_80'],
            entry['category_80_90'],
            entry['category_90_100'],
            entry['category_100']
        ]
    # Define the raw SQL query - filter by collector's district schools
    school_ids = list(schools.values_list('id', flat=True))
    sql_query = """
    WITH school_avg_marks AS (
        SELECT
            sch.id AS school_id, t.test_name, t.subject_name, t.max_marks, AVG(m.marks) AS avg_marks
        FROM public.school_app_marks m
        JOIN public.school_app_student s ON m.student_id = s.id
        JOIN public.school_app_school sch ON s.school_id = sch.id
        JOIN public.school_app_test t ON m.test_id = t.test_number
        WHERE sch.id = ANY(%s)
        GROUP BY sch.id, t.test_name, t.subject_name, t.max_marks
    )
    SELECT test_name, subject_name,
        COUNT(DISTINCT CASE WHEN avg_marks < max_marks * 0.33 THEN school_id END) AS category_0_33,
        COUNT(DISTINCT CASE WHEN avg_marks >= max_marks * 0.33 AND avg_marks < max_marks * 0.60 THEN school_id END) AS category_33_60,
        COUNT(DISTINCT CASE WHEN avg_marks >= max_marks * 0.60 AND avg_marks < max_marks * 0.80 THEN school_id END) AS category_60_80,
        COUNT(DISTINCT CASE WHEN avg_marks >= max_marks * 0.80 AND avg_marks < max_marks * 0.90 THEN school_id END) AS category_80_90,
        COUNT(DISTINCT CASE WHEN avg_marks >= max_marks * 0.90 AND avg_marks < max_marks THEN school_id END) AS category_90_100,
        COUNT(DISTINCT CASE WHEN avg_marks = max_marks THEN school_id END) AS category_100
    FROM school_avg_marks
    GROUP BY test_name, subject_name
    ORDER BY test_name;
    """

    # Execute the query with school IDs as parameter
    with connection.cursor() as cursor:
        cursor.execute(sql_query, [school_ids])
        result = cursor.fetchall()

    # Convert the result into a list of dictionaries for easy access
    result_data = []
    for row in result:
        result_data.append({
            'test_name': row[0],
            'subject_name': row[1],
            'category_0_33': row[2],
            'category_33_60': row[3],
            'category_60_80': row[4],
            'category_80_90': row[5],
            'category_90_100': row[6],
            'category_100': row[7]
        })
    #Previuos year data
    block_ids = [b.id for b in blocks]
    query = """ SELECT     session_year,     SUM(total_students) AS total_students,
            SUM(below33) AS below_33,    SUM(maths_33_60) AS maths_33_60,    SUM(maths_60_80) AS maths_60_80,    SUM(maths_80_90) AS maths_80_90,    SUM(maths_90_100) AS maths_90_100,    SUM(maths_100) AS maths_100 FROM student_exam_results
                WHERE block_id = ANY(%s) GROUP BY session_year ORDER BY session_year ;"""

    with connection.cursor() as cursor:
         cursor.execute(query, [block_ids])
         result = cursor.fetchall()
        # Convert result to a list of dictionaries

    results_dict = [
        {

            'session_year': row[0],
            'total_students': row[1],
            'below33': row[2],
            'maths_33_60': row[3],
            'maths_60_80': row[4],
            'maths_80_90': row[5],
            'maths_90_100': row[6],
            'maths_100': row[7],
        }
        for row in result
    ]

    return render(request, 'school_app/dashboards/collector_dashboard.html', {
        'tests': tests,
        'schools': schools,
        'total_schools': schools.count(),
        'total_students': students.count(),
        'total_tests': tests.count(),
        'get_active_users': live_sessions.count(),
        'data': data,
        'result': result_data,
        'results': results_dict,
        'district_name': district_name,
        'available_districts': available_districts,
        'current_district': district,
        'user_role': hierarchy['role'],
    })


@user_passes_test(is_system_admin)
def system_admin_dashboard(request):
    schools = School.objects.all().annotate(
        student_count=Count('students')
    )
    context = {
        'schools': schools,
        'total_schools': schools.count(),
        'total_students': Student.objects.count(),

    }
    return render(request, 'school_app/dashboards/system_admin_dashboard.html', context)
