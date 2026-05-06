"""
Views for assigning question papers to students and managing test attempts.
"""
from .utils import *
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _auto_grade(paper_json, answers):
    """
    Auto-grade a student attempt.
    answers format: {"A": {"1": "B", "2": "A"}, "B": {"1": "True"}, ...}
    Returns (score, max_score, section_results).
    section_results: [{"section": "A", "title": "...", "score": x, "max": y, "questions": [...]}]
    """
    score = 0.0
    max_score = 0.0
    section_results = []

    for sec in paper_json.get('sections', []):
        sec_id = sec['section']
        marks_each = float(sec.get('marks_each', 1))
        sec_answers = answers.get(sec_id, {})
        sec_score = 0.0
        sec_max = 0.0
        q_results = []

        for q in sec.get('questions', []):
            q_no = str(q['q_no'])
            correct_raw = str(q.get('answer', '')).strip()
            student_raw = str(sec_answers.get(q_no, '')).strip()
            sec_max += marks_each

            # Normalise for comparison
            correct = correct_raw.lower().replace('.', '').replace(' ', '')
            student = student_raw.lower().replace('.', '').replace(' ', '')

            if sec_id in ('A', 'B', 'C'):
                # Exact match (MCQ, T/F, Fill-in-blank)
                earned = marks_each if (student and student == correct) else 0.0
            else:
                # Short/Long: keyword-based partial credit
                if not student:
                    earned = 0.0
                else:
                    correct_words = set(correct_raw.lower().split())
                    student_words = set(student_raw.lower().split())
                    if not correct_words:
                        earned = marks_each
                    else:
                        overlap = len(correct_words & student_words) / len(correct_words)
                        earned = round(marks_each * min(overlap, 1.0), 2)

            sec_score += earned
            q_results.append({
                'q_no': q_no,
                'question': q.get('question', ''),
                'correct_answer': correct_raw,
                'student_answer': student_raw,
                'earned': earned,
                'max': marks_each,
                'correct': (earned == marks_each and bool(student_raw)),
            })

        score += sec_score
        max_score += sec_max
        section_results.append({
            'section': sec_id,
            'title': sec.get('section_title', ''),
            'score': sec_score,
            'max': sec_max,
            'questions': q_results,
        })

    return round(score, 2), round(max_score, 2), section_results


# ─────────────────────────────────────────────────────────────────────────────
# Teacher views
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def assign_paper(request, pk):
    """Teacher assigns a question paper to a class."""
    from ..models import QuestionPaperHistory, AssignedPaper, School

    paper = get_object_or_404(QuestionPaperHistory, pk=pk, user=request.user)
    try:
        school = request.user.administered_school
    except Exception:
        messages.error(request, 'No school associated with your account.')
        return redirect('question_paper_history')

    if request.method == 'POST':
        class_name   = request.POST.get('class_name', '').strip()
        due_date_str = request.POST.get('due_date', '').strip()
        time_limit   = request.POST.get('time_limit', '').strip()
        instructions = request.POST.get('instructions', '').strip()

        if not class_name:
            messages.error(request, 'Please select a class.')
            return redirect('assign_paper', pk=pk)

        due_date = None
        if due_date_str:
            try:
                from django.utils.dateparse import parse_datetime
                due_date = parse_datetime(due_date_str)
            except Exception:
                pass

        AssignedPaper.objects.create(
            question_paper=paper,
            assigned_by=request.user,
            school=school,
            class_name=class_name,
            due_date=due_date,
            time_limit=int(time_limit) if time_limit.isdigit() else None,
            instructions=instructions,
        )
        messages.success(request, f'Paper assigned to Class {class_name} successfully!')
        return redirect('assigned_papers')

    # Build available class list from students in this school
    from ..models import Student
    classes = (Student.objects
               .filter(school=school, is_active=True)
               .values_list('class_name', flat=True)
               .distinct()
               .order_by('class_name'))

    return render(request, 'school_app/question_paper/assign_paper.html', {
        'paper': paper,
        'classes': list(classes),
        'school': school,
    })


@login_required
def assigned_papers(request):
    """Teacher sees all their assigned papers with attempt stats."""
    from ..models import AssignedPaper, Student

    try:
        school = request.user.administered_school
    except Exception:
        school = None

    assignments = (AssignedPaper.objects
                   .filter(assigned_by=request.user)
                   .select_related('question_paper')
                   .order_by('-created_at'))

    # Annotate with counts
    from django.db.models import Count, Avg, Q
    assignments = assignments.annotate(
        submitted_count=Count('attempts', filter=Q(attempts__is_submitted=True)),
    )

    return render(request, 'school_app/question_paper/assigned_papers.html', {
        'assignments': assignments,
    })


