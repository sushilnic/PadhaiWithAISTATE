"""
Attendance views.
"""
from .utils import *
from .hierarchy import get_user_hierarchy, get_user_schools


@login_required
def submit_attendance(request):
    if request.user.is_school_user:
        try:
            school = School.objects.get(admin=request.user)
            students = Student.objects.filter(school=school)
        except School.DoesNotExist:
            return redirect('error_page')

        if request.method == 'POST':
            selected_students = request.POST.getlist('absent_students')
            for student in students:
                is_present = str(student.id) not in selected_students
                try:
                    # Use filter() and update() instead of update_or_create() to avoid duplicates
                    attendance, created = Attendance.objects.get_or_create(
                        student=student,
                        date=timezone.now().date(),
                        defaults={'is_present': is_present}
                    )
                    if not created:
                        attendance.is_present = is_present
                        attendance.save()
                except IntegrityError:
                    # Log error and handle it gracefully
                    print(f"Duplicate attendance record for student {student.id} on {timezone.now().date()}")
            log_activity(request, 'ATTENDANCE', f'Attendance submitted for {school.name} ({students.count()} students)')
            return redirect('attendance_summary')

        context = {'students': students}
        return render(request, 'school_app/attendance/attendance_submit.html', context)

    return redirect('system_admin_dashboard')


@login_required
def attendance_summary(request):
    user = request.user
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            attendance_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            attendance_date = date.today()
    else:
        attendance_date = date.today()

    # Get user hierarchy info
    hierarchy = get_user_hierarchy(user)
    user_role = hierarchy['role']

    # Get schools based on user hierarchy
    schools = hierarchy['schools']

    # Get attendance for accessible schools
    attendance = list(Attendance.objects.filter(
        date=attendance_date,
        student__school__in=schools
    ).values('student__school__name').annotate(
        present_count=Count('is_present', filter=Q(is_present=True)),
        total_count=Count('student'),
        Percentage=Case(
            When(total_count=0, then=Value(0)),
            default=Count('is_present', filter=Q(is_present=True)) * 100 / Count('student'),
            output_field=FloatField()
        ),
    ).order_by('-Percentage'))

    total_present = 0
    total_students = 0
    schools_with_attendance = 0

    # Calculate summary statistics
    for record in attendance:
        total_present += record['present_count']
        total_students += record['total_count']
        if record['total_count'] > 0:
            schools_with_attendance += 1

    avg_attendance = (total_present * 100 / total_students) if total_students > 0 else 0

    total_absent = total_students - total_present

    context = {
        'attendance_summary': attendance,
        'attendance_date': attendance_date,
        'total_schools': len(attendance),
        'schools_with_attendance': schools_with_attendance,
        'total_present': total_present,
        'total_absent': total_absent,
        'total_students': total_students,
        'avg_attendance': round(avg_attendance, 2),
        'user_role': user_role,
    }
    return render(request, 'school_app/attendance/attendance_summary.html', context)


@login_required
def block_attendance_report(request):

    if request.user.is_district_user:
     blocks = Block.objects.all()
    elif request.user.is_block_user:
     blocks = Block.objects.get(admin=request.user)
    report = []

    for block in blocks:
        #schools = School.objects.get(block=block)
        schools = block.schools.all()
        total_students = 0
        total_present = 0
        total_absent = 0

        for school in schools:
            total_students += school.students.count()
            attendance_records = Attendance.objects.filter(student__school=school)
            total_present += attendance_records.filter(is_present=True).count()
            total_absent += attendance_records.filter(is_present=False).count()

        # Calculate attendance percentage
        percentage = (total_present / total_students * 100) if total_students > 0 else 0

        # Append block data to the report
        report.append({
            "block_name": block.name_english,
            "total_students": total_students,
            "total_present": total_present,
            "total_absent": total_absent,
            "percentage": f"{percentage:.2f}%",
        })

    return render(request, "school_app/attendance/block_attendance_report.html", {"report": report})


@login_required
def school_daily_attendance_summary(request):
    # Filter schools based on user role
    if request.user.is_district_user:
        schools_filter = {}
    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        schools_filter = {'student__school__block': block}
    else:  # School user
        school = School.objects.get(admin=request.user)
        schools_filter = {'student__school': school}

    # Fetch attendance data grouped by school and date
    attendance_summary = (
        Attendance.objects.filter(**schools_filter).values('student__school__name', 'date')
        .annotate(
            total_students=Count('student'),
            present_students=Count('student', filter=Q(is_present=True)),
            absent_students=Count('student', filter=Q(is_present=False)),
        )
        .order_by('date', 'student__school__name')
    )

    # Restructure data for the template
    summary_by_school_and_date = {}
    for record in attendance_summary:
        school_name = record['student__school__name']
        date = record['date']
        if date not in summary_by_school_and_date:
            summary_by_school_and_date[date] = []
        summary_by_school_and_date[date].append({
            'school_name': school_name,
            'total_students': record['total_students'],
            'present_students': record['present_students'],
            'absent_students': record['absent_students'],
        })

    return render(request, 'school_app/attendance/school_daily_attendance_summary.html', {
        'summary_by_school_and_date': summary_by_school_and_date
    })


