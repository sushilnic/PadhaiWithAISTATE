"""
Chat / AI tutor views.
"""
import base64
import io
import json
import logging

from django.conf import settings
from django.utils import timezone
from PIL import Image

#from school_project.school_app.views.auth import student_required
from .auth import student_required
from .utils import *
from .utils import _strip_think
from ..models import AISathiClass, AISathiSubject, AISathiChapter

logger = logging.getLogger(__name__)

# ── AI Sathi limits from settings ────────────────────────────────────────────
_MSG_LIMIT   = getattr(settings, 'AI_SATHI_MSG_LIMIT',   20)
_SESSION_MINS = getattr(settings, 'AI_SATHI_SESSION_MINS', 30)

# ── Singleton Sarvam client ───────────────────────────────────────────────────
_sarvam_key = os.getenv("SARVAM_API_KEY")
SARVAM_MODEL = os.getenv("SARVAM_MODEL", "sarvam-m")
SARVAM_MAX_TOKENS = int(os.getenv("SARVAM_MAX_TOKENS", "4000"))
if _sarvam_key:
    _sarvam_client = SarvamAI(api_subscription_key=_sarvam_key)
else:
    _sarvam_client = None
    logger.warning("SARVAM_API_KEY is not set — AI chat features will be unavailable")


def _get_client():
    if _sarvam_client is None:
        raise RuntimeError("Sarvam AI is not configured (SARVAM_API_KEY missing)")
    return _sarvam_client


def _build_system_prompt(class_level, subject, chapter, language, description=''):
    """Build a system prompt in the target language for better native responses."""
    ctx = f"\n{description}" if description else ""
    if language == 'Hindi':
        return (
            f"आप एक सरकारी स्कूल शिक्षक हैं।\n"
            f"कक्षा: {class_level}\nविषय: {subject}\nअध्याय: {chapter}{ctx}\n\n"
            "नियम:\n"
            "- केवल इसी अध्याय से उत्तर दें\n"
            "- NCERT पाठ्यपुस्तक की भाषा का प्रयोग करें\n"
            "- चरण-दर-चरण व्याख्या करें\n"
            "- पाठ्यक्रम से बाहर के प्रश्नों पर विनम्रतापूर्वक मना करें\n"
            "- चरणों के बीच कोई खाली पंक्ति नहीं। प्रत्येक चरण अपनी पंक्ति पर।"
        )
    return (
        f"You are a government school teacher.\n"
        f"Class: {class_level}\nSubject: {subject}\nChapter: {chapter}{ctx}\n"
        f"Language: Respond in {language}\n\n"
        "Rules:\n"
        "- Answer ONLY from this chapter\n"
        "- Use NCERT textbook language\n"
        "- Step-by-step explanation\n"
        "- If outside syllabus, politely refuse\n"
        "- NO blank lines between steps. Each step on its own line only."
    )


def _get_chapter_description(class_level, subject, chapter):
    """Fetch chapter description from DB for richer system prompt context."""
    try:
        chap = AISathiChapter.objects.get(
            subject__class_ref__number=int(class_level),
            subject__name=subject,
            name=chapter,
            is_active=True,
        )
        return chap.description or ''
    except Exception:
        return ''


def _call_sarvam(api_messages, b64_image=None):
    """Call Sarvam API (text) or OpenAI (image fallback). Returns (reply_str, error_str)."""
    if b64_image:
        # Sarvam-105b does not support vision — go straight to OpenAI
        return _call_openai_vision(api_messages, b64_image)

    try:
        response = _get_client().chat.completions(
            model=SARVAM_MODEL, messages=api_messages, temperature=0.2, max_tokens=SARVAM_MAX_TOKENS, top_p=0.5,
        )
        _m = response.choices[0].message
        _r = _m.content or getattr(_m, 'reasoning_content', None) or ''
        return _strip_think(_r), None
    except Exception as e:
        return None, str(e)


