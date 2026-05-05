"""
Report views.
"""
from .utils import *
from .utils import _get_user_district
from .hierarchy import get_user_hierarchy, get_user_schools


@login_required
def test_results_analysis(request):
    # Use hierarchy-based filtering
    schools = get_user_schools(request.user)

    # Optional: Filter by selected block
    selected_block_id = request.GET.get('block', None)
    if selected_block_id:
        try:
            selected_block_id = int(selected_block_id)
        except (ValueError, TypeError):
            selected_block_id = None
    if selected_block_id:
        schools = schools.filter(block_id=selected_block_id)

    # Check if specific tests are selected, and filter accordingly
    selected_test_numbers = request.GET.getlist('test', [])
    selected_test_numbers = [test for test in selected_test_numbers if test]

    if not selected_test_numbers:
        # If no tests are selected, show results for all tests
        school_tests = Test.objects.filter(marks__student__school__in=schools).distinct().order_by('test_number')
    else:
        # If specific tests are selected, show results only for those tests
        school_tests = Test.objects.filter(test_number__in=selected_test_numbers).distinct().order_by('test_number')

    results = []

    for school in schools:
        school_data = {
            'school_name': school.name,
            'block_name': school.block.name_english if school.block else "N/A",
            'tests': []
        }

        for test in school_tests:
            # Fetch marks for this test and school
            marks = Marks.objects.filter(test=test, student__school=school)
            appeared = marks.count()  # Students who actually took the test
            max_marks = test.max_marks

            # Calculate the number of students in each percentage range
            category_0_33 = marks.filter(marks__lt=(0.33 * max_marks)).count()
            category_33_60 = marks.filter(marks__gte=(0.33 * max_marks), marks__lt=(0.60 * max_marks)).count()
            category_60_80 = marks.filter(marks__gte=(0.60 * max_marks), marks__lt=(0.80 * max_marks)).count()
            category_80_90 = marks.filter(marks__gte=(0.80 * max_marks), marks__lt=(0.90 * max_marks)).count()
            category_90_100 = marks.filter(marks__gte=(0.90 * max_marks), marks__lt=max_marks).count()
            category_100 = marks.filter(marks=max_marks).count()

            # Calculate average percentage
            if appeared > 0 and max_marks > 0:
                from django.db.models import Avg
                avg_marks_val = marks.aggregate(avg=Avg('marks'))['avg'] or 0
                avg_percentage = round(float(avg_marks_val) / float(max_marks) * 100, 1)
            else:
                avg_percentage = 0

            if appeared > 0:
                test_data = {
                    'test_name': test.test_name,
                    'appeared': appeared,
                    'avg_percentage': avg_percentage,
                    'category_0_33': f"{category_0_33}/{appeared} ({(category_0_33 / appeared * 100):.1f}%)",
                    'category_33_60': f"{category_33_60}/{appeared} ({(category_33_60 / appeared * 100):.1f}%)",
                    'category_60_80': f"{category_60_80}/{appeared} ({(category_60_80 / appeared * 100):.1f}%)",
                    'category_80_90': f"{category_80_90}/{appeared} ({(category_80_90 / appeared * 100):.1f}%)",
                    'category_90_100': f"{category_90_100}/{appeared} ({(category_90_100 / appeared * 100):.1f}%)",
                    'category_100': f"{category_100}/{appeared} ({(category_100 / appeared * 100):.1f}%)",
                }
            else:
                test_data = {
                    'test_name': test.test_name,
                    'appeared': 0,
                    'avg_percentage': 0,
                    'category_0_33': "N/A",
                    'category_33_60': "N/A",
                    'category_60_80': "N/A",
                    'category_80_90': "N/A",
                    'category_90_100': "N/A",
                    'category_100': "N/A",
                }

            school_data['tests'].append(test_data)

        results.append(school_data)

    # Get blocks and tests scoped to user's hierarchy
    hierarchy = get_user_hierarchy(request.user)
    blocks = hierarchy.get('blocks', Block.objects.none())
    tests = Test.objects.filter(marks__student__school__in=schools).distinct().order_by('test_number')
    context = {
        'results': results,
        'blocks': blocks,
        'tests':tests,
        'selected_block_id': selected_block_id,
        'selected_test_numbers': selected_test_numbers,
    }

    return render(request, 'school_app/marks/test_results_analysis.html', context)


