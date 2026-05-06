"""
Student management views.
"""
from .utils import *
from .utils import _get_user_district
from .hierarchy import get_user_hierarchy, get_user_schools

logger = logging.getLogger(__name__)


@login_required
def student_list(request):
    school = School.objects.get(admin=request.user)
    students = Student.objects.filter(school=school)
    return render(request, 'school_app/students_mgmt/student_list.html', {'students': students})


@login_required
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save(commit=False)
            student.school = School.objects.get(admin=request.user)
            student.password = make_password('1234')
            student.save()
            log_activity(request, 'CREATE', f'Student added: {student.name} ({student.roll_number})')
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'school_app/students_mgmt/student_add.html', {'form': form})


@login_required
def student_edit(request, student_id):
    school = School.objects.get(admin=request.user)
    student = get_object_or_404(Student, id=student_id, school=school)

    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully!')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)

    return render(request, 'school_app/students_mgmt/student_edit.html', {'form': form})


@login_required
def edit_student(request, student_id):
    school = get_object_or_404(School, admin=request.user)
    student = get_object_or_404(Student, id=student_id, school=school)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        roll_number = request.POST.get('roll_number', '').strip()
        if name and roll_number:
            student.name = name
            student.roll_number = roll_number
            student.save()
            log_activity(request, 'EDIT', f'Student edited: {student.name} ({student.roll_number})')
            return redirect('dashboard')
    return render(request, 'school_app/students_mgmt/edit_student.html', {'student': student})


@login_required
@require_POST
def delete_student(request, student_id):
    school = get_object_or_404(School, admin=request.user)
    if Student.objects.filter(id=student_id).exclude(school=school).exists():
        logger.warning('SECURITY: IDOR delete_student user=%s student_id=%s',
                       request.user.email, student_id)
        log_activity(request, 'SECURITY', f'Unauthorized delete_student attempt: id={student_id}')
        return HttpResponseForbidden()
    student = get_object_or_404(Student, id=student_id, school=school)
    log_activity(request, 'DELETE', f'Student deleted: {student.name} ({student.roll_number})')
    student.delete()
    return redirect('dashboard')


@login_required
def school_student_list(request):
    """List schools and their students based on user hierarchy."""
    schools = get_user_schools(request.user)

    school_students = {}
    for school in schools:
        school_students[school] = school.students.all()

    return render(request, 'school_app/students_mgmt/school_student_list.html', {'school_students': school_students})


@login_required
def student_ranking(request):
    selected_test = request.GET.get('test', None)

    rankings = []

    if request.user.is_district_user:
        if selected_test:
            # Ranking for a specific test
            rankings = (
                Marks.objects.filter(test__test_number=selected_test)
                .select_related('student', 'student__school', 'test')
                .annotate(
                    percentage=ExpressionWrapper(
                        F('marks') * 100 / F('test__max_marks'),
                        output_field=FloatField()
                    )
                )
                .values(
                    'student__id', 'student__name', 'student__school__name',
                    'marks', 'percentage', 'test__test_name'
                )
                .order_by('-marks')
            )
        else:
            # Cumulative ranking for district user (all tests)
            rankings = (
                Marks.objects
                .select_related('student', 'student__school')
                .values('student__id', 'student__name', 'student__school__name')
                .annotate(
                    total_marks=Sum('marks'),
                    total_max_marks=Sum('test__max_marks'),
                    percentage=ExpressionWrapper(
                        (Sum('marks') * 100.0) / Sum('test__max_marks'),
                        output_field=FloatField()
                    )
                )
                .order_by('-total_marks')
            )

    elif request.user.is_block_user:
        block = Block.objects.get(admin=request.user)
        schools_in_block = School.objects.filter(block=block)
        students_in_block = Student.objects.filter(school__in=schools_in_block)

        if selected_test:
            # Ranking for a specific test within a block
            rankings = (
                Marks.objects.filter(student__in=students_in_block, test__test_number=selected_test)
                .select_related('student', 'student__school', 'test')
                .annotate(
                    percentage=ExpressionWrapper(
                        F('marks') * 100 / F('test__max_marks'),
                        output_field=FloatField()
                    )
                )
                .values(
                    'student__id', 'student__name', 'student__school__name',
                    'marks', 'percentage', 'test__test_name'
                )
                .order_by('-marks')
            )
        else:
            # Cumulative ranking for block user (all tests)
            rankings = (
                Marks.objects.filter(student__in=students_in_block)
                .select_related('student', 'student__school')
                .values('student__id', 'student__name', 'student__school__name')
                .annotate(
                    total_marks=Sum('marks'),
                    total_max_marks=Sum('test__max_marks'),
                    percentage=ExpressionWrapper(
                        (Sum('marks') * 100.0) / Sum('test__max_marks'),
                        output_field=FloatField()
                    )
                )
                .order_by('-total_marks')
            )

    else:
        return HttpResponseForbidden("You are not authorized to access this page.")

    # Get tests for dropdown scoped to user's district
    _district = _get_user_district(request)
    tests = Test.objects.filter(district=_district) if _district else Test.objects.all()

    return render(request, 'school_app/students_mgmt/student_ranking.html', {
        'rankings': rankings,
        'tests': tests,
        'selected_test': selected_test
    })


@login_required
def student_report(request):
    """Student report view with hierarchy-based filtering."""
    hierarchy = get_user_hierarchy(request.user)
    total_students = hierarchy['students'].count()

    return render(request, 'school_app/students_mgmt/student_report.html', {
        'total_students': total_students,
        'role': hierarchy['role']
    })


@login_required
@require_POST
def delete_student_mark(request, mark_id):
    school = get_object_or_404(School, admin=request.user)
    if Marks.objects.filter(id=mark_id).exclude(student__school=school).exists():
        logger.warning('SECURITY: IDOR delete_student_mark user=%s mark_id=%s',
                       request.user.email, mark_id)
        log_activity(request, 'SECURITY', f'Unauthorized delete_student_mark attempt: id={mark_id}')
        return HttpResponseForbidden()
    mark = get_object_or_404(Marks, id=mark_id, student__school=school)
    mark.delete()
    return redirect('add_marks')
