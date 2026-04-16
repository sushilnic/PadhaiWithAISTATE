"""
Chat / AI tutor views.
"""
import logging
from .utils import *
from .utils import _strip_think
from ..models import AISathiClass, AISathiSubject, AISathiChapter

logger = logging.getLogger(__name__)

# ── Singleton Sarvam client ───────────────────────────────────────────────────
# Created once at startup. If the key is missing we set it to None and log a
# warning — the module still imports cleanly and every other URL keeps working.
_sarvam_key = os.getenv("SARVAM_API_KEY")
if _sarvam_key:
    _sarvam_client = SarvamAI(api_subscription_key=_sarvam_key)
else:
    _sarvam_client = None
    logger.warning("SARVAM_API_KEY is not set — AI chat features will be unavailable")


def _get_client():
    """Return the shared Sarvam client. Raises RuntimeError if not configured."""
    if _sarvam_client is None:
        raise RuntimeError("Sarvam AI is not configured (SARVAM_API_KEY missing)")
    return _sarvam_client


def chat_view(request):
    # Get or create history from session
    history = request.session.get("history", [])

    # Clear chat if ?clear=1
    if request.GET.get("clear") == "1":
        request.session["history"] = []
        return redirect("chat_page")

    if request.method == "POST":
        user_prompt = (request.POST.get("prompt") or "").strip()

        if user_prompt:
            # 1. Add user message
            history.append({"role": "user", "content": user_prompt})

            # 2. Call Sarvam AI — wrapped in try/except so API failures
            #    return a friendly message instead of crashing with 500
            try:
                response = _get_client().chat.completions(
                    messages=history,
                    temperature=0.3,
                    max_tokens=2000,
                    top_p=0.9,
                )
                assistant_reply = _strip_think(response.choices[0].message.content)
            except Exception:
                logger.exception("chat_view: Sarvam AI call failed")
                assistant_reply = "Sorry, something went wrong. Please try again."

            # 3. Add assistant message
            history.append({"role": "assistant", "content": assistant_reply})

            # 4. Save updated history in session
            request.session["history"] = history

    # Render template with full history
    return render(request, "school_app/chat/chat_page.html", {"history": history})


