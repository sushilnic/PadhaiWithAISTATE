"""
Question paper generator views and helpers.
"""
import re
from .utils import *
from .utils import _strip_think

# Content directory inputs (book_id, chapter_id) come from POST data, so they
# MUST be validated before being used in os.path.join() — otherwise path
# traversal (e.g. book_id='../../../etc') could read arbitrary files.
_BOOK_ID_RE    = re.compile(r'^[A-Za-z0-9_\-]+$')
_CHAPTER_ID_RE = re.compile(r'^[A-Za-z0-9_\-]+$')


def _safe_book_dir(book_id):
    """Return absolute path to a book's content directory, or None if invalid."""
    if not book_id or not isinstance(book_id, str) or not _BOOK_ID_RE.match(book_id):
        return None
    base = os.path.realpath(os.path.join(settings.BASE_DIR, 'school_app', 'content'))
    target = os.path.realpath(os.path.join(base, book_id))
    # Defence in depth: ensure resolved path stays inside content/
    if not target.startswith(base + os.sep):
        return None
    return target


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
    except Exception:
        logger.exception('get_available_books: failed to scan content directory')

    return books


def load_chapter_content(book_id, chapter_id):
    """Load the content of a specific chapter from a book.
    Returns None if book_id or chapter_id is invalid (path-traversal protection).
    """
    book_dir = _safe_book_dir(book_id)
    if not book_dir:
        logger.warning('load_chapter_content: invalid book_id=%r', book_id)
        return None
    if not _CHAPTER_ID_RE.match(str(chapter_id)):
        logger.warning('load_chapter_content: invalid chapter_id=%r', chapter_id)
        return None
    try:
        chapter_file = os.path.join(book_dir, f'chapter{chapter_id}.json')
        with open(chapter_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        logger.exception('load_chapter_content: read failed for %r/%r', book_id, chapter_id)
        return None


def get_book_chapters(book_id):
    """Return a list of chapters for a given book ID."""
    book_dir = _safe_book_dir(book_id)
    if not book_dir:
        logger.warning('get_book_chapters: invalid book_id=%r', book_id)
        return []
    try:
        content_file = os.path.join(book_dir, 'content.json')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                book_info = json.load(f)
                return book_info.get('chapters', [])
        return []
    except Exception:
        logger.exception('get_book_chapters: read failed for %r', book_id)
        return []


def get_book_language(book_id):
    """Determine the language of a book based on its content.json file."""
    book_dir = _safe_book_dir(book_id)
    if not book_dir:
        logger.warning('get_book_language: invalid book_id=%r', book_id)
        return 'English'
    try:
        content_file = os.path.join(book_dir, 'content.json')
        if os.path.exists(content_file):
            with open(content_file, 'r', encoding='utf-8') as f:
                book_info = json.load(f)
                return book_info.get('language', 'English')
        return 'English'
    except Exception:
        logger.exception('get_book_language: read failed for %r', book_id)
        return 'English'


@login_or_student_required
def get_chapters(request, book_id):
    try:
        chapters = get_book_chapters(book_id)
        return JsonResponse({'chapters': chapters})
    except Exception:
        logger.exception('get_chapters failed for book_id=%r', book_id)
        return JsonResponse({'error': 'Could not load chapters.'}, status=400)


@login_required
def question_paper_generator(request):
    """Render the AI Question Paper Generator form for school teachers."""
    school_name = ''
    try:
        school_name = request.user.administered_school.name
    except Exception:
        pass
    return render(request, 'school_app/question_paper/question_paper_generator.html', {'school_name': school_name})


def _is_paper_quality_ok(paper):
    """Python port of the client-side isPaperValid() — catches AI-generated
    junk before it hits the DB. Returns False if:
        - No sections
        - Any section has zero questions
        - Any question text or answer is placeholder (dots/spaces only, or
          too short after stripping)
        - MCQ (Section A) has fewer than 4 options, or an option looks
          like a placeholder, or two options are identical
    """
    if not paper or not isinstance(paper, dict):
        return False
    sections = paper.get('sections') or []
    if not sections:
        return False
    import re
    dots_ws = re.compile(r'[.\s]')
    for sec in sections:
        qs = sec.get('questions') or []
        if not qs:
            return False
        section_id = str(sec.get('section', '')).strip()
        for q in qs:
            qtext = str(q.get('question', '')).strip()
            atext = str(q.get('answer', '')).strip()
            # Placeholder question (<8 real chars after stripping dots/whitespace)
            if len(dots_ws.sub('', qtext)) < 8:
                return False
            # Placeholder / empty answer
            if len(dots_ws.sub('', atext)) < 1:
                return False
            # MCQ-specific checks
            if section_id == 'A':
                options = q.get('options') or []
                if len(options) < 4:
                    return False
                cleaned = []
                for opt in options:
                    s = str(opt or '')
                    # Strip common A./B./ prefixes and dots/spaces
                    stripped = re.sub(r'[A-D.\s]', '', s)
                    if len(stripped) < 3:
                        return False
                    cleaned.append(s.strip().lower())
                # Duplicate option texts
                if len(set(cleaned)) < len(cleaned):
                    return False
    return True


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

        # ── Validate counts ────────────────────────────────────────────────
        for name, val in [('MCQ', mcq_count), ('True/False', tf_count),
                          ('Fill-in-blank', fib_count), ('Short answer', short_count),
                          ('Long answer', long_count)]:
            if val < 0:
                return JsonResponse({'error': f'{name} count cannot be negative.'}, status=400)
        for name, val in [('MCQ marks', mcq_marks), ('True/False marks', tf_marks),
                          ('Fill-in-blank marks', fib_marks), ('Short answer marks', short_marks),
                          ('Long answer marks', long_marks)]:
            if val < 1:
                return JsonResponse({'error': f'{name} must be at least 1.'}, status=400)
        if mcq_count + tf_count + fib_count + short_count + long_count == 0:
            return JsonResponse({'error': 'At least one section must have questions.'}, status=400)
        if total_marks < 1:
            return JsonResponse({'error': 'Total marks must be at least 1.'}, status=400)
        try:
            cn = int(class_name)
            if not (1 <= cn <= 12):
                raise ValueError
        except ValueError:
            return JsonResponse({'error': 'Class must be between 1 and 12.'}, status=400)

        difficulty_hindi = {'Easy': 'सरल', 'Medium': 'मध्यम', 'Hard': 'कठिन', 'Mixed': 'मिश्रित'}.get(difficulty, 'मध्यम')

        if language == 'Hindi':
            system_msg = "आप एक अनुभवी शिक्षक हैं। केवल वैध JSON में उत्तर दें। JSON compact रखें, कोई अतिरिक्त whitespace या indentation नहीं।"
        else:
            system_msg = "You are an experienced teacher. Always respond with valid compact JSON only. No extra whitespace, newlines, or indentation."

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
        sarvam_model = os.getenv("SARVAM_MODEL", "sarvam-m")
        
        sarvam_max_tokens = int(os.getenv("SARVAM_MAX_TOKENS", "4000"))
        
        def _repair_json(text):
            """Fix common AI JSON issues: trailing commas, unclosed brackets."""
            import re
            # 1. Remove trailing commas before } or ]
            text = re.sub(r',\s*([\}\]])', r'\1', text)
            # 2. Close unclosed brackets/braces caused by token-limit truncation
            stack = []
            in_string = False
            escape = False
            for ch in text:
                if escape:
                    escape = False; continue
                if ch == '\\' and in_string:
                    escape = True; continue
                if ch == '"':
                    in_string = not in_string; continue
                if in_string:
                    continue
                if ch in '{[':
                    stack.append('}' if ch == '{' else ']')
                elif ch in '}]' and stack and stack[-1] == ch:
                    stack.pop()
            return text + ''.join(reversed(stack))

        def _extract_json(raw_text):
            """Strip AI preamble/postamble and return the JSON string."""
            text = _strip_think(raw_text)
            if not text:
                return ''
            if '```' in text:
                for part in text.split('```'):
                    p = part.strip()
                    if p.startswith('json'):
                        text = p[4:].strip(); break
                    elif '{' in p:
                        text = p; break
            s, e = text.find('{'), text.rfind('}')
            if s != -1 and e != -1:
                text = text[s:e + 1]
            return text

        def call_ai(user_prompt, max_tok=sarvam_max_tokens):
            """Call Sarvam and return parsed JSON dict, or raise json.JSONDecodeError."""
            resp = client.chat.completions(
                model=sarvam_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=max_tok,
                top_p=0.9,
                reasoning_effort=None
            )
            msg = resp.choices[0].message
            raw = msg.content or msg.reasoning_content
            if not raw:
                raise json.JSONDecodeError("Empty AI response", "", 0)
            text = _extract_json(raw)
            if not text:
                raise json.JSONDecodeError("Empty AI response after stripping", "", 0)
            logger.warning("Sarvam raw JSON: %r", text[:300])
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                repaired = _repair_json(text)
                logger.warning("Repaired JSON, retrying parse")
                return json.loads(repaired)

        def call_ai_robust(user_prompt, section_label, max_tok=sarvam_max_tokens):
            """call_ai with one automatic retry; returns None on persistent failure."""
            for attempt in range(2):
                try:
                    return call_ai(user_prompt, max_tok)
                except json.JSONDecodeError:
                    if attempt == 0:
                        logger.warning("JSON parse failed for %s, retrying…", section_label)
                        continue
                    logger.error("Both attempts failed for %s", section_label)
                    return None
                except Exception as exc:
                    logger.error("AI call error for %s: %s", section_label, exc)
                    return None

        # ── Call 1: header + Section A (MCQ) ──────────────────────────
        # ── Call 2: Section B (True/False) + Section C (FIB) ──────────
        # ── Call 3: Section D (Short Answer) + Section E (Long Answer) ─
        NO_DOTS = "CRITICAL: Write real exam content. Do NOT output dots, ellipsis, or placeholder text in any field."
        NO_DOTS_HI = "महत्वपूर्ण: प्रत्येक प्रश्न और उत्तर वास्तविक परीक्षा सामग्री होनी चाहिए। कोई भी फ़ील्ड में '...' या खाली प्लेसहोल्डर मत लिखें।"

        if language == 'Hindi':
            prompt1 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}", कठिनाई: {difficulty_hindi}।