def _call_openai_vision(api_messages, b64_image):
    """Use OpenAI gpt-4o-mini for image-based AI Sathi queries."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return None, "Image analysis requires OpenAI (OPENAI_API_KEY not configured)"
    try:
        import openai as openai_lib
        oai_client = openai_lib.OpenAI(api_key=openai_key)
        # Inject image into last user message
        messages_copy = [dict(m) for m in api_messages]
        last = messages_copy[-1]
        if last["role"] == "user":
            text = last["content"] if isinstance(last["content"], str) else ""
            last["content"] = [
                {"type": "text",      "text": text},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
            ]
        resp = oai_client.chat.completions.create(
            model="gpt-4o-mini", messages=messages_copy, temperature=0.2, max_tokens=4096,
        )
        return resp.choices[0].message.content, None
    except Exception as e:
        return None, str(e)


def _save_to_db(request, class_level, subject, chapter, language, user_prompt, reply):
    """Persist session + messages to DB. Returns assistant AISathiMessage id or None."""
    try:
        from ..models import AISathiChatSession, AISathiMessage
        if not request.session.session_key:
            request.session.save()
        session_key = request.session.session_key or ''
        # student FK if logged-in student session
        student_id = request.session.get('student_id')
        student_obj = None
        if student_id:
            from ..models import Student
            try:
                student_obj = Student.objects.get(id=student_id)
            except Student.DoesNotExist:
                pass

        chat_session, _ = AISathiChatSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'class_level': class_level,
                'subject': subject,
                'chapter': chapter,
                'language': language,
                'student': student_obj,
            },
        )
        AISathiMessage.objects.create(session=chat_session, role='user', content=user_prompt)
        msg_obj = AISathiMessage.objects.create(session=chat_session, role='assistant', content=reply)
        return msg_obj.id
    except Exception as e:
        from django.db.utils import ProgrammingError, OperationalError
        if isinstance(e, (ProgrammingError, OperationalError)):
            logger.debug("ai_sathi: DB tables not yet migrated — skipping persistence")
        else:
            logger.exception("ai_sathi: DB save failed")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# VIEWS
# ─────────────────────────────────────────────────────────────────────────────

def chat_view(request):
    history = request.session.get("history", [])

    if request.GET.get("clear") == "1":
        request.session["history"] = []
        return redirect("chat_page")

    if request.method == "POST":
        user_prompt = (request.POST.get("prompt") or "").strip()
        if user_prompt:
            history.append({"role": "user", "content": user_prompt})
            try:
                response = _get_client().chat.completions(
                    model=SARVAM_MODEL, messages=history, temperature=0.3, max_tokens=SARVAM_MAX_TOKENS, top_p=0.9,
                )
                _m = response.choices[0].message
                _r = _m.content or getattr(_m, 'reasoning_content', None) or ''
                assistant_reply = _strip_think(_r)
            except Exception:
                logger.exception("chat_view: Sarvam AI call failed")
                assistant_reply = "Sorry, something went wrong. Please try again."
            history.append({"role": "assistant", "content": assistant_reply})
            request.session["history"] = history

    return render(request, "school_app/chat/chat_page.html", {"history": history})


def chat_smart_tutor(request):
    """Main AI Sathi page — renders shell; chat is handled by AJAX endpoint."""
    history = request.session.get("history", [])

    if request.GET.get("clear") == "1":
        for key in ['history', 'guardrail_set', 'class_level', 'subject', 'chapter', 'language', 'session_start']:
            request.session.pop(key, None)
        return redirect("ai_sathi")

    # Legacy: support old direct-POST on page load (first visit guardrail save)
    if request.method == "POST" and not request.session.get("guardrail_set"):
        request.session["class_level"] = request.POST.get("class_level", "")
        request.session["subject"] = request.POST.get("subject", "")
        request.session["chapter"] = request.POST.get("chapter", "")
        request.session["language"] = request.POST.get("language", "Hindi")
        request.session["guardrail_set"] = True
        request.session["session_start"] = timezone.now().isoformat()

    class_level = request.session.get("class_level")
    subject     = request.session.get("subject")
    chapter     = request.session.get("chapter")
    language    = request.session.get("language", "Hindi")

    MSG_LIMIT    = _MSG_LIMIT
    SESSION_MINS = _SESSION_MINS

    user_msgs  = [m for m in history if m.get("role") == "user"]
    msg_count  = len(user_msgs)
    msgs_left  = max(0, MSG_LIMIT - msg_count)
    limit_reached = msg_count >= MSG_LIMIT

    mins_left = SESSION_MINS
    if class_level:
        start_iso = request.session.get("session_start")
        if start_iso:
            try:
                from datetime import datetime
                start_dt = datetime.fromisoformat(start_iso)
                elapsed = int((timezone.now() - start_dt).total_seconds() / 60)
                mins_left = max(0, SESSION_MINS - elapsed)
            except Exception:
                pass

    ai_classes = list(AISathiClass.objects.filter(is_active=True).values_list('number', flat=True))

    return render(request, "school_app/chat/chat_smart_tutor.html", {
        "history":        history,
        "guardrail":      class_level,
        "language":       language,
        "msg_count":      msg_count,
        "msg_limit":      MSG_LIMIT,
        "msgs_left":      msgs_left,
        "limit_reached":  limit_reached,
        "mins_left":      mins_left,
        "session_expired": mins_left == 0 and bool(class_level),
        "ai_classes":     ai_classes,
    })


@require_http_methods(["POST"])
@rate_limit(max_calls=30, period=60)
def ai_sathi_chat_ajax(request):
    """AJAX endpoint: receive prompt + optional image, return JSON reply."""
    history = request.session.get("history", [])

    # Set guardrail on first message
    if not request.session.get("guardrail_set"):
        request.session["class_level"]   = request.POST.get("class_level", "")
        request.session["subject"]        = request.POST.get("subject", "")
        request.session["chapter"]        = request.POST.get("chapter", "")
        request.session["language"]       = request.POST.get("language", "Hindi")
        request.session["guardrail_set"]  = True
        request.session["session_start"]  = timezone.now().isoformat()

    class_level = request.session.get("class_level", "")
    subject     = request.session.get("subject", "")
    chapter     = request.session.get("chapter", "")
    language    = request.session.get("language", "Hindi")

    user_prompt = request.POST.get("prompt", "").strip()
    if not user_prompt:
        return JsonResponse({"error": "Empty prompt"}, status=400)

    # Check message limit
    user_msgs = [m for m in history if m.get("role") == "user"]
    if len(user_msgs) >= _MSG_LIMIT:
        return JsonResponse({"error": "limit_reached"}, status=429)

    # Process optional image (decompression-bomb safe)
    b64_image = None
    image_file = request.FILES.get("image")
    if image_file:
        raw = image_file.read()
        if len(raw) > 5 * 1024 * 1024:
            return JsonResponse({"error": "Image too large (max 5 MB)."}, status=400)
        try:
            img = open_image_safely(raw, mode="RGB")
            img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70, optimize=True)
            b64_image = base64.b64encode(buf.getvalue()).decode("utf-8")
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

    # Build system prompt (with chapter description for richer context)
    description = _get_chapter_description(class_level, subject, chapter)
    system_prompt = _build_system_prompt(class_level, subject, chapter, language, description)

    # Only send last 6 messages to API (3 turns) to reduce token cost
    recent = history[-6:] if len(history) > 6 else history
    api_messages = (
        [{"role": "system", "content": system_prompt}]
        + [{"role": m["role"], "content": m["content"]} for m in recent]
        + [{"role": "user", "content": user_prompt}]
    )

    reply, error = _call_sarvam(api_messages, b64_image)
    if not reply:
        logger.error("ai_sathi_chat_ajax: Sarvam failed — %s", error)
        return JsonResponse({"error": "AI service error. Please try again."}, status=503)

    now_ts = timezone.now().strftime("%I:%M %p")
    history.append({"role": "user",      "content": user_prompt, "timestamp": now_ts})
    history.append({"role": "assistant", "content": reply,        "timestamp": now_ts})

    # Cap session history at MSG_LIMIT * 2 messages
    if len(history) > _MSG_LIMIT * 2:
        history = history[-(_MSG_LIMIT * 2):]
    request.session["history"] = history

    # Persist to DB for analytics
    msg_db_id = _save_to_db(request, class_level, subject, chapter, language, user_prompt, reply)

    new_user_count = len([m for m in history if m.get("role") == "user"])
    msgs_left = max(0, _MSG_LIMIT - new_user_count)

    return JsonResponse({
        "reply":         reply,
        "timestamp":     now_ts,
        "msg_count":     new_user_count,
        "msgs_left":     msgs_left,
        "limit_reached": msgs_left == 0,
        "msg_db_id":     msg_db_id,
    })


@require_http_methods(["POST"])
def ai_sathi_clear(request):
    """AJAX: clear chat session without page reload."""
    for key in ['history', 'guardrail_set', 'class_level', 'subject', 'chapter', 'language', 'session_start']:
        request.session.pop(key, None)
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def ai_sathi_change_chapter(request):
    """AJAX: reset guardrail (show selector again) but keep message count summary."""
    for key in ['guardrail_set', 'class_level', 'subject', 'chapter', 'language', 'session_start']:
        request.session.pop(key, None)
    # Keep history in session but clear it from the UI perspective
    request.session.pop('history', None)
    return JsonResponse({"ok": True})


@require_http_methods(["POST"])
def ai_sathi_feedback(request):
    """AJAX: store 👍/👎 rating against a persisted AISathiMessage."""
    try:
        from ..models import AISathiMessage
        msg_id = int(request.POST.get("msg_id", 0))
        rating = int(request.POST.get("rating", 0))
        if rating not in (1, -1):
            return JsonResponse({"ok": False, "error": "Invalid rating"}, status=400)
        AISathiMessage.objects.filter(id=msg_id, role='assistant').update(rating=rating)
        return JsonResponse({"ok": True})
    except Exception as e:
        from django.db.utils import ProgrammingError, OperationalError
        if not isinstance(e, (ProgrammingError, OperationalError)):
            logger.exception("ai_sathi_feedback: error")
        return JsonResponse({"ok": False}, status=400)


@require_http_methods(["GET"])
def ai_sathi_starters(request):
    """Return chapter-specific starter questions from DB, or language-appropriate defaults."""
    try:
        class_number = int(request.GET.get('class', ''))
        subject_name = request.GET.get('subject', '').strip()
        chapter_name = request.GET.get('chapter', '').strip()
    except (ValueError, TypeError):
        return JsonResponse({'starters': []})

    language = request.GET.get('language', 'Hindi').strip()
    if language not in ('Hindi', 'English'):
        language = 'Hindi'

    starters = []
    try:
        chap = AISathiChapter.objects.get(
            subject__class_ref__number=class_number,
            subject__name=subject_name,
            name=chapter_name,
            is_active=True,
        )
        starters = chap.starter_questions or []
    except Exception:
        pass

    if not starters:
        starters = _DEFAULT_STARTERS_HI if language == 'Hindi' else _DEFAULT_STARTERS_EN
    return JsonResponse({'starters': starters})


_DEFAULT_STARTERS_EN = [
    "What is this chapter about?",
    "Give me key formulas / definitions",
    "Explain with a real-life example",
    "What are common exam questions?",
    "Quiz me on this chapter",
    "Solve a practice problem step by step",
    "What mistakes do students commonly make here?",
    "How is this topic connected to real life?",
    "Explain this like I'm a beginner",
    "Give me a memory trick to remember this",
    "What should I revise before this chapter?",
    "Create a short summary I can use for revision",
]

_DEFAULT_STARTERS_HI = [
    "यह अध्याय किस बारे में है?",
    "मुख्य सूत्र / परिभाषाएं बताइए",
    "वास्तविक जीवन के उदाहरण से समझाइए",
    "इस अध्याय से परीक्षा में क्या प्रश्न आते हैं?",
    "इस अध्याय पर मेरा क्विज़ लीजिए",
    "एक अभ्यास प्रश्न चरण-दर-चरण हल कीजिए",
    "इस अध्याय में विद्यार्थी कौन-सी सामान्य गलतियां करते हैं?",
    "यह विषय वास्तविक जीवन से कैसे जुड़ा है?",
    "इसे आसान भाषा में शुरुआती की तरह समझाइए",
    "इसे याद रखने का कोई आसान तरीका बताइए",
    "इस अध्याय से पहले मुझे क्या दोहराना चाहिए?",
    "पुनरावृत्ति के लिए एक संक्षिप्त सारांश बनाइए",
]


def ask_pai(request):
    """AI-powered question answering interface using Sarvam AI."""
    answer = None
    question = ""

    if request.method == "POST":
        question = request.POST.get("question", "").strip()
        if not question:
            answer = "Please enter your question before submitting."
            return render(request, "school_app/chat/ask_pai.html", {"question": question, "answer": answer})

        messages = [
            {"role": "system", "content": """You are an experienced mathematics teacher. Solve the questions given, following these guidelines:
                1. Include step-by-step solutions
                2. Use LaTeX formatting for mathematical expressions (use $ for inline math and $$ for display math)
                3. Show complete solution with final answers written as Final Answer: <answer>
                4. Ensure that the last step, with the final value of the variable, is displayed at the end of the solution. The value should be in numbers, do not write an unsolved equation as the final value
                5. Whenever showing the solution, first explain the concept that is being tested by the question in simple terms
                6. While explaining a concept, besides giving an example, also give a counter-example at the beginning. That always makes things clear
                7. Any time you write a solution, explain the solution in a way that is extremely easy to understand by children struggling with complex technical terms
                8. Whenever trying to explain in simple terms: 1. use colloquial local language terms and try to avoid technical terms. When using technical terms, re explain those terms in local colloquial terms
                9. Recheck the solution for any mistakes
                10. If an image is provided, analyze it carefully as it may contain important visual information needed to solve the problem
                 Rules: NO blank lines between steps. Each step on its own line only.\n         """},
            {"role": "user", "content": question},
        ]

        try:
            response = _get_client().chat.completions(model=SARVAM_MODEL, messages=messages, temperature=0.2, max_tokens=SARVAM_MAX_TOKENS, top_p=0.5,)
            _m = response.choices[0].message
            _r = _m.content or getattr(_m, 'reasoning_content', None) or ''
            answer = _strip_think(_r)
        except ApiError as e:
            logger.error("ask_pai: Sarvam API error status=%s body=%s", e.status_code, e.body)
            answer = "AI service returned an error. Please try again."
        except Exception:
            logger.exception("ask_pai: unexpected error during AI call")
            answer = "Something went wrong. Please try again."

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO chat_history (question, answer, use_model, school_id)"
                    " VALUES (%s, %s, %s, %s)",
                    [question, answer, "SARVAM", None],
                )
        except Exception:
            logger.exception("ask_pai: failed to save to chat_history")

    return render(request, "school_app/chat/ask_pai.html", {"question": question, "answer": answer})


@require_http_methods(["GET", "POST"])
@student_required
def student_doubt_solver(request):
    """AI Doubt Solver — Try Sarvam first; fall back to OpenAI on any error."""
    if request.method == "GET":
        return render(request, 'school_app/student/student_doubt_solver.html')

    import requests as http_requests
    from PIL import Image

    question_text = request.POST.get("question", "").strip()
    image_file    = request.FILES.get("image")

    if not image_file and not question_text:
        return JsonResponse({"error": "Please provide an image or type your question."}, status=400)

    system_prompt = (
        "You are a helpful teacher for class 10 students.\n"
        "IMPORTANT: First check if the question or image is related to an academic/educational subject "
        "(Mathematics, Science, Social Studies, English, Hindi, or any school subject). "
        "If the content is NOT related to education (e.g. personal photos, memes, food, selfies, adult content, unrelated objects), "
        "respond with exactly this one line and nothing else: NOT_EDUCATIONAL\n"
        "If it IS educational, be concise and compact. NO blank lines between steps. Each step on its own line only.\n"
        "Format: **Topic:** one line. **Solution:** steps numbered 1,2,3... **Final Answer:** last line.\n"
        "Use LaTeX: $inline$ or $$display$$. Answer in the same language as the question or image."
    )

    b64 = None
    prompt_text = question_text if question_text else "Please read the problem in this image and solve it step by step."
    if image_file:
        raw = image_file.read()
        if len(raw) > 5 * 1024 * 1024:
            return JsonResponse({"error": "Image too large. Please upload an image under 5 MB."}, status=400)
        try:
            img = open_image_safely(raw, mode="RGB")
            img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

    sarvam_answer = None
    sarvam_error  = None
    if SARVAM_API_KEY:
        try:
            if b64:
                payload = {
                    "model": "sarvam-105b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text",      "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ]},
                    ],
                    "temperature": 0.3, "max_tokens": SARVAM_MAX_TOKENS, "top_p": 0.9,
                }
                resp = http_requests.post(
                    "https://api.sarvam.ai/v1/chat/completions",
                    headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                    data=json.dumps(payload), timeout=60,
                )
                if resp.status_code == 200:
                    sarvam_answer = resp.json()["choices"][0]["message"]["content"]
                else:
                    sarvam_error = f"Sarvam {resp.status_code}: {resp.text[:200]}"
            else:
                response = _get_client().chat.completions(
                    model=SARVAM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": question_text},
                    ],
                    temperature=0.3, max_tokens=SARVAM_MAX_TOKENS, top_p=0.9,
                )
                _m = response.choices[0].message
                _r = _m.content or getattr(_m, 'reasoning_content', None) or ''
                sarvam_answer = _strip_think(_r)
        except Exception as e:
            sarvam_error = str(e)

    NOT_EDU_MSG = "This image or question does not appear to be related to any school subject. Please upload a photo of a textbook problem, handwritten question, or type an academic question."

    if sarvam_answer:
        if sarvam_answer.strip() == "NOT_EDUCATIONAL":
            return JsonResponse({"error": NOT_EDU_MSG}, status=400)
        return JsonResponse({"answer": sarvam_answer})

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return JsonResponse({"error": f"Sarvam failed ({sarvam_error}) and OpenAI is not configured."}, status=503)

    try:
        import openai as openai_lib
        oai_client = openai_lib.OpenAI(api_key=openai_key)
        if b64:
            oai_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text",      "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ]},
            ]
        else:
            oai_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": question_text},
            ]
        resp = oai_client.chat.completions.create(
            model="gpt-4o-mini", messages=oai_messages, temperature=0.3, max_tokens=4096,
        )
        oai_answer = resp.choices[0].message.content
        if oai_answer.strip() == "NOT_EDUCATIONAL":
            return JsonResponse({"error": NOT_EDU_MSG}, status=400)
        return JsonResponse({"answer": oai_answer})
    except ImportError:
        logger.error('student_doubt_solver: openai package not installed')
        return JsonResponse({"error": "AI service is not available."}, status=503)
    except Exception:
        logger.exception('student_doubt_solver: all AI services failed. sarvam_error=%s', sarvam_error)
        return JsonResponse({"error": "AI service is temporarily unavailable. Please try again."}, status=500)


@require_http_methods(["GET"])
def ai_sathi_subjects(request):
    try:
        class_number = int(request.GET.get('class', ''))
    except (ValueError, TypeError):
        return JsonResponse({'subjects': []})
    try:
        cls = AISathiClass.objects.get(number=class_number, is_active=True)
    except AISathiClass.DoesNotExist:
        return JsonResponse({'subjects': []})
    subjects = list(cls.subjects.filter(is_active=True).order_by('order', 'name').values_list('name', flat=True))
    return JsonResponse({'subjects': subjects})


@require_http_methods(["GET"])
def ai_sathi_chapters(request):
    try:
        class_number = int(request.GET.get('class', ''))
    except (ValueError, TypeError):
        return JsonResponse({'chapters': []})
    subject_name = request.GET.get('subject', '').strip()
    if not subject_name:
        return JsonResponse({'chapters': []})
    try:
        subj = AISathiSubject.objects.get(
            class_ref__number=class_number, class_ref__is_active=True,
            name=subject_name, is_active=True,
        )
    except AISathiSubject.DoesNotExist:
        return JsonResponse({'chapters': []})
    chapters = list(subj.chapters.filter(is_active=True).order_by('order', 'id').values_list('name', flat=True))
    return JsonResponse({'chapters': chapters})