@login_required
def assignment_report(request, pk):
    """Class-wide report for one assigned paper."""
    from ..models import AssignedPaper, Student, StudentPaperAttempt

    assignment = get_object_or_404(AssignedPaper, pk=pk, assigned_by=request.user)
    paper_json = assignment.question_paper.paper_json

    students = Student.objects.filter(
        school=assignment.school,
        class_name=assignment.class_name,
        is_active=True,
    ).order_by('roll_number')

    attempts = {a.student_id: a for a in
                StudentPaperAttempt.objects.filter(assigned_paper=assignment)
                .select_related('student')}

    rows = []
    for s in students:
        attempt = attempts.get(s.pk)
        rows.append({
            'student': s,
            'attempt': attempt,
            'status': ('Submitted' if attempt and attempt.is_submitted
                       else 'In Progress' if attempt
                       else 'Not Started'),
        })

    submitted = [r for r in rows if r['attempt'] and r['attempt'].is_submitted]
    avg_score = (sum(r['attempt'].score or 0 for r in submitted) / len(submitted)
                 if submitted else 0)

    return render(request, 'school_app/question_paper/assignment_report.html', {
        'assignment': assignment,
        'rows': rows,
        'submitted_count': len(submitted),
        'total_students': len(rows),
        'avg_score': round(avg_score, 1),
        'max_score': assignment.question_paper.total_marks,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Student views
# ─────────────────────────────────────────────────────────────────────────────

def _get_student(request):
    """Return Student object from session or None."""
    from ..models import Student
    sid = request.session.get('student_id')
    if not sid:
        return None
    try:
        return Student.objects.get(pk=sid, is_active=True)
    except Student.DoesNotExist:
        return None


def _student_required_redirect(request):
    messages.error(request, 'Please login as a student.')
    return redirect('student_login')


@login_or_student_required
def student_assigned_papers(request):
    """Student sees all tests assigned to their class."""
    from ..models import AssignedPaper, StudentPaperAttempt

    student = _get_student(request)
    if not student:
        return _student_required_redirect(request)

    assignments = (AssignedPaper.objects
                   .filter(school=student.school,
                           class_name=student.class_name,
                           is_active=True)
                   .select_related('question_paper')
                   .order_by('-created_at'))

    attempts = {a.assigned_paper_id: a for a in
                StudentPaperAttempt.objects.filter(
                    student=student,
                    assigned_paper__in=assignments)}

    items = []
    for a in assignments:
        attempt = attempts.get(a.pk)
        items.append({
            'assignment': a,
            'attempt': attempt,
            'status': ('Submitted' if attempt and attempt.is_submitted
                       else 'In Progress' if attempt
                       else 'Not Started'),
            'can_take': not (attempt and attempt.is_submitted),
        })

    return render(request, 'school_app/student/assigned_papers.html', {
        'items': items,
        'student': student,
    })


@login_or_student_required
def take_paper(request, pk):
    """Student takes the test."""
    from ..models import AssignedPaper, StudentPaperAttempt

    student = _get_student(request)
    if not student:
        return _student_required_redirect(request)

    assignment = get_object_or_404(
        AssignedPaper, pk=pk,
        school=student.school, class_name=student.class_name, is_active=True
    )

    # Get or create attempt
    attempt, _ = StudentPaperAttempt.objects.get_or_create(
        assigned_paper=assignment, student=student
    )

    if attempt.is_submitted:
        return redirect('paper_result', pk=attempt.pk)

    # Save draft answers on POST (auto-save) without submitting
    if request.method == 'POST' and request.POST.get('action') == 'save_draft':
        answers = _parse_answers_from_post(request.POST, assignment.question_paper.paper_json)
        attempt.answers = answers
        attempt.save(update_fields=['answers'])
        return JsonResponse({'ok': True})

    paper_json = assignment.question_paper.paper_json

    return render(request, 'school_app/student/take_paper.html', {
        'assignment': assignment,
        'attempt': attempt,
        'paper_json': paper_json,
        'saved_answers': attempt.answers,
        'student': student,
    })


def _parse_answers_from_post(post, paper_json):
    """Build answers dict from submitted form data."""
    answers = {}
    for sec in paper_json.get('sections', []):
        sec_id = sec['section']
        answers[sec_id] = {}
        for q in sec.get('questions', []):
            q_no = str(q['q_no'])
            key = f"ans_{sec_id}_{q_no}"
            val = post.get(key, '').strip()
            answers[sec_id][q_no] = val
    return answers


@login_or_student_required
def submit_paper(request, pk):
    """Student submits the test — grades and saves result."""
    from ..models import AssignedPaper, StudentPaperAttempt

    if request.method != 'POST':
        return redirect('student_assigned_papers')

    student = _get_student(request)
    if not student:
        return _student_required_redirect(request)

    assignment = get_object_or_404(
        AssignedPaper, pk=pk,
        school=student.school, class_name=student.class_name, is_active=True
    )
    attempt, _ = StudentPaperAttempt.objects.get_or_create(
        assigned_paper=assignment, student=student
    )

    if attempt.is_submitted:
        return redirect('paper_result', pk=attempt.pk)

    paper_json = assignment.question_paper.paper_json
    answers = _parse_answers_from_post(request.POST, paper_json)
    score, max_score, _ = _auto_grade(paper_json, answers)

    attempt.answers = answers
    attempt.score = score
    attempt.max_score = max_score
    attempt.is_submitted = True
    attempt.submitted_at = timezone.now()
    attempt.save()

    messages.success(request, 'Test submitted successfully!')
    return redirect('paper_result', pk=attempt.pk)


@login_or_student_required
def paper_result(request, pk):
    """Student or teacher views the report card for one attempt."""
    from ..models import StudentPaperAttempt

    student = _get_student(request)

    # Students can only view their own result; teachers can view any
    if student:
        attempt = get_object_or_404(StudentPaperAttempt, pk=pk, student=student)
    else:
        attempt = get_object_or_404(
            StudentPaperAttempt, pk=pk,
            assigned_paper__assigned_by=request.user
        )

    paper_json = attempt.assigned_paper.question_paper.paper_json
    _, _, section_results = _auto_grade(paper_json, attempt.answers)

    return render(request, 'school_app/student/paper_result.html', {
        'attempt': attempt,
        'section_results': section_results,
        'student': attempt.student,
        'assignment': attempt.assigned_paper,
    })
