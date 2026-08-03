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
            student.must_change_password = True
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
        gender = request.POST.get('gender', '').strip().upper()
        if gender not in ('M', 'F', 'O'):
            gender = ''
        if name and roll_number:
            student.name = name
            student.roll_number = roll_number
            student.gender = gender
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
    """List all students the user can see — with search, class filter, sort,
    pagination and CSV export. Scoped via get_user_students() so district
    users see their district, block users their block, etc.
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.http import HttpResponse
    from urllib.parse import urlencode
    import csv

    # ── Scope ────────────────────────────────────────────────────────────
    students_qs = (get_user_students(request.user)
                   .select_related('school', 'school__block'))
    schools_qs  = get_user_schools(request.user)

    # ── Filters (from GET) ───────────────────────────────────────────────
    q            = (request.GET.get('q', '') or '').strip()
    class_filter = (request.GET.get('class_name', '') or '').strip()
    school_id    = (request.GET.get('school', '') or '').strip()
    sort_by      = (request.GET.get('sort', 'name') or 'name').strip()

    if q:
        students_qs = students_qs.filter(
            Q(name__icontains=q) | Q(roll_number__icontains=q)
        )
    if class_filter:
        students_qs = students_qs.filter(class_name=class_filter)
    if school_id:
        try:
            students_qs = students_qs.filter(school_id=int(school_id))
        except (TypeError, ValueError):
            pass

    # Whitelisted sort keys → real ORM fields (guards against SQL-injection via ?sort=)
    sort_map = {
        'name':    ('name',),
        '-name':   ('-name',),
        'class':   ('class_name', 'name'),
        '-class':  ('-class_name', 'name'),
        'roll':    ('roll_number',),
        '-roll':   ('-roll_number',),
        'school':  ('school__name', 'name'),
        '-school': ('-school__name', 'name'),
    }
    order_fields = sort_map.get(sort_by, ('name',))
    students_qs = students_qs.order_by(*order_fields)

    # ── CSV export (short-circuits the rest) ─────────────────────────────
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="students.csv"'
        writer = csv.writer(response)
        writer.writerow(['#', 'Roll Number', 'Name', 'Class', 'Gender', 'School', 'Block'])
        for idx, s in enumerate(students_qs.iterator(chunk_size=500), start=1):
            writer.writerow([
                idx,
                s.roll_number or '',
                s.name or '',
                s.get_class_name_display() if s.class_name else '',
                s.get_gender_display() if s.gender else '',
                s.school.name if s.school_id else '',
                (s.school.block.name_english if s.school and s.school.block else ''),
            ])
        return response

    # ── Summary + pagination ─────────────────────────────────────────────
    total_students = students_qs.count()
    total_schools  = schools_qs.count()

    paginator = Paginator(students_qs, 50)  # 50 per page
    page_num  = request.GET.get('page', 1)
    try:
        page = paginator.page(page_num)
    except (PageNotAnInteger, EmptyPage):
        page = paginator.page(1)

    class_choices = dict(Student.CLASS_CHOICES)

    # Preserve current filters when building pagination links
    filter_qs = urlencode({
        k: v for k, v in {
            'q': q, 'class_name': class_filter, 'school': school_id, 'sort': sort_by,
        }.items() if v
    })

    return render(request, 'school_app/students_mgmt/school_student_list.html', {
        'page':            page,
        'total_students':  total_students,
        'total_schools':   total_schools,
        'q':               q,
        'class_filter':    class_filter,
        'school_id':       school_id,
        'sort_by':         sort_by,
        'class_choices':   class_choices,
        'schools_qs':      schools_qs.order_by('name'),
        'filter_qs':       filter_qs,
    })


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