@login_required
def block_wise_attendance_summary(request):
    """Block-wise attendance summary with hierarchy-based filtering."""
    # Filter based on user hierarchy
    schools = get_user_schools(request.user)
    attendance_queryset = Attendance.objects.filter(student__school__in=schools)

    # Get filter inputs
    start_date = parse_date(request.GET.get('start_date', ''))
    end_date = parse_date(request.GET.get('end_date', ''))

    # Fetch attendance data with optional date filtering
    if start_date and end_date:
        attendance_queryset = attendance_queryset.filter(date__range=(start_date, end_date))

    attendance_summary = (
        attendance_queryset.values('student__school__block__name_english', 'date')
        .annotate(
            total_students=Count('student'),
            present_students=Count('student', filter=Q(is_present=True)),
            absent_students=Count('student', filter=Q(is_present=False)),
        )
        .order_by('date', 'student__school__block__name_english')
    )

    # Restructure data for the template
    summary_by_block_and_date = {}
    for record in attendance_summary:
        block_name = record['student__school__block__name_english']
        date = record['date']
        if date not in summary_by_block_and_date:
            summary_by_block_and_date[date] = []
        summary_by_block_and_date[date].append({
            'block_name': block_name,
            'total_students': record['total_students'],
            'present_students': record['present_students'],
            'absent_students': record['absent_students'],
        })

    return render(request, 'school_app/attendance/block_wise_attendance_summary.html', {
        'summary_by_block_and_date': summary_by_block_and_date,
        'start_date': start_date,
        'end_date': end_date
    })


@login_required
def district_wise_attendance_summary(request):
    """District-wise attendance summary with hierarchy-based filtering."""
    # Filter based on user hierarchy
    schools = get_user_schools(request.user)
    attendance_queryset = Attendance.objects.filter(student__school__in=schools)

    # Fetch attendance data grouped by district and date
    attendance_summary = (
        attendance_queryset.values('student__school__block__district__name_english', 'date')
        .annotate(
            total_students=Count('student'),
            present_students=Count('student', filter=Q(is_present=True)),
            absent_students=Count('student', filter=Q(is_present=False)),
        )
        .order_by('date', 'student__school__block__district__name_english')
    )

    # Restructure data for template
    summary_by_district_and_date = {}
    for record in attendance_summary:
        district_name = record['student__school__block__district__name_english']
        date = record['date']
        if date not in summary_by_district_and_date:
            summary_by_district_and_date[date] = []
        summary_by_district_and_date[date].append({
            'district_name': district_name,
            'total_students': record['total_students'],
            'present_students': record['present_students'],
            'absent_students': record['absent_students'],
        })

    return render(request, 'school_app/attendance/district_wise_attendance_summary.html', {
        'summary_by_district_and_date': summary_by_district_and_date
    })


@login_required
def date_wise_attendance_summary(request):
    """Date-wise attendance summary with hierarchy-based filtering."""
    import json
    # Filter based on user hierarchy
    schools = get_user_schools(request.user)
    schools_filter = {'student__school__in': schools}

    # Fetch attendance data grouped by school and date
    attendance_summary = (
        Attendance.objects.filter(**schools_filter).values('student__school__name', 'date')
        .annotate(
            total_students=Count('student'),
            present_students=Count('student', filter=Q(is_present=True)),
            absent_students=Count('student', filter=Q(is_present=False)),
        )
        .order_by('date', 'student__school__name')
    )

    # Restructure data for easy use in the template
    summary_by_date = {}
    for record in attendance_summary:
        school_name = record['student__school__name']
        date = str(record['date'])
        if date not in summary_by_date:
            summary_by_date[date] = []
        summary_by_date[date].append({
            'school_name': school_name,
            'total_students': record['total_students'],
            'present_students': record['present_students'],
            'absent_students': record['absent_students'],
        })

    # Convert dates to JSON serializable format
    summary_data = json.dumps(summary_by_date)

    return render(request, 'school_app/attendance/date_wise_attendance_summary.html', {'summary_data': summary_data})
