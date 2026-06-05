"""
Test management views.
"""
from django.utils.http import url_has_allowed_host_and_scheme

from .utils import *
from .utils import _get_user_district
from .hierarchy import get_user_schools
from .auth import get_logged_in_student


def _safe_referer(request, fallback='/'):
    """Return the Referer header only if it points to this site, else fallback."""
    ref = request.META.get('HTTP_REFERER', '')
    if ref and url_has_allowed_host_and_scheme(
        ref, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return ref
    return fallback


@login_required
def add_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST, request.FILES)
        if form.is_valid():
            test = form.save(commit=False)
            test.created_by = request.user  # Set the collector as the creator of the test
            # Auto-assign district for district admin users
            if request.user.is_district_user:
                try:
                    test.district = District.objects.get(admin=request.user)
                except District.DoesNotExist:
                    pass
            test.save()
            log_activity(request, 'TEST_CREATE', f'Test created: {test.test_name} ({test.subject_name})')
            messages.success(request, 'Test details have been successfully added!')
            return redirect('collector_dashboard')  # Redirect to collector dashboard or wherever appropriate
    else:
        form = TestForm()

    return render(request, 'school_app/tests/add_test.html', {'form': form})


@login_required
def activate_test(request, test_id):
    # Change `id` to `test_number`, since that is your primary key
    test = get_object_or_404(Test, test_number=test_id)
    test.is_active = True
    test.save()
    log_activity(request, 'TEST_ACTIVATE', f'Test activated: {test.test_name}')
    messages.success(request, 'Test has been activated successfully!')

    return HttpResponseRedirect(_safe_referer(request))


@login_required
def deactivate_test(request, test_id):
    test = get_object_or_404(Test, test_number=test_id)
    test.is_active = False
    test.save()
    log_activity(request, 'TEST_DEACTIVATE', f'Test deactivated: {test.test_name}')
    messages.success(request, 'Test has been deactivated successfully!')

    return HttpResponseRedirect(_safe_referer(request))

@login_required
def view_test_results(request, test_number):
    """View test results with hierarchy-based filtering."""
    test = get_object_or_404(Test, test_number=test_number)

    # Get schools based on user hierarchy
    schools = get_user_schools(request.user)
    if not schools.exists():
        return render(request, 'school_app/errors/403.html')

    # Get results for accessible schools
    results = Marks.objects.filter(test_id=test_number, student__school__in=schools).select_related('student')

    # Get sorting parameters (whitelisted — prevent ORM sort injection)
    ALLOWED_SORT = {'student__name', 'student__roll_number', 'student__class_name', 'marks'}
    sort_by = request.GET.get('sort_by', 'student__name')
    if sort_by not in ALLOWED_SORT:
        sort_by = 'student__name'
    order = request.GET.get('order', 'asc')
    if order not in ('asc', 'desc'):
        order = 'asc'

    # Adjust the ordering
    if order == 'desc':
        sort_by = f"-{sort_by}"

    # Apply the sorting to the results
    results = results.order_by(sort_by)
# Calculate percentage for each result based on max_marks from the test
    max_marks = Decimal(test.max_marks)   # Get the maximum marks for the test
    for result in results:
        result.percentage = (Decimal(result.marks) / max_marks) * 100 if max_marks > 0 else 0
   # Pass the context to the template
    context = {
        'test': test,
        'results': results,
        'current_sort_by': request.GET.get('sort_by', 'student__name'),
        'current_order': request.GET.get('order', 'asc'),
    }

    return render(request, 'school_app/tests/test_results.html', context)

@login_required
def student_tests(request):
    """List all tests available and completed by student."""
    student = get_logged_in_student(request)
    if not student:
        messages.error(request, 'Please log in to continue.')
        return redirect('student_login')

    # Get all active tests scoped to the student's district only
    student_district = student.school.block.district
    active_tests = Test.objects.filter(
        is_active=True,
        district=student_district
    ).order_by('-test_date')

    # Get completed tests (tests where student has marks)
    completed_test_ids = Marks.objects.filter(student=student).values_list('test_id', flat=True)

    # Separate tests into completed and pending
    completed_tests = []
    pending_tests = []

    for test in active_tests:
        if test.test_number in completed_test_ids:
            mark = Marks.objects.get(student=student, test=test)
            completed_tests.append({
                'test': test,
                'marks': mark.marks,
                'percentage': round(mark.percentage, 1),
                'date': mark.date
            })
        else:
            pending_tests.append(test)

    context = {
        'student': student,
        'completed_tests': completed_tests,
        'pending_tests': pending_tests,
    }

    return render(request, 'school_app/student/student_tests.html', context)

@login_required
def student_view_test(request, test_id):
    """View test details and download question paper."""
    student = get_logged_in_student(request)
    if not student:
        messages.error(request, 'Please log in to continue.')
        return redirect('student_login')

    test = get_object_or_404(Test, test_number=test_id)

    # Check if student has attempted this test
    mark = Marks.objects.filter(student=student, test=test).first()

    context = {
        'student': student,
        'test': test,
        'mark': mark,
        'percentage': round(mark.percentage, 1) if mark else None,
    }

    return render(request, 'school_app/student/student_view_test.html', context)


@login_required
def active_test_list(request):
    _district = _get_user_district(request)
    tests = (Test.objects.filter(district=_district) if _district else Test.objects.all()).order_by('test_number')
    return render(request, 'school_app/tests/active_test_list.html', {'tests': tests})
