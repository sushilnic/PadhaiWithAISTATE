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
            system_msg = "आप एक अनुभवी शिक्षक हैं। केवल वैध JSON में उत्तर दें।"
        else:
            system_msg = "You are an experienced teacher. Always respond with valid JSON only."

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

        def call_ai(user_prompt):
            """Call Sarvam and return parsed JSON dict, or raise json.JSONDecodeError."""
            resp = client.chat.completions(
                #model="sarvam-105b",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
                top_p=0.9,
            )
            msg = resp.choices[0].message
            raw = msg.content or msg.reasoning_content
            if not raw:
                raise json.JSONDecodeError("Empty AI response", "", 0)
            text = _strip_think(raw)
            if not text:
                raise json.JSONDecodeError("Empty AI response after stripping", "", 0)
            if '```' in text:
                for part in text.split('```'):
                    if part.startswith('json'):
                        text = part[4:].strip(); break
                    elif '{' in part:
                        text = part.strip(); break
            s, e = text.find('{'), text.rfind('}')
            if s != -1 and e != -1:
                text = text[s:e + 1]
            logger.warning("Sarvam text before json.loads: %r", text)
            return json.loads(text)

        # ── Call 1: header + Section A (MCQ) ──────────────────────────
        # ── Call 2: Section B (True/False) + Section C (FIB) ──────────
        # ── Call 3: Section D (Short Answer) + Section E (Long Answer) ─
        if language == 'Hindi':
            prompt1 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}" के लिए।
कठिनाई: {difficulty_hindi}

केवल निम्न JSON लौटाएं (कोई अतिरिक्त टेक्स्ट नहीं):
{{
  "paper_title": "...",
  "subject": "{subject}",
  "class": "{class_name}",
  "chapter": "{chapter}",
  "total_marks": {total_marks},
  "time_allowed": "3 घंटे",
  "sections": [
    {{
      "section": "A", "section_title": "बहुविकल्पीय प्रश्न", "marks_each": {mcq_marks},
      "questions": [{{"q_no": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}]
    }}
  ]
}}
खंड A में {mcq_count} प्रश्न दें। सभी हिंदी में।"""

            prompt2 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}" के लिए।
कठिनाई: {difficulty_hindi}

केवल निम्न JSON लौटाएं (कोई अतिरिक्त टेक्स्ट नहीं):
{{
  "sections": [
    {{
      "section": "B", "section_title": "सही / गलत", "marks_each": {tf_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "सही"}}]
    }},
    {{
      "section": "C", "section_title": "रिक्त स्थान भरो", "marks_each": {fib_marks},
      "questions": [{{"q_no": 1, "question": "_______ का मान π होता है।", "answer": "..."}}]
    }}
  ]
}}
खंड B में {tf_count} प्रश्न और खंड C में {fib_count} प्रश्न दें। सभी हिंदी में।"""

            prompt3 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}" के लिए।
कठिनाई: {difficulty_hindi}

केवल निम्न JSON लौटाएं (कोई अतिरिक्त टेक्स्ट नहीं):
{{
  "sections": [
    {{
      "section": "D", "section_title": "लघु उत्तरीय प्रश्न", "marks_each": {short_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "..."}}]
    }},
    {{
      "section": "E", "section_title": "दीर्घ उत्तरीय प्रश्न", "marks_each": {long_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "..."}}]
    }}
  ]
}}
खंड D में {short_count} प्रश्न और खंड E में {long_count} प्रश्न दें। सभी हिंदी में।"""
        else:
            prompt1 = f"""Class {class_name}, subject "{subject}", chapter "{chapter}". Difficulty: {difficulty}.

Return ONLY this JSON (no extra text):
{{
  "paper_title": "...",
  "subject": "{subject}",
  "class": "{class_name}",
  "chapter": "{chapter}",
  "total_marks": {total_marks},
  "time_allowed": "3 Hours",
  "sections": [
    {{
      "section": "A", "section_title": "Multiple Choice Questions", "marks_each": {mcq_marks},
      "questions": [{{"q_no": 1, "question": "...", "options": ["A. ...", "B. ...", "C. ...", "D. ..."], "answer": "..."}}]
    }}
  ]
}}
Section A: {mcq_count} questions."""

            prompt2 = f"""Class {class_name}, subject "{subject}", chapter "{chapter}". Difficulty: {difficulty}.

Return ONLY this JSON (no extra text):
{{
  "sections": [
    {{
      "section": "B", "section_title": "True / False", "marks_each": {tf_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "True"}}]
    }},
    {{
      "section": "C", "section_title": "Fill in the Blanks", "marks_each": {fib_marks},
      "questions": [{{"q_no": 1, "question": "The value of pi is ___.", "answer": "3.14"}}]
    }}
  ]
}}
Section B: {tf_count} questions, Section C: {fib_count} questions."""

            prompt3 = f"""Class {class_name}, subject "{subject}", chapter "{chapter}". Difficulty: {difficulty}.

Return ONLY this JSON (no extra text):
{{
  "sections": [
    {{
      "section": "D", "section_title": "Short Answer Questions", "marks_each": {short_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "..."}}]
    }},
    {{
      "section": "E", "section_title": "Long Answer Questions", "marks_each": {long_marks},
      "questions": [{{"q_no": 1, "question": "...", "answer": "..."}}]
    }}
  ]
}}
Section D: {short_count} questions, Section E: {long_count} questions."""

        part1 = call_ai(prompt1)
        part2 = call_ai(prompt2)
        part3 = call_ai(prompt3)

        # Merge: use part1 as the base, append sections from part2 and part3
        paper_data = part1
        paper_data['sections'].extend(part2.get('sections', []))
        paper_data['sections'].extend(part3.get('sections', []))

        paper_data = json.loads(json.dumps(paper_data))  # validate round-trip

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