@login_required
def test_wise_average_marks(request):
    from django.db.models import Avg, F, ExpressionWrapper, FloatField
    from django.db.models import Count, Case, When, IntegerField

    if request.user.is_district_user:
     district = get_object_or_404(District, admin=request.user)
     data = (
        Test.objects.filter(marks__student__school__block__district=district).annotate(
            avg_marks=Avg('marks__marks'),
            percentage=ExpressionWrapper(
                F('avg_marks') * 100 / F('max_marks'),
                output_field=FloatField()),
            total_students=Count('marks', distinct=True),
            category_0_and_less=Count(Case(When(marks__marks__lte=0, then=1), output_field=IntegerField())),
            category_0_33=Count(Case(When(marks__marks__gte=F('max_marks') * 0.01,marks__marks__lt=F('max_marks') * 0.33, then=1), output_field=IntegerField())),
            category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks') * 0.60, then=1), output_field=IntegerField())),
            category_60_80=Count(Case(When(marks__marks__gte=F('max_marks') * 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1), output_field=IntegerField())),
            category_80_90=Count(Case(When(marks__marks__gte=F('max_marks') * 0.80, marks__marks__lt=F('max_marks') * 0.90, then=1), output_field=IntegerField())),
            category_90_100=Count(Case(When(marks__marks__gte=F('max_marks') * 0.90, marks__marks__lt=F('max_marks'), then=1), output_field=IntegerField())),
            category_100=Count(Case(When(marks__marks=F('max_marks') , then=1), output_field=IntegerField()))
        )
        .values('test_name', 'avg_marks', 'percentage', 'total_students', 'category_0_and_less',
                'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
        .order_by('test_number')
    )
    elif request.user.is_block_user:
       block = get_object_or_404(Block, admin=request.user)
       data = (
        Test.objects.filter(marks__student__school__block_id=block.id).annotate(
            avg_marks=Avg('marks__marks'),
            percentage=ExpressionWrapper(
                F('avg_marks') * 100 / F('max_marks'),
                output_field=FloatField()),
            # Count the total number of students for each test
            total_students=Count('marks', distinct=True),  # Total number of students
            # Count the number of students with marks less than 0 (invalid or missing)
            category_0_and_less=Count(Case(When(marks__marks__lte=0, then=1), output_field=IntegerField())),
            category_0_33=Count(Case(When(marks__marks__gte=F('max_marks') * 0.01,marks__marks__lt=F('max_marks') * 0.33, then=1), output_field=IntegerField())),
            category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks') * 0.60, then=1), output_field=IntegerField())),
            category_60_80=Count(Case(When(marks__marks__gte=F('max_marks') * 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1), output_field=IntegerField())),
            category_80_90=Count(Case(When(marks__marks__gte=F('max_marks') * 0.80, marks__marks__lt=F('max_marks') * 0.90, then=1), output_field=IntegerField())),
            category_90_100=Count(Case(When(marks__marks__gte=F('max_marks') * 0.90, marks__marks__lt=F('max_marks'), then=1), output_field=IntegerField())),
            category_100=Count(Case(When(marks__marks=F('max_marks') , then=1), output_field=IntegerField()))
        )
        .values('test_name', 'avg_marks', 'percentage', 'total_students', 'category_0_and_less',
                'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
        .order_by('test_number')
    )

    elif request.user.is_school_user:
     school = get_object_or_404(School, admin=request.user)
     data = (
        Test.objects.filter(marks__student__school=school).annotate(
            avg_marks=Avg('marks__marks'),
            percentage=ExpressionWrapper(
                F('avg_marks') * 100 / F('max_marks'),
                output_field=FloatField()),
            # Count the total number of students for each test
            total_students=Count('marks', distinct=True),  # Total number of students
            # Count the number of students with marks less than 0 (invalid or missing)
            category_0_and_less=Count(Case(When(marks__marks__lte=0, then=1), output_field=IntegerField())),
            category_0_33=Count(Case(When(marks__marks__gte=F('max_marks') * 0.01,marks__marks__lt=F('max_marks') * 0.33, then=1), output_field=IntegerField())),
            category_33_60=Count(Case(When(marks__marks__gte=F('max_marks') * 0.33, marks__marks__lt=F('max_marks') * 0.60, then=1), output_field=IntegerField())),
            category_60_80=Count(Case(When(marks__marks__gte=F('max_marks') * 0.60, marks__marks__lt=F('max_marks') * 0.80, then=1), output_field=IntegerField())),
            category_80_90=Count(Case(When(marks__marks__gte=F('max_marks') * 0.80, marks__marks__lt=F('max_marks') * 0.90, then=1), output_field=IntegerField())),
            category_90_100=Count(Case(When(marks__marks__gte=F('max_marks') * 0.90, marks__marks__lt=F('max_marks'), then=1), output_field=IntegerField())),
            category_100=Count(Case(When(marks__marks=F('max_marks') , then=1), output_field=IntegerField()))
        )
        .values('test_name', 'avg_marks', 'percentage', 'total_students', 'category_0_and_less',
                'category_0_33', 'category_33_60', 'category_60_80', 'category_80_90', 'category_90_100', 'category_100')
        .order_by('test_number')
    )

    else:
     # State users, system admins, or any other role — show all tests
     data = (
        Test.objects.annotate(
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
def school_average_marks(request):
    """School average marks with hierarchy-based filtering."""
    # Filter schools based on user hierarchy
    schools = get_user_schools(request.user)

    results = []
    _district = _get_user_district(request)
    tests = (Test.objects.filter(district=_district) if _district else Test.objects.all()).order_by('test_number')

    for school in schools:
        school_data = {
            'school_name': school.name,
            'block_name': school.block.name_english if school.block else "N/A",
            'test_averages': [],
            'school_average': 0,
            'school_percentage': 0  # Add field for cumulative percentage
        }

        test_avg_list = []  # List to store test averages for cumulative calculation
        total_max_marks = 0  # Variable to store the total max marks
        total_avg_marks = 0  # Variable to store the total average marks for percentage calculation

        for test in tests:
            # Get max marks for the test
            max_marks = test.max_marks if test.max_marks else 100  # Use 100 as default if max_marks not set

            # Get the average marks for the test
            avg_marks = Marks.objects.filter(test=test, student__school=school).aggregate(avg_marks=Avg('marks'))['avg_marks']
            avg_marks = avg_marks if avg_marks is not None else 0  # Handle None values

            # Calculate the percentage for the test (avg_marks / max_marks * 100)
            #test_percentage = (avg_marks / max_marks) * 100 if max_marks > 0 else 0
            test_percentage = (float(avg_marks) / float(max_marks)) * 100 if max_marks > 0 else 0
            # Append the test details to school_data
            school_data['test_averages'].append({
                'test_name': test.subject_name,
                'average_marks': avg_marks,
                'percentage': round(test_percentage, 2)  # Round the percentage to 2 decimal places
            })

            # Add to the cumulative values
            total_max_marks += max_marks
            total_avg_marks += avg_marks

        # Calculate cumulative percentage for the school
        #school_data['school_percentage'] = (total_avg_marks / total_max_marks) * 100 if total_max_marks > 0 else 0
        school_data['school_percentage'] = (float(total_avg_marks) / float(total_max_marks)) * 100 if total_max_marks > 0 else 0
        # Calculate the cumulative average marks for the school
        school_data['school_average'] = total_avg_marks / len(tests) if tests else 0

        results.append(school_data)

    # Sort schools by overall average marks (Descending Order)
    results.sort(key=lambda x: x['school_percentage'], reverse=True)

    context = {
        'results': results,
        'tests': tests
    }
    log_activity(request, 'EDIT', f'Report accessed: School Average Marks ({len(results)} schools)')
    return render(request, 'school_app/reports/school_average.html', context)


@login_required
def top_students(request):
    """Get top performing students based on user hierarchy."""
    # Get selected test numbers (default: all tests)
    selected_test_numbers = request.GET.getlist('test', [])
    selected_test_numbers = [test for test in selected_test_numbers if test]

    # Determine total available tests
    total_tests_count = Test.objects.count() if not selected_test_numbers else len(selected_test_numbers)

    # Filter students based on user hierarchy
    schools = get_user_schools(request.user)

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

    # Determine total available tests
    total_tests_count = Test.objects.count() if not selected_test_numbers else len(selected_test_numbers)

    # Filter students based on user hierarchy
    schools = get_user_schools(request.user)

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
    # Filter based on user role
    if request.user.is_district_user:
        schools = School.objects.all()
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        schools = School.objects.filter(block=block)
    else:  # School user
        schools = School.objects.filter(admin=request.user)

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
        # District user sees all inactive schools
        schools = schools.values('id', 'name', 'admin__email', 'block__name_english', 'last_login_date')

    elif user.is_block_user:
        # Block user sees only schools in their block
        block = Block.objects.get(admin=request.user)
        schools = schools.filter(block=block).values('id', 'name', 'admin__email', 'block__name_english', 'last_login_date')

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

    # Determine the user role and filter schools accordingly
    if request.user.is_district_user:
        district = District.objects.get(admin=request.user)
        schools = School.objects.filter(block__district=district).select_related('block')
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)  # Get the block assigned to the block user
        schools = School.objects.filter(block=block)  # Filter schools in the user's block
    else:
        school = School.objects.get(admin=request.user)  # Get the school for a school user
        schools = School.objects.filter(id=school.id)  # Only the school of the logged-in user

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
        selected_test_name = Test.objects.get(test_number=selected_test).test_name
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
    # Filter based on user role
    if request.user.is_district_user:
        schools = School.objects.all()
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        schools = School.objects.filter(block=block)
    else:  # School user
        schools = School.objects.filter(admin=request.user)

    schools = schools.annotate(test_count=Count('students__marks_records__test')).filter(test_count=0)
    context = {'schools': schools}
    return render(request, 'school_app/reports/schools_without_tests.html', context)


@login_required
def schools_with_student_counts(request):
    # Filter based on user role
    if request.user.is_district_user:
        schools = School.objects.all()
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        schools = School.objects.filter(block=block)
    else:  # School user
        schools = School.objects.filter(admin=request.user)

    schools = schools.annotate(student_count=Count('students')).order_by('-student_count')

    # Calculate total students
    total_students = sum(school.student_count for school in schools)

    context = {
        'schools': schools,
        'total_students': total_students
    }
    return render(request, 'school_app/reports/schools_with_student_counts.html', context)


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
