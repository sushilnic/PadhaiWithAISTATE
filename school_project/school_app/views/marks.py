"""
Marks management views.
"""
from .utils import *

logger = logging.getLogger(__name__)


@login_required
def marks_add(request):
    if request.method == 'POST':
        form = MarksForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('marks_list')
    else:
        school = School.objects.get(admin=request.user)
        form = MarksForm()
        form.fields['student'].queryset = Student.objects.filter(school=school)
    return render(request, 'school_app/marks/marks_add.html', {'form': form})


@login_required
def marks_list(request):
    school = School.objects.get(admin=request.user)
    marks = Marks.objects.filter(student__school=school).select_related('test', 'student')  # Use select_related to reduce queries
    return render(request, 'school_app/marks/marks_list.html', {'marks': marks})


@login_required
def marks_edit(request, marks_id):
    school = School.objects.get(admin=request.user)
    marks = get_object_or_404(Marks, id=marks_id, student__school=school)

    if request.method == 'POST':
        form = MarksForm(request.POST, instance=marks)
        if form.is_valid():
            form.save()
            messages.success(request, 'Marks updated successfully!')
            return redirect('marks_list')
    else:
        form = MarksForm(instance=marks)
        # Limit student choices to only those in the current school
        form.fields['student'].queryset = Student.objects.filter(school=school)

    return render(request, 'school_app/marks/marks_edit.html', {'form': form})


@login_required
def update_marks(request, mark_id):
    """Update marks for a specific student."""
    if request.method == 'POST':
        try:
            school = get_object_or_404(School, admin=request.user)
            data = json.loads(request.body)
            new_marks = data.get('marks')

            mark = get_object_or_404(Marks, id=mark_id, student__school=school)

            if new_marks is None:
                return JsonResponse({'success': False, 'message': 'Marks value is required'})
            new_marks = float(new_marks)
            if new_marks < 0 or new_marks > mark.test.max_marks:
                return JsonResponse({'success': False, 'message': f'Marks must be between 0 and {mark.test.max_marks}'})

            mark.marks = new_marks
            mark.save()

            log_activity(request, 'MARKS_ENTRY', f'Marks updated for {mark.student.name}: {new_marks}')
            return JsonResponse({'success': True, 'message': 'Marks updated successfully'})
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'message': 'Invalid marks value'})
        except Exception:
            return JsonResponse({'success': False, 'message': 'An error occurred. Please try again.'})


@login_required
def test_marks_entry(request, test_id):
    """Display and edit marks for a selected test."""
    school = get_object_or_404(School, admin=request.user)

    # Verify the test belongs to this school's district — prevents cross-district data entry
    district = school.block.district if school.block else None
    if district:
        test = get_object_or_404(Test, test_number=test_id, district=district)
    else:
        test = get_object_or_404(Test, test_number=test_id)

    students = Student.objects.filter(school=school)

    if request.method == 'POST':
        error_messages = []

        for student in students:
            marks_value = request.POST.get(f'marks_{student.id}', '').strip()

            if marks_value:
                try:
                    marks_value = float(marks_value)

                    # Validate marks are within allowed range
                    if marks_value < 0 or marks_value > test.max_marks:
                        error_messages.append(
                            f"Marks for {student.name} must be between 0 and {test.max_marks}."
                        )
                        continue

                    mark, created = Marks.objects.update_or_create(
                        student=student,
                        test=test,
                        defaults={'marks': marks_value}
                    )
                    logger.debug('Marks %s: student_id=%s test_id=%s',
                                 'created' if created else 'updated', student.id, test_id)

                except InvalidOperation:
                    error_messages.append(f"Invalid marks entered for {student.name}. Please enter a valid number.")
                except ValueError:
                    error_messages.append(f"Invalid marks entered for {student.name}. Please enter a valid number.")
                except IntegrityError:
                    logger.error('IntegrityError saving marks: student_id=%s test_id=%s', student.id, test_id)
                    error_messages.append(f"Failed to save marks for {student.name}. Please try again.")
                except Exception:
                    logger.exception('Unexpected error saving marks: student_id=%s test_id=%s', student.id, test_id)
                    error_messages.append(f"An unexpected error occurred while saving marks for {student.name}. Please try again.")

        # If there are errors, return to the form with those errors
        if error_messages:
            # Fetch the marks again, so it persists after form submission
            student_marks = [
                {
                    'student': student,
                    'marks': Marks.objects.filter(student=student, test=test).first().marks if Marks.objects.filter(student=student, test=test).first() else ''
                }
                for student in students
            ]
            return render(request, 'school_app/marks/test_marks_entry.html', {
                'test': test,
                'student_marks': student_marks,
                'error_messages': error_messages,
            })

        # After successfully saving marks, redirect back to the same page
        log_activity(request, 'MARKS_ENTRY', f'Marks entered for test: {test.test_name}')
        return redirect('test_marks_entry', test_id=test_id)

    # Fetch marks for all students for this test
    student_marks = [
        {
            'student': student,
            'marks': Marks.objects.filter(student=student, test=test).first().marks if Marks.objects.filter(student=student, test=test).first() else ''
        }
        for student in students
    ]

    return render(request, 'school_app/marks/test_marks_entry.html', {
        'test': test,
        'student_marks': student_marks,
    })


@login_required
@require_POST
def delete_marks(request, student_id, test_id):
    school = get_object_or_404(School, admin=request.user)
    # Detect and log IDOR attempts before doing the actual delete
    if Marks.objects.filter(student_id=student_id, test_id=test_id).exclude(student__school=school).exists():
        logger.warning('SECURITY: IDOR delete_marks user=%s student_id=%s test_id=%s',
                       request.user.email, student_id, test_id)
        log_activity(request, 'SECURITY', f'Unauthorized delete_marks attempt: student_id={student_id}')
        return HttpResponseForbidden()
    mark = get_object_or_404(Marks, student_id=student_id, test_id=test_id, student__school=school)
    mark.delete()
    return redirect('test_marks_entry', test_id=test_id)