खंड A के लिए {mcq_count} बहुविकल्पीय प्रश्न बनाएं।

केवल यह JSON लौटाएं:
{{"paper_title":"{subject} प्रश्न पत्र","subject":"{subject}","class":"{class_name}","chapter":"{chapter}","total_marks":{total_marks},"time_allowed":"3 घंटे","sections":[{{"section":"A","section_title":"बहुविकल्पीय प्रश्न","marks_each":{mcq_marks},"questions":[{{"q_no":1,"question":"अध्याय से संबंधित वास्तविक प्रश्न","options":["A. पहला विकल्प","B. दूसरा विकल्प","C. तीसरा विकल्प","D. चौथा विकल्प"],"answer":"A. सही विकल्प"}}]}}]}}

नियम: {mcq_count} प्रश्न दें। प्रत्येक प्रश्न में 4 अलग-अलग विकल्प हों। सही उत्तर केवल एक विकल्प में हो। {NO_DOTS_HI}"""

            prompt2 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}", कठिनाई: {difficulty_hindi}।
खंड B में {tf_count} सही/गलत प्रश्न और खंड C में {fib_count} रिक्त स्थान प्रश्न बनाएं।

केवल यह JSON लौटाएं:
{{"sections":[{{"section":"B","section_title":"सही / गलत","marks_each":{tf_marks},"questions":[{{"q_no":1,"question":"अध्याय से संबंधित कथन लिखें।","answer":"सही"}}]}},{{"section":"C","section_title":"रिक्त स्थान भरो","marks_each":{fib_marks},"questions":[{{"q_no":1,"question":"_______ अध्याय की परिभाषा है।","answer":"सही शब्द"}}]}}]}}

नियम: खंड B में {tf_count} और खंड C में {fib_count} प्रश्न दें। {NO_DOTS_HI}"""

            prompt3 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}", कठिनाई: {difficulty_hindi}।
