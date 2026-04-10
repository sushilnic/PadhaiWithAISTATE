"""
Question paper generator views and helpers.
"""
from .utils import *
from .utils import _strip_think


def get_available_books():
    """Return a list of available books from the content directory"""
    content_dir = os.path.join(settings.BASE_DIR, 'school_app', 'content')
    books = []

    try:
        # List all directories (books) in content folder
        book_dirs = [d for d in os.listdir(content_dir)
                    if os.path.isdir(os.path.join(content_dir, d))]

        for book_dir in book_dirs:
            content_file = os.path.join(content_dir, book_dir, 'content.json')
            if os.path.exists(content_file):
                with open(content_file, 'r', encoding='utf-8') as f:
                    book_info = json.load(f)
                    books.append({
                        'id': book_dir,  # Use directory name as ID
                        'name': book_info['book_name'],
                        'language': book_info['language'],
                        'class': book_info['class']
                    })
    except Exception as e:
        print(f"Error loading books: {e}")

    return books


def load_chapter_content(book_id, chapter_id):
    """Load the content of a specific chapter from a book"""
    try:
        chapter_file = os.path.join(
            settings.BASE_DIR,
            'school_app',
            'content',
            book_id,
            f'chapter{chapter_id}.json'
        )

        with open(chapter_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading chapter content: {e}")
        return None


def get_book_chapters(book_id):
    """Return a list of chapters for a given book ID"""
    try:
        content_file = os.path.join(
            settings.BASE_DIR,
            'school_app',
            'content',
            book_id,
            'content.json'
        )

        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                book_info = json.load(f)
                return book_info.get('chapters', [])
        return []

    except Exception as e:
        print(f"Error loading chapters for book {book_id}: {e}")
        return []


def get_book_language(book_id):
    """Determine the language of a book based on its content.json file"""
    try:
        content_file = os.path.join(
            settings.BASE_DIR,
            'school_app',
            'content',
            book_id,
            'content.json'
        )

        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                book_info = json.load(f)
                return book_info.get('language', 'English')  # Default to English if not specified
        return 'English'  # Default to English if file doesn't exist

    except Exception as e:
        print(f"Error determining book language for {book_id}: {e}")
        return 'English'  # Default to English on error


@login_or_student_required
def get_chapters(request, book_id):
    try:
        chapters = get_book_chapters(book_id)
        return JsonResponse({'chapters': chapters})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def question_paper_generator(request):
    """Render the AI Question Paper Generator form for school teachers."""
    school_name = ''
    try:
        school_name = request.user.administered_school.name
    except Exception:
        pass
    return render(request, 'school_app/question_paper/question_paper_generator.html', {'school_name': school_name})


@login_required
@require_http_methods(["POST"])
def generate_question_paper_ai(request):
    """Generate a full question paper + answer key using Sarvam AI."""
    try:
        if not SarvamAI or not SARVAM_API_KEY:
            return JsonResponse({'error': 'AI service not configured.'}, status=500)

        data = json.loads(request.body)
        subject     = str(data.get('subject', '')).strip()[:100]
        chapter     = str(data.get('chapter', '')).strip()[:200]
        class_name  = str(data.get('class_name', '10')).strip()[:3]
        total_marks = int(data.get('total_marks', 50))
        language    = data.get('language', 'English')
        difficulty  = data.get('difficulty', 'Medium')
        if difficulty not in ('Easy', 'Medium', 'Hard', 'Mixed'):
            difficulty = 'Medium'
        mcq_count   = int(data.get('mcq_count', 10))
        mcq_marks   = int(data.get('mcq_marks', 1))
        tf_count    = int(data.get('tf_count', 5))
        tf_marks    = int(data.get('tf_marks', 1))
        fib_count   = int(data.get('fib_count', 5))
        fib_marks   = int(data.get('fib_marks', 1))
        short_count = int(data.get('short_count', 5))
        short_marks = int(data.get('short_marks', 3))
        long_count  = int(data.get('long_count', 3))
        long_marks  = int(data.get('long_marks', 5))

        if not subject or not chapter:
            return JsonResponse({'error': 'Subject and chapter are required.'}, status=400)

        difficulty_hindi = {'Easy': 'सरल', 'Medium': 'मध्यम', 'Hard': 'कठिन', 'Mixed': 'मिश्रित'}.get(difficulty, 'मध्यम')
        if language == 'Hindi':
            prompt = f"""कक्षा {class_name} के लिए "{subject}" विषय के "{chapter}" अध्याय पर एक पूर्ण प्रश्न पत्र बनाएं।
कुल अंक: {total_marks}
कठिनाई स्तर: {difficulty_hindi}

निम्नलिखित खंड शामिल करें:
खंड A: {mcq_count} बहुविकल्पीय प्रश्न (प्रत्येक {mcq_marks} अंक)
खंड B: {tf_count} सही/गलत प्रश्न (प्रत्येक {tf_marks} अंक)
खंड C: {fib_count} रिक्त स्थान भरो प्रश्न (प्रत्येक {fib_marks} अंक)
खंड D: {short_count} लघु उत्तरीय प्रश्न (प्रत्येक {short_marks} अंक)
खंड E: {long_count} दीर्घ उत्तरीय प्रश्न (प्रत्येक {long_marks} अंक)

इस JSON प्रारूप में उत्तर दें:
{{
  "paper_title": "...",
  "subject": "{subject}",
  "class": "{class_name}",
  "chapter": "{chapter}",
  "total_marks": {total_marks},
  "time_allowed": "...",
  "sections": [
    {{
      "section": "A",
      "section_title": "बहुविकल्पीय प्रश्न",
      "marks_each": {mcq_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}
      ]
    }},
    {{
      "section": "B",
      "section_title": "सही / गलत",
      "marks_each": {tf_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "सही"}}
      ]
    }},
    {{
      "section": "C",
      "section_title": "रिक्त स्थान भरो",
      "marks_each": {fib_marks},
      "questions": [
        {{"q_no": 1, "question": "_______ का मान π होता है।", "answer": "..."}}
      ]
    }},
    {{
      "section": "D",
      "section_title": "लघु उत्तरीय प्रश्न",
      "marks_each": {short_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "..."}}
      ]
    }},
    {{
      "section": "E",
      "section_title": "दीर्घ उत्तरीय प्रश्न",
      "marks_each": {long_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "..."}}
      ]
    }}
  ]
}}
केवल JSON लौटाएं। सभी प्रश्न और उत्तर हिंदी में होने चाहिए।"""
            system_msg = "आप एक अनुभवी शिक्षक हैं। केवल वैध JSON में उत्तर दें।"
        else:
            prompt = f"""Create a complete question paper for Class {class_name} on the chapter "{chapter}" of subject "{subject}".
Total Marks: {total_marks}
Difficulty Level: {difficulty}

Include the following sections:
Section A: {mcq_count} Multiple Choice Questions ({mcq_marks} mark each)
Section B: {tf_count} True/False Questions ({tf_marks} mark each)
Section C: {fib_count} Fill in the Blank Questions ({fib_marks} mark each)
Section D: {short_count} Short Answer Questions ({short_marks} marks each)
Section E: {long_count} Long Answer Questions ({long_marks} marks each)

Respond strictly in this JSON format:
{{
  "paper_title": "...",
  "subject": "{subject}",
  "class": "{class_name}",
  "chapter": "{chapter}",
  "total_marks": {total_marks},
  "time_allowed": "...",
  "sections": [
    {{
      "section": "A",
      "section_title": "Multiple Choice Questions",
      "marks_each": {mcq_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}
      ]
    }},
    {{
      "section": "B",
      "section_title": "True / False",
      "marks_each": {tf_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "True"}}
      ]
    }},
    {{
      "section": "C",
      "section_title": "Fill in the Blanks",
      "marks_each": {fib_marks},
      "questions": [
        {{"q_no": 1, "question": "The value of pi is approximately ___.", "answer": "3.14"}}
      ]
    }},
    {{
      "section": "D",
      "section_title": "Short Answer Questions",
      "marks_each": {short_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "..."}}
      ]
    }},
    {{
      "section": "E",
      "section_title": "Long Answer Questions",
      "marks_each": {long_marks},
      "questions": [
        {{"q_no": 1, "question": "...", "answer": "..."}}
      ]
    }}
  ]
}}
Return ONLY the JSON. No extra text."""
            system_msg = "You are an experienced teacher. Always respond with valid JSON only."

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        response = client.chat.completions(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.4,
            max_tokens=4000,
            top_p=0.5,
        )

        ai_text = _strip_think(response.choices[0].message.content)

        # Extract JSON robustly
        if '```' in ai_text:
            for part in ai_text.split('```'):
                if part.startswith('json'):
                    ai_text = part[4:].strip()
                    break
                elif '{' in part:
                    ai_text = part.strip()
                    break
        start = ai_text.find('{')
        end   = ai_text.rfind('}')
        if start != -1 and end != -1:
            ai_text = ai_text[start:end + 1]

        paper_data = json.loads(ai_text)

        from ..models import QuestionPaperHistory
        history = QuestionPaperHistory.objects.create(
            user=request.user,
            subject=subject,
            chapter=chapter,
            class_name=class_name,
            language=language,
            difficulty=difficulty,
            total_marks=total_marks,
            time_allowed=int(data.get('time_allowed', 90)),
            paper_json=paper_data,
        )

        return JsonResponse({'success': True, 'paper': paper_data, 'paper_id': history.pk})

    except json.JSONDecodeError:
        return JsonResponse({'error': 'AI returned invalid data. Please try again.'}, status=500)
    except Exception as e:
        logger.exception("generate_question_paper_ai error")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def question_paper_history(request):
    """List all question papers generated by the logged-in user."""
    from ..models import QuestionPaperHistory
    papers = QuestionPaperHistory.objects.filter(user=request.user).order_by('-created_at')
    school_name = ''
    try:
        school_name = request.user.administered_school.name
    except Exception:
        pass
    return render(request, 'school_app/question_paper/question_paper_history.html', {'papers': papers, 'school_name': school_name})
