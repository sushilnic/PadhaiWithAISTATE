"""
Marks management views.
"""
from .utils import *


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
            data = json.loads(request.body)
            new_marks = data.get('marks')

            mark = Marks.objects.get(id=mark_id)
            mark.marks = new_marks
            mark.save()

            log_activity(request, 'MARKS_ENTRY', f'Marks updated for {mark.student.name}: {new_marks}')
            return JsonResponse({'success': True, 'message': 'Marks updated successfully'})
        except Marks.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Mark record not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})


@login_required
def test_marks_entry(request, test_id):
    """Display and edit marks for a selected test."""
    test = get_object_or_404(Test, test_number=test_id)
    # Fetch the school associated with the logged-in user
    school = School.objects.get(admin=request.user)

    # Get all students from the logged-in user's school
    students = Student.objects.filter(school=school)

    if request.method == 'POST':
        # To store error messages
        error_messages = []

        for student in students:
            marks_value = request.POST.get(f'marks_{student.id}', '').strip()

            if marks_value:  # If marks are provided
                try:
                    # Validate numeric marks and convert them
                    marks_value = float(marks_value)

                    # Try to get or create a Marks record for the student and test
                    mark, created = Marks.objects.update_or_create(
                        student=student,
                        test=test,
                        defaults={'marks': marks_value}
                    )

                    # Optionally, you can check if the record was updated
                    if created:
                        print(f"Created new marks record for {student.name}")
                    else:
                        print(f"Updated marks record for {student.name}")

                except InvalidOperation:
                    error_messages.append(f"Invalid marks entered for {student.name}. Please enter a valid number.")
                except ValueError:
                    error_messages.append(f"Invalid marks entered for {student.name}. Please enter a valid number.")
                except IntegrityError as e:
                    # Log the error message for debugging
                    print(f"IntegrityError for {student.name}: {e}")
                    error_messages.append(f"Failed to save marks for {student.name}. Please try again.")
                except Exception as e:
                    # Log any unexpected errors
                    print(f"Unexpected error for {student.name}: {e}")
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
# Delete Marks Entry
def delete_marks(request, student_id, test_id):
    print(f"Attempting to delete marks for student_id={student_id}, test_id={test_id}")
    try:
        mark = get_object_or_404(Marks, student_id=student_id, test_id=test_id)
        mark.delete()
        return redirect('test_marks_entry', test_id=test_id)
    except Marks.DoesNotExist:
        print("No matching record found in Marks table.")
        return redirect('test_marks_entry', test_id=test_id)