def chat_smart_tutor(request):
    history = request.session.get("history", [])

    if request.GET.get("clear") == "1":
        for key in ['history', 'guardrail_set', 'class_level', 'subject', 'chapter', 'language', 'session_start']:
            request.session.pop(key, None)
        return redirect("ai_sathi")

    # Store guardrail once
    if request.method == "POST":
        if not request.session.get("guardrail_set"):
            request.session["class_level"] = request.POST.get("class_level")
            request.session["subject"] = request.POST.get("subject")
            request.session["chapter"] = request.POST.get("chapter")
            request.session["language"] = request.POST.get("language", "Hindi")
            request.session["guardrail_set"] = True
            request.session["session_start"] = timezone.now().isoformat()

    class_level = request.session.get("class_level")
    subject = request.session.get("subject")
    chapter = request.session.get("chapter")
    language = request.session.get("language", "Hindi")

    if request.method == "POST":
        user_prompt = request.POST.get("prompt", "").strip()

        if user_prompt:
            system_prompt = f"""
                    You are a government school teacher.

                    Class: {class_level}
                    Subject: {subject}
                    Chapter: {chapter}
                    Language: Respond in {language}

                    Rules:
                    - Answer ONLY from this chapter
                    - Use NCERT textbook language
                    - Step-by-step explanation
                    - If outside syllabus, politely refuse
                    - NO blank lines between steps. Each step on its own line only
                    """

            api_messages = (
                [{"role": "system", "content": system_prompt}]
                + [{"role": m["role"], "content": m["content"]} for m in history]
                + [{"role": "user", "content": user_prompt}]
            )

            now_ts = timezone.now().strftime("%I:%M %p")

            try:
                response = _get_client().chat.completions(
                    messages=api_messages, temperature=0.2,
                    max_tokens=2000, top_p=0.5,
                )
                reply = _strip_think(response.choices[0].message.content)
            except Exception:
                logger.exception("chat_smart_tutor: Sarvam AI call failed")
                reply = "Sorry, something went wrong. Please try again."

            history.append({"role": "user", "content": user_prompt, "timestamp": now_ts})
            history.append({"role": "assistant", "content": reply, "timestamp": now_ts})

            # Cap history at 20 messages to prevent session overflow
            if len(history) > 20:
                history = history[-20:]

            request.session["history"] = history

    # Compute session stats for template
    MSG_LIMIT = 20
    SESSION_MINS = 30
    user_msgs = [m for m in history if m.get("role") == "user"]
    msg_count = len(user_msgs)
    msgs_left = max(0, MSG_LIMIT - msg_count)
    limit_reached = msg_count >= MSG_LIMIT

    mins_left = SESSION_MINS
    if class_level:
        start_iso = request.session.get("session_start")
        if start_iso:
            try:
                from datetime import datetime, timezone as dt_tz
                start_dt = datetime.fromisoformat(start_iso)
                elapsed_mins = int((timezone.now() - start_dt).total_seconds() / 60)
                mins_left = max(0, SESSION_MINS - elapsed_mins)
            except Exception:
                pass

    ai_classes = list(
        AISathiClass.objects.filter(is_active=True).values_list('number', flat=True)
    )

    return render(request, "school_app/chat/chat_smart_tutor.html", {
        "history": history,
        "guardrail": class_level,
        "language": request.session.get("language", "Hindi"),
        "msg_count": msg_count,
        "msg_limit": MSG_LIMIT,
        "msgs_left": msgs_left,
        "limit_reached": limit_reached,
        "mins_left": mins_left,
        "session_expired": mins_left == 0 and bool(class_level),
        "ai_classes": ai_classes,
    })


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
            response = _get_client().chat.completions(messages=messages, temperature=0.2, max_tokens=2000, top_p=0.5,)
            answer = _strip_think(response.choices[0].message.content)
        except ApiError as e:
            logger.error("ask_pai: Sarvam API error status=%s body=%s", e.status_code, e.body)
            answer = "AI service returned an error. Please try again."
        except Exception:
            logger.exception("ask_pai: unexpected error during AI call")
            answer = "Something went wrong. Please try again."

        # Save to chat_history — log failure silently, never show DB errors to user
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
def student_doubt_solver(request):
    """AI Doubt Solver — Try Sarvam first; fall back to OpenAI on any error."""
    if request.method == "GET":
        return render(request, 'school_app/student/student_doubt_solver.html')

    import base64, io, json, requests as http_requests
    from PIL import Image

    question_text = request.POST.get("question", "").strip()
    image_file = request.FILES.get("image")

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

    # Compress image once (reused by both Sarvam and OpenAI fallback)
    b64 = None
    prompt_text = question_text if question_text else "Please read the problem in this image and solve it step by step."
    if image_file:
        raw = image_file.read()
        if len(raw) > 5 * 1024 * 1024:
            return JsonResponse({"error": "Image too large. Please upload an image under 5 MB."}, status=400)
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            img.thumbnail((1024, 1024), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        except Exception:
            b64 = base64.b64encode(raw).decode("utf-8")

    # ── 1. Try Sarvam ──────────────────────────────────────────────────────────
    sarvam_answer = None
    sarvam_error = None
    if SARVAM_API_KEY:
        try:
            if b64:
                # Image: call REST directly (SDK only accepts str content)
                payload = {
                    "model": "sarvam-105b",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ]},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "top_p": 0.9,
                }
                resp = http_requests.post(
                    "https://api.sarvam.ai/v1/chat/completions",
                    headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=60,
                )
                if resp.status_code == 200:
                    sarvam_answer = resp.json()["choices"][0]["message"]["content"]
                else:
                    sarvam_error = f"Sarvam {resp.status_code}: {resp.text[:200]}"
            else:
                # Text-only: use shared singleton client
                response = _get_client().chat.completions(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question_text},
                    ],
                    temperature=0.3, max_tokens=2000, top_p=0.9,
                )
                sarvam_answer = _strip_think(response.choices[0].message.content)
        except Exception as e:
            sarvam_error = str(e)

    NOT_EDU_MSG = "This image or question does not appear to be related to any school subject. Please upload a photo of a textbook problem, handwritten question, or type an academic question."

    if sarvam_answer:
        if sarvam_answer.strip() == "NOT_EDUCATIONAL":
            return JsonResponse({"error": NOT_EDU_MSG}, status=400)
        return JsonResponse({"answer": sarvam_answer})

    # ── 2. Fallback: OpenAI ────────────────────────────────────────────────────
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
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ]},
            ]
        else:
            oai_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question_text},
            ]

        resp = oai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=oai_messages,
            temperature=0.3,
            max_tokens=4096,
        )
        oai_answer = resp.choices[0].message.content
        if oai_answer.strip() == "NOT_EDUCATIONAL":
            return JsonResponse({"error": NOT_EDU_MSG}, status=400)
        return JsonResponse({"answer": oai_answer})
    except ImportError:
        return JsonResponse({"error": "openai package not installed. Run: pip install openai"}, status=503)
    except Exception as e:
        return JsonResponse({"error": f"All AI services failed. Sarvam: {sarvam_error}. OpenAI: {str(e)}"}, status=500)


@require_http_methods(["GET"])
def ai_sathi_subjects(request):
    """Return active subjects for a given class number."""
    try:
        class_number = int(request.GET.get('class', ''))
    except (ValueError, TypeError):
        return JsonResponse({'subjects': []})

    try:
        cls = AISathiClass.objects.get(number=class_number, is_active=True)
    except AISathiClass.DoesNotExist:
        return JsonResponse({'subjects': []})

    subjects = list(
        cls.subjects.filter(is_active=True).order_by('order', 'name').values_list('name', flat=True)
    )
    return JsonResponse({'subjects': subjects})


@require_http_methods(["GET"])
def ai_sathi_chapters(request):
    """Return active chapters for a given class + subject."""
    try:
        class_number = int(request.GET.get('class', ''))
    except (ValueError, TypeError):
        return JsonResponse({'chapters': []})

    subject_name = request.GET.get('subject', '').strip()
    if not subject_name:
        return JsonResponse({'chapters': []})

    try:
        subj = AISathiSubject.objects.get(
            class_ref__number=class_number,
            class_ref__is_active=True,
            name=subject_name,
            is_active=True,
        )
    except AISathiSubject.DoesNotExist:
        return JsonResponse({'chapters': []})

    chapters = list(
        subj.chapters.filter(is_active=True).order_by('order', 'id').values_list('name', flat=True)
    )
    return JsonResponse({'chapters': chapters})
