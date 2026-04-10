"""
Analysis dashboard and math tools views.
"""
from .utils import *
from .question_paper import get_available_books, get_book_chapters, get_book_language, load_chapter_content


@login_required
def analysis_dashboard(request):
    """Render the analysis dashboard page"""
    return render(request, 'school_app/dashboards/analysis_dashboard.html')


@login_required
def get_students(request):
    """API endpoint to get list of students"""
    try:
        # If user is a school admin, get only their school's students
        if hasattr(request.user, 'administered_school'):
            school = School.objects.get(admin=request.user)
            students = Student.objects.filter(school=school)
            print(f"Found {students.count()} students for school {school.name}")  # Debug print
        else:
            # For system admin or collector, get all students
            students = Student.objects.all()
            print(f"Found {students.count()} students total")  # Debug print

        students_data = []
        for student in students:
            students_data.append({
                'id': student.id,
                'name': student.name,
                'roll_number': student.roll_number,
                'class_name': student.class_name
            })

        print("Students data:", students_data)  # Debug print
        return JsonResponse({'students': students_data})
    except Exception as e:
        print(f"Error in get_students: {str(e)}")  # Debug print
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_student_analysis(request, student_id):
    """API endpoint to get detailed analysis for a specific student."""
    try:
        # Get the student
        if hasattr(request.user, 'administered_school'):
            # School admin can only see their school's students
            student = get_object_or_404(Student, id=student_id, school=request.user.administered_school)
        else:
            # System admin or collector can see all students
            student = get_object_or_404(Student, id=student_id)

        # Get all marks for the student
        marks = Marks.objects.filter(student=student).select_related('test')

        # Calculate class averages for each test
        test_performance = []
        for mark in marks:
            # Get class average for this test
            class_average = Marks.objects.filter(
                test=mark.test,
                student__class_name=student.class_name,
                student__school=student.school  # Only compare with students from same school
            ).aggregate(Avg('marks'))['marks__avg']

            test_performance.append({
                'test_id': mark.test.test_number,
                'test_name': mark.test.test_name,
                'subject': mark.test.subject_name,
                'date': mark.test.test_date.strftime('%Y-%m-%d') if mark.test.test_date else None,
                'marks': float(mark.marks),
                'class_average': round(float(class_average), 2) if class_average else None
            })

        # Sort by test date
        test_performance.sort(key=lambda x: x['date'] if x['date'] else '')

        # Calculate overall statistics
        all_marks = [mark.marks for mark in marks]
        average_marks = sum(all_marks) / len(all_marks) if all_marks else 0
        highest_mark = max(all_marks) if all_marks else 0
        lowest_mark = min(all_marks) if all_marks else 0

        response_data = {
            'name': student.name,
            'roll_number': student.roll_number,
            'class_name': student.class_name,
            'test_performance': test_performance,
            'statistics': {
                'average_marks': round(average_marks, 2),
                'highest_mark': round(highest_mark, 2),
                'lowest_mark': round(lowest_mark, 2),
                'total_tests': len(all_marks)
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        print(f"Error in get_student_analysis: {str(e)}")  # Debug print
        return JsonResponse({'error': str(e)}, status=500)


@login_or_student_required
def math_tools(request):
    # 1 Try to get model_type from GET
    model_type = request.GET.get("model")
    # 2 If not in GET, use session value (previously stored)
    if not model_type:
        model_type = request.session.get("model_type", "sarvam")

    # 3 Save it back to session (so it persists)
    request.session["model_type"] = model_type
    context = {
        'books': get_available_books(),
        'selected_book': request.session.get('selected_book'),
        'selected_chapter': request.session.get('selected_chapter'),
        'model_type': model_type
    }

    # If a book is selected, load its chapters
    if context['selected_book']:
        context['chapters'] = get_book_chapters(context['selected_book'])

    return render(request, 'school_app/math/math_tools.html', context)

@login_or_student_required
def load_questions(request):
    if request.method == 'POST':
        book_id = request.POST.get('book')
        chapter_id = request.POST.get('chapter')
        model_type = request.session["model_type"]

        if not book_id or not chapter_id:
            messages.error(request, 'Please select both book and chapter')
            return redirect('math_tools')

        # Store selections in session
        request.session['selected_book'] = book_id
        request.session['selected_chapter'] = chapter_id

        # Load chapter content
        content = load_chapter_content(book_id, chapter_id)

        context = {
            'books': get_available_books(),
            'selected_book': book_id,
            'chapters': get_book_chapters(book_id),
            'selected_chapter': chapter_id,
            'model_type': model_type
        }

        if content:
            context['questions'] = content.get('exercises', [])
            # Get chapter name for display
            for chapter in context['chapters']:
                if str(chapter['id']) == str(chapter_id):
                    context['chapter_name'] = chapter['name']
                    break
        else:
            messages.warning(
                request,
                f'No content found for Chapter {chapter_id} in selected book'
            )

        return render(request, 'school_app/math/math_tools.html', context)

    return redirect('math_tools')


@login_or_student_required
def solve_math(request):
    """Solve selected math questions using AI."""
    if request.method == 'POST':
        try:
            # Get questions and book ID from POST data
            questions_json = request.POST.get('questions')
            book_id = request.session.get('selected_book')
            model_type = request.session["model_type"]
            if not questions_json:
                messages.error(request, 'No questions selected')
                return redirect('math_tools')

            # Get the book's language
            language = get_book_language(book_id)

            # Parse the JSON string to get list of questions
            questions = json.loads(questions_json)

            # If questions is a string, try to parse it again
            if isinstance(questions, str):
                try:
                    questions = json.loads(questions)
                except json.JSONDecodeError:
                    pass

            solutions = []

            # Convert questions to list if it's not already
            if not isinstance(questions, list):
                questions = [questions]

            # Solve each question in the appropriate language
            for question_data in questions:
                # If question_data is a string, try to parse it as JSON
                if isinstance(question_data, str):
                    try:
                        question_data = json.loads(question_data)
                    except json.JSONDecodeError:
                        pass

                if isinstance(question_data, dict):
                    question = question_data.get('question', '')
                    img_filename = question_data.get('img', '')

                    # Construct absolute path to image
                    if img_filename:
                        img_path = os.path.join(
                            settings.BASE_DIR,
                            'school_app',
                            'static',
                            'school_app',
                            'images',
                            img_filename
                        )

                        if os.path.exists(img_path):
                            raw_solution = async_to_sync(async_solve_math_problem)(request,             question=question,
                                image_path=img_path,
                                language=language
                            )
                        else:
                            raw_solution = async_to_sync(async_solve_math_problem)(request,question=question, language=language)
                    else:
                        raw_solution = async_to_sync(async_solve_math_problem)(request,question=question, language=language)
                else:
                    question = question_data
                    raw_solution = async_to_sync(async_solve_math_problem)(request,question=question, language=language)

                # Format the solution using the SolutionFormatter
                formatted_solution = SolutionFormatter.format_solution(raw_solution)
                #print(formatted_solution)
                # formatted_question = SolutionFormatter.format_question(
                #     question if 'question' in locals() else question_data
                # )

                # For template display, use the static URL path for images
                static_img_url = img_filename if 'img_filename' in locals() else None

                solutions.append({
                    'question': question,
                    'img': static_img_url,
                    'solution': formatted_solution
                })

            # Get chapter name for display
            chapter_id = request.session.get('selected_chapter')
            chapter_name = None
            if book_id and chapter_id:
                chapters = get_book_chapters(book_id)
                for chapter in chapters:
                    if str(chapter['id']) == str(chapter_id):
                        chapter_name = chapter['name']
                        break

            context = {
                'solutions': solutions,
                'language': language,
                'original_book': book_id,
                'original_chapter': chapter_id,
                'chapter_name': chapter_name,
                'model_type':model_type
            }

            return render(request, 'school_app/math/solutions.html', context)

        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")  # Debug print
            error_msg = 'Invalid question data received' if language == 'English' else 'अमान्य प्रश्न डेटा प्राप्त हुआ'
            messages.error(request, error_msg)
        except Exception as e:
            print(f"Error processing request: {e}")  # Debug print
            error_msg = f'Error solving questions: {str(e)}' if language == 'English' else f'प्रश्नों को हल करने में त्रुटि: {str(e)}'
            messages.error(request, error_msg)

    return redirect('math_tools')

#10-10-2025
@login_or_student_required
@require_http_methods(["POST"])
def solve_again(request):
    """
    View function to re-solve a single math question.
    """
    if request.method == 'POST':
        try:
            question = request.POST.get('question')
            img_filename = request.POST.get('img')
            book_id = request.session.get('selected_book')
            model_type = request.session["model_type"]
            if not question:
                messages.error(request, 'No question provided to solve again.')
                return redirect('math_tools')

            language = get_book_language(book_id)
            raw_solution = ''

            if img_filename:
                img_path = os.path.join(
                    settings.BASE_DIR,
                    'school_app',
                    'static',
                    'school_app',
                    'images',
                    img_filename
                )
                if os.path.exists(img_path):
                    raw_solution = async_to_sync(async_solve_math_problem)(request,
                        question=question,
                        image_path=img_path,
                        language=language
                    )
                else:
                    raw_solution = async_to_sync(async_solve_math_problem)(request,question=question, language=language)
            else:
                raw_solution = async_to_sync(async_solve_math_problem)(request,question=question, language=language)

            formatted_solution = SolutionFormatter.format_solution(raw_solution)

            solutions = [{
                'question': question,
                'img': img_filename,
                'solution': formatted_solution
            }]

            context = {
                'solutions': solutions,
                'language': language,
                'original_book': book_id,
                'original_chapter': request.session.get('selected_chapter'),
                'model_type':model_type
            }

            return render(request, 'school_app/math/solutions.html', context)

        except Exception as e:
            messages.error(request, f"An error occurred while trying to solve the question again: {str(e)}")
            return redirect('math_tools')

    return redirect('math_tools')


@login_or_student_required
def generate_math(request):
    """
    View function to handle math question generation with language support.
    """
    try:
        # Get questions from POST data
        questions_json = request.POST.get('questions')
        book_id = request.session.get('selected_book')
        model_type = request.session["model_type"]

        if not questions_json:
            messages.error(request, 'No questions selected')
            return redirect('math_tools')

        # Get the book's language
        language = get_book_language(book_id)

        # Error messages based on language
        error_messages = {
            'Hindi': {
                'no_questions': 'कोई प्रश्न नहीं चुना गया है। कृपया मुख्य पृष्ठ से प्रश्न चुनें।',
                'generating': 'प्रश्न उत्पन्न किए जा रहे हैं... कृपया प्रतीक्षा करें',
                'error': 'प्रश्न उत्पन्न करने में त्रुटि:',
                'invalid_data': 'अमान्य प्रश्न डेटा प्राप्त हुआ'
            },
            'English': {
                'no_questions': 'No questions selected. Please select questions from the main page.',
                'generating': 'Generating questions... please wait',
                'error': 'Error generating questions:',
                'invalid_data': 'Invalid question data received'
            }
        }

        # Parse the JSON string to get list of questions
        questions = json.loads(questions_json)

        if request.method == 'POST':
            difficulty = request.POST.get('difficulty', 'Same Level')
            num_questions = int(request.POST.get('num_questions', 5))
            question_type = request.POST.get('question_type', 'Same as Original')

            # Calculate distribution of questions
            num_selected = len(questions)
            base_count = num_questions // num_selected
            remainder = num_questions % num_selected
            distribution = [base_count] * num_selected
            for i in range(remainder):
                distribution[i] += 1

            all_generated_questions = []

            # Generate questions using the book's language
            for i, (question, count) in enumerate(zip(questions, distribution)):
                try:
                    generated_content = async_to_sync(async_generate_similar_questions)(request,
                        question=question,
                        difficulty=difficulty,
                        num_questions=count,
                        language=language,  # Use book's language
                        question_type=question_type
                    )
                    all_generated_questions.append(generated_content)

                except Exception as e:
                    print(f"Error generating questions: {e}")
                    messages.error(request, f"Error generating questions: {str(e)}")
                    return redirect('login')

            # Combine all generated questions
            combined_content = "\n\n".join(all_generated_questions)
            formatted_content = SolutionFormatter.format_solution(combined_content)

            # Get chapter name for display
            chapter_id = request.session.get('selected_chapter')
            chapter_name = None
            chapters = []
            if book_id:
                chapters = get_book_chapters(book_id)
                if chapter_id:
                    for chapter in chapters:
                        if str(chapter['id']) == str(chapter_id):
                            chapter_name = chapter['name']
                            break

            context = {
                'generated_questions': formatted_content,
                'original_questions': questions,
                'language': language,
                'question_type': question_type,
                'difficulty': difficulty,
                'num_questions': num_questions,
                'questions_json': questions_json,
                'model_type': model_type,
                'books': get_available_books(),
                'selected_book': book_id,
                'chapters': chapters,
                'selected_chapter': chapter_id,
                'chapter_name': chapter_name
            }

            return render(request, 'school_app/math/math_tools.html', context)

    except json.JSONDecodeError:
        messages.error(request, error_messages[language]['invalid_data'])
    except Exception as e:
        print(f"Unexpected error: {e}")
        messages.error(request, f"An unexpected error occurred: {str(e)}")
        return redirect('login')

    return redirect('math_tools')

@login_or_student_required
def generate_form(request):
    if request.method == 'POST':
        questions = json.loads(request.POST.get('questions', '[]'))

        # Get chapter name from session (same as generate_math does)
        chapter_name = request.POST.get('chapter_name', '')
        if not chapter_name:
            book_id = request.session.get('selected_book')
            chapter_id = request.session.get('selected_chapter')
            if book_id and chapter_id:
                for ch in get_book_chapters(book_id):
                    if str(ch['id']) == str(chapter_id):
                        chapter_name = ch['name']
                        break

        book_id = request.session.get('selected_book')
        language = get_book_language(book_id) if book_id else 'English'

        context = {
            'questions': questions,
            'questions_json': request.POST.get('questions'),
            'chapter_name': chapter_name,
            'language': language,
        }
        return render(request, 'school_app/math/generate_form.html', context)
    return redirect('math_tools')


def presentation(request):
    """Display the PadhaiWithAI project presentation."""
    return render(request, 'school_app/misc/presentation.html')


def user_manual(request):
    """Display the system user manual."""
    return render(request, 'school_app/misc/user_manual.html')