खंड D के लिए {short_count} लघु उत्तरीय प्रश्न बनाएं।

केवल यह JSON लौटाएं:
{{"sections":[{{"section":"D","section_title":"लघु उत्तरीय प्रश्न","marks_each":{short_marks},"questions":[{{"q_no":1,"question":"अध्याय से संबंधित लघु प्रश्न लिखें।","answer":"2-3 वाक्यों में उत्तर लिखें।"}}]}}]}}

नियम: {short_count} प्रश्न दें। प्रत्येक उत्तर 2-3 वाक्यों में हो। {NO_DOTS_HI}"""

            prompt4 = f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}", कठिनाई: {difficulty_hindi}।
खंड E के लिए {long_count} दीर्घ उत्तरीय प्रश्न बनाएं।

केवल यह JSON लौटाएं:
{{"sections":[{{"section":"E","section_title":"दीर्घ उत्तरीय प्रश्न","marks_each":{long_marks},"questions":[{{"q_no":1,"question":"अध्याय से संबंधित विस्तृत प्रश्न लिखें।","answer":"4-5 वाक्यों में विस्तृत उत्तर लिखें।"}}]}}]}}

नियम: {long_count} प्रश्न दें। प्रत्येक उत्तर कम से कम 4-5 वाक्यों में हो। {NO_DOTS_HI}"""
        else:
            prompt1 = f"""Class {class_name}, Subject "{subject}", Chapter "{chapter}", Difficulty: {difficulty}.
Generate {mcq_count} Multiple Choice Questions for Section A.

Return ONLY this JSON:
{{"paper_title":"{subject} Question Paper","subject":"{subject}","class":"{class_name}","chapter":"{chapter}","total_marks":{total_marks},"time_allowed":"3 Hours","sections":[{{"section":"A","section_title":"Multiple Choice Questions","marks_each":{mcq_marks},"questions":[{{"q_no":1,"question":"Write an actual exam question about the chapter topic","options":["A. first option text","B. second option text","C. third option text","D. fourth option text"],"answer":"A. correct option text"}}]}}]}}

Rules: Generate {mcq_count} questions. Each question needs exactly 4 distinct options. The answer must match one option exactly. No two options may have the same text. {NO_DOTS}"""

            prompt2 = f"""Class {class_name}, Subject "{subject}", Chapter "{chapter}", Difficulty: {difficulty}.
Generate {tf_count} True/False questions (Section B) and {fib_count} Fill-in-the-Blank questions (Section C).

Return ONLY this JSON:
{{"sections":[{{"section":"B","section_title":"True / False","marks_each":{tf_marks},"questions":[{{"q_no":1,"question":"Write a factual statement about the chapter.","answer":"True"}}]}},{{"section":"C","section_title":"Fill in the Blanks","marks_each":{fib_marks},"questions":[{{"q_no":1,"question":"The ___ is the key concept of this chapter.","answer":"correct word or phrase"}}]}}]}}

Rules: Section B needs {tf_count} questions (answer True or False). Section C needs {fib_count} questions with ___ for the blank. {NO_DOTS}"""

            prompt3 = f"""Class {class_name}, Subject "{subject}", Chapter "{chapter}", Difficulty: {difficulty}.
Generate {short_count} Short Answer Questions for Section D.

Return ONLY this JSON:
{{"sections":[{{"section":"D","section_title":"Short Answer Questions","marks_each":{short_marks},"questions":[{{"q_no":1,"question":"Write an actual short-answer question about the chapter.","answer":"Write a concise 2-3 sentence model answer."}}]}}]}}

Rules: Generate {short_count} questions. Each answer should be 2-3 sentences. {NO_DOTS}"""

            prompt4 = f"""Class {class_name}, Subject "{subject}", Chapter "{chapter}", Difficulty: {difficulty}.
Generate {long_count} Long Answer Questions for Section E.

Return ONLY this JSON:
{{"sections":[{{"section":"E","section_title":"Long Answer Questions","marks_each":{long_marks},"questions":[{{"q_no":1,"question":"Write an actual detailed question about the chapter.","answer":"Write a comprehensive 4-5 sentence model answer."}}]}}]}}

Rules: Generate {long_count} questions. Each answer must be at least 4-5 sentences. {NO_DOTS}"""

        # ── Make only the API calls needed (skip sections with 0 questions) ──
        def get_sec(data, letter):
            if not data:
                return None
            for s in data.get('sections', []):
                if s.get('section') == letter:
                    return s
            return None

        def fill_missing(sec, expected, make_prompt):
            """One retry: ask AI only for the missing questions."""
            if not sec or expected == 0:
                return
            qs = sec.get('questions', [])
            have = len(qs)
            if have >= expected:
                return
            missing = expected - have
            start_q = have + 1
            try:
                extra = call_ai(make_prompt(start_q, missing))
                extra_sec = get_sec(extra, sec['section'])
                if extra_sec:
                    new_qs = extra_sec.get('questions', [])[:missing]
                    for i, q in enumerate(new_qs):
                        q['q_no'] = start_q + i
                    qs.extend(new_qs)
                    sec['questions'] = qs
            except Exception:
                pass  # keep whatever was generated

        part1 = call_ai_robust(prompt1, 'Section A (MCQ)')           if mcq_count > 0 else None
        part2 = call_ai_robust(prompt2, 'Section B+C (TF+FIB)')     if (tf_count > 0 or fib_count > 0) else None
        part3 = call_ai_robust(prompt3, 'Section D (Short Answer)')  if short_count > 0 else None
        part4 = call_ai_robust(prompt4, 'Section E (Long Answer)')   if long_count > 0 else None

        sec_a = get_sec(part1, 'A')
        sec_b = get_sec(part2, 'B')
        sec_c = get_sec(part2, 'C')
        sec_d = get_sec(part3, 'D')
        sec_e = get_sec(part4, 'E')

        if language == 'Hindi':
            fill_missing(sec_a, mcq_count, lambda s, n: f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}"। {n} बहुविकल्पीय प्रश्न {s} से {s+n-1} तक बनाएं। केवल JSON:
{{"sections":[{{"section":"A","section_title":"बहुविकल्पीय प्रश्न","marks_each":{mcq_marks},"questions":[{{"q_no":{s},"question":"अध्याय से वास्तविक प्रश्न","options":["A. पहला विकल्प","B. दूसरा विकल्प","C. तीसरा विकल्प","D. चौथा विकल्प"],"answer":"A. सही विकल्प"}}]}}]}}
{NO_DOTS_HI}""")

            fill_missing(sec_b, tf_count, lambda s, n: f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}"। {n} सही/गलत प्रश्न {s} से {s+n-1} तक बनाएं। केवल JSON:
{{"sections":[{{"section":"B","section_title":"सही / गलत","marks_each":{tf_marks},"questions":[{{"q_no":{s},"question":"अध्याय से वास्तविक कथन","answer":"सही"}}]}}]}}
{NO_DOTS_HI}""")

            fill_missing(sec_c, fib_count, lambda s, n: f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}"। {n} रिक्त स्थान प्रश्न {s} से {s+n-1} तक बनाएं। केवल JSON:
{{"sections":[{{"section":"C","section_title":"रिक्त स्थान भरो","marks_each":{fib_marks},"questions":[{{"q_no":{s},"question":"अध्याय से ___ वाक्य","answer":"सही शब्द"}}]}}]}}
{NO_DOTS_HI}""")

            fill_missing(sec_d, short_count, lambda s, n: f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}"। {n} लघु उत्तरीय प्रश्न {s} से {s+n-1} तक बनाएं। केवल JSON:
{{"sections":[{{"section":"D","section_title":"लघु उत्तरीय प्रश्न","marks_each":{short_marks},"questions":[{{"q_no":{s},"question":"अध्याय से वास्तविक प्रश्न","answer":"2-3 वाक्यों में उत्तर"}}]}}]}}
{NO_DOTS_HI}""")

            fill_missing(sec_e, long_count, lambda s, n: f"""कक्षा {class_name}, विषय "{subject}", अध्याय "{chapter}"। {n} दीर्घ उत्तरीय प्रश्न {s} से {s+n-1} तक बनाएं। केवल JSON:
{{"sections":[{{"section":"E","section_title":"दीर्घ उत्तरीय प्रश्न","marks_each":{long_marks},"questions":[{{"q_no":{s},"question":"अध्याय से विस्तृत प्रश्न","answer":"4-5 वाक्यों में विस्तृत उत्तर"}}]}}]}}
{NO_DOTS_HI}""")
        else:
            fill_missing(sec_a, mcq_count, lambda s, n: f"""Class {class_name}, "{subject}", "{chapter}". Generate {n} MCQ questions numbered {s} to {s+n-1}. Return ONLY JSON:
{{"sections":[{{"section":"A","section_title":"Multiple Choice Questions","marks_each":{mcq_marks},"questions":[{{"q_no":{s},"question":"actual exam question text","options":["A. first option","B. second option","C. third option","D. fourth option"],"answer":"A. correct option"}}]}}]}}
{NO_DOTS}""")

            fill_missing(sec_b, tf_count, lambda s, n: f"""Class {class_name}, "{subject}", "{chapter}". Generate {n} True/False questions numbered {s} to {s+n-1}. Return ONLY JSON:
{{"sections":[{{"section":"B","section_title":"True / False","marks_each":{tf_marks},"questions":[{{"q_no":{s},"question":"factual statement about the topic","answer":"True"}}]}}]}}
{NO_DOTS}""")

            fill_missing(sec_c, fib_count, lambda s, n: f"""Class {class_name}, "{subject}", "{chapter}". Generate {n} Fill-in-the-Blank questions numbered {s} to {s+n-1}. Return ONLY JSON:
{{"sections":[{{"section":"C","section_title":"Fill in the Blanks","marks_each":{fib_marks},"questions":[{{"q_no":{s},"question":"The ___ is the key term.","answer":"correct word"}}]}}]}}
{NO_DOTS}""")

            fill_missing(sec_d, short_count, lambda s, n: f"""Class {class_name}, "{subject}", "{chapter}". Generate {n} Short Answer questions numbered {s} to {s+n-1}. Return ONLY JSON:
{{"sections":[{{"section":"D","section_title":"Short Answer Questions","marks_each":{short_marks},"questions":[{{"q_no":{s},"question":"actual short-answer question","answer":"concise 2-3 sentence answer"}}]}}]}}
{NO_DOTS}""")

            fill_missing(sec_e, long_count, lambda s, n: f"""Class {class_name}, "{subject}", "{chapter}". Generate {n} Long Answer questions numbered {s} to {s+n-1}. Return ONLY JSON:
{{"sections":[{{"section":"E","section_title":"Long Answer Questions","marks_each":{long_marks},"questions":[{{"q_no":{s},"question":"actual detailed question","answer":"comprehensive 4-5 sentence answer"}}]}}]}}
{NO_DOTS}""")

        # Merge: build header from input data; collect only non-empty sections
        paper_data = {
            'paper_title': (part1 or {}).get('paper_title',
                            f'{subject} — {chapter}'),
            'subject':      subject,
            'class':        class_name,
            'chapter':      chapter,
            'total_marks':  total_marks,
            'time_allowed': '3 Hours' if language != 'Hindi' else '3 घंटे',
            'sections': [],
        }
        for sec in [sec_a, sec_b, sec_c, sec_d, sec_e]:
            if sec:
                paper_data['sections'].append(sec)

        if not paper_data['sections']:
            return JsonResponse({'error': 'AI could not generate any questions. Please try again.'}, status=500)

        paper_data = json.loads(json.dumps(paper_data))  # validate round-trip

        # ── Server-side quality gate (defensive) ─────────────────────────
        # The validator is best-effort — if it itself blows up on some odd
        # AI output, we default to quality_ok=True so the paper still saves.
        try:
            quality_ok = _is_paper_quality_ok(paper_data)
        except Exception:
            logger.exception("Quality validator crashed — treating as OK")
            quality_ok = True
        if not quality_ok:
            logger.warning(
                "Paper quality check failed — inserting with warning. "
                "subject=%s chapter=%s user=%s",
                subject, chapter, request.user.pk,
            )

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

        return JsonResponse({
            'success':         True,
            'paper':           paper_data,
            'paper_id':        history.pk,
            'quality_warning': not quality_ok,
        })

    except Exception as exc:
        logger.exception("generate_question_paper_ai error")
        # Include the exception class + message in the client response so we
        # can see WHY generation is failing (e.g. AI timeout, DB error, JSON
        # parse). Full traceback still goes to server log.
        return JsonResponse({
            'error': f'Could not generate the paper. Please try again. '
                     f'[Debug: {type(exc).__name__}: {str(exc)[:200]}]'
        }, status=500)


@login_required
@require_POST
def delete_question_from_paper(request, paper_id):
    """Delete a single question from a saved question paper.

    Body (JSON): {"section": "A", "q_no": 3}
    - Removes that question from paper.paper_json.sections[X].questions
    - Renumbers the remaining questions in that section (1..N)
    - Recomputes total_marks
    - Owner-only (paper.user == request.user)

    Returns updated paper_json, new total_marks, and remaining question count.
    """
    from ..models import QuestionPaperHistory

    try:
        paper = QuestionPaperHistory.objects.get(pk=paper_id, user=request.user)
    except QuestionPaperHistory.DoesNotExist:
        return JsonResponse({'error': 'Paper not found or not yours.'}, status=404)

    try:
        payload = json.loads(request.body or '{}')
        target_section = str(payload.get('section', '')).strip()
        target_q_no    = int(payload.get('q_no'))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid section or q_no.'}, status=400)

    paper_json = paper.paper_json or {}
    sections = paper_json.get('sections', []) or []

    removed = False
    new_total_marks = 0

    for sec in sections:
        if str(sec.get('section', '')).strip() == target_section:
            qs = sec.get('questions', []) or []
            kept = [q for q in qs if int(q.get('q_no', 0)) != target_q_no]
            if len(kept) != len(qs):
                removed = True
            # Renumber the section's remaining questions
            for idx, q in enumerate(kept, start=1):
                q['q_no'] = idx
            sec['questions'] = kept
        # Contribute this (possibly-untouched) section's marks to the running total
        marks_each = float(sec.get('marks_each', 0) or 0)
        new_total_marks += marks_each * len(sec.get('questions', []) or [])

    if not removed:
        return JsonResponse({'error': 'Question not found in that section.'}, status=404)

    # Drop any empty sections so the paper stays clean
    sections = [s for s in sections if s.get('questions')]
    paper_json['sections'] = sections
    paper_json['total_marks'] = int(new_total_marks) if new_total_marks.is_integer() else new_total_marks

    paper.paper_json  = paper_json
    paper.total_marks = paper_json['total_marks']
    paper.save(update_fields=['paper_json', 'total_marks'])

    logger.info('delete_question_from_paper: paper=%s section=%s q_no=%s new_total=%s',
                paper_id, target_section, target_q_no, paper_json['total_marks'])

    return JsonResponse({
        'success': True,
        'paper': paper_json,
        'total_marks': paper_json['total_marks'],
        'remaining_questions': sum(len(s.get('questions', []) or []) for s in sections),
    })


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
    papers_dict = {
        p.pk: {
            'paper': p.paper_json,
            'language': p.language,
            'difficulty': p.difficulty,
            'time_allowed': p.time_allowed,
            'school_name': school_name,
        }
        for p in papers
    }
    return render(request, 'school_app/question_paper/question_paper_history.html', {
        'papers': papers,
        'school_name': school_name,
        'papers_json': json.dumps(papers_dict, ensure_ascii=False),
    })
