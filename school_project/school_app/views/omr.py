"""OMR-based MCQ test: printable sheet generation and bubble detection."""
import base64
import io
import json
import logging

import numpy as np
from PIL import Image, ExifTags

from .utils import *

logger = logging.getLogger('school_app.views.omr')

# ── Optional packages (fail gracefully if not installed) ────────────────────
try:
    import cv2
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False

try:
    from pyzbar import pyzbar as _pyzbar
    _HAS_PYZBAR = True
except ImportError:
    _HAS_PYZBAR = False

try:
    from reportlab.lib.pagesizes import A4 as _RL_A4
    from reportlab.lib.units import mm as _RL_MM
    from reportlab.pdfgen import canvas as _rl_canvas
    from reportlab.lib import colors as _rl_colors
    from reportlab.lib.utils import ImageReader as _RL_ImageReader
    _HAS_REPORTLAB = True
except ImportError:
    _HAS_REPORTLAB = False

try:
    import qrcode as _qrcode_lib
    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False

# ── Sheet Layout Constants (mm, top-left origin) ────────────────────────────
_PAGE_W, _PAGE_H = 210, 297        # A4

# Corner registration mark centres and radius (mm)
_CORNER_TL = (12, 12)
_CORNER_TR = (198, 12)
_CORNER_BL = (12, 285)
_CORNER_BR = (198, 285)
_CORNER_R  = 8.0   # large so they dominate each image quadrant

# Warped processing image size — 10 px/mm of the inter-corner span
_CONTENT_W_MM = _CORNER_TR[0] - _CORNER_TL[0]  # 186 mm
_CONTENT_H_MM = _CORNER_BL[1] - _CORNER_TL[1]  # 273 mm
_WARP_W = _CONTENT_W_MM * 10                    # 1860 px
_WARP_H = _CONTENT_H_MM * 10                    # 2730 px
_SCX    = 10.0                                  # px per mm (exact)
_SCY    = 10.0

# QR code region (mm)
_QR_X, _QR_Y, _QR_SZ = 155, 22, 33

# Bubble grid (mm)
_COL1_Q_X = 32        # right edge of Q-number label, column 1
_COL2_Q_X = 126       # column 2
_COL1_A_X = 38        # centre of option-A bubble, column 1
_COL2_A_X = 132       # column 2
_OPT_STEP  = 9.0      # mm between option bubble centres
_GRID_TOP  = 87       # mm: y of first question row
_ROW_H     = 7.5      # mm between rows
_BUBBLE_R  = 3.0      # bubble radius mm
_MAX_PER_COL = 20     # questions per column (40 total)


def _sheet_to_warp_px(x_mm, y_mm):
    """Convert sheet (mm) to warped-image pixel coordinates."""
    px_x = (x_mm - _CORNER_TL[0]) * _SCX
    px_y = (y_mm - _CORNER_TL[1]) * _SCY
    return int(px_x), int(px_y)


def _bubble_centres_mm(num_q):
    """Return {idx: {opt: (x_mm, y_mm)}} for 0-based question indices."""
    centres = {}
    for i in range(min(num_q, _MAX_PER_COL * 2)):
        base_x = _COL1_A_X if i < _MAX_PER_COL else _COL2_A_X
        row    = i if i < _MAX_PER_COL else i - _MAX_PER_COL
        y      = _GRID_TOP + row * _ROW_H
        centres[i] = {
            'A': (base_x,                y),
            'B': (base_x + _OPT_STEP,   y),
            'C': (base_x + _OPT_STEP*2, y),
            'D': (base_x + _OPT_STEP*3, y),
        }
    return centres


def _collect_mcq(paper_json):
    """[(sec_id, q_no_str), ...] for sections A and B (OMR-compatible)."""
    rows = []
    for sec in paper_json.get('sections', []):
        if sec.get('section') in ('A', 'B'):
            for q in sec.get('questions', []):
                rows.append((sec['section'], str(q['q_no'])))
    return rows


# ── PDF Sheet Generator ─────────────────────────────────────────────────────

def _draw_one_sheet(c, assignment, student, q_list, centres):
    """Draw one student's OMR sheet as the current page on canvas c."""
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    import qrcode as _qr

    W, H = _RL_A4

    def ry(mm_top):
        return (_PAGE_H - mm_top) * _RL_MM

    # ── Corner registration marks (solid black, 8 mm radius) ──
    # Large solid circles — must be the biggest dark blob in each image quadrant.
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    for cx, cy in [_CORNER_TL, _CORNER_TR, _CORNER_BL, _CORNER_BR]:
        c.circle(cx * _RL_MM, ry(cy), _CORNER_R * _RL_MM, fill=1, stroke=0)

    # ── QR code (encodes paper_id + roll_number) ──
    qr_data = f"PAI:{assignment.pk}:{student.roll_number}"
    qr_img  = _qr.make(qr_data, border=1)
    qr_buf  = io.BytesIO()
    qr_img.save(qr_buf, format='PNG')
    qr_buf.seek(0)
    c.drawImage(ImageReader(qr_buf),
                _QR_X * _RL_MM, ry(_QR_Y + _QR_SZ),
                width=_QR_SZ * _RL_MM, height=_QR_SZ * _RL_MM)

    # ── Header ──
    c.setFont('Helvetica-Bold', 14)
    c.setFillColor(colors.HexColor('#1e3c72'))
    c.drawCentredString(W / 2, ry(13), 'PadhaiWithAI — OMR Answer Sheet')
    c.setFont('Helvetica', 8.5)
    c.setFillColor(colors.HexColor('#334155'))
    c.drawCentredString(W / 2, ry(20.5),
        f'{assignment.question_paper.subject}  ·  '
        f'{assignment.question_paper.chapter}  ·  '
        f'Class {assignment.class_name}  ·  '
        f'{assignment.question_paper.total_marks} marks')

    # ── Divider ──
    c.setStrokeColor(colors.HexColor('#cbd5e1'))
    c.setLineWidth(0.5)
    c.line(14 * _RL_MM, ry(25), 150 * _RL_MM, ry(25))

    # ── Student info box ──
    c.setStrokeColor(colors.HexColor('#1e3c72'))
    c.setFillColor(colors.HexColor('#eef2ff'))
    c.setLineWidth(0.8)
    c.roundRect(14 * _RL_MM, ry(63), 138 * _RL_MM, 37 * _RL_MM,
                3 * _RL_MM, fill=1, stroke=1)
    c.setFont('Helvetica-Bold', 9)
    c.setFillColor(colors.HexColor('#1e293b'))
    c.drawString(18 * _RL_MM, ry(37), f'Name:    {student.name}')
    c.drawString(18 * _RL_MM, ry(45), f'Roll No: {student.roll_number}')
    c.drawString(18 * _RL_MM, ry(53), f'Class:   {assignment.class_name}    |    Paper ID: {assignment.pk}')

    # ── Instructions ──
    c.setFont('Helvetica', 7.5)
    c.setFillColor(colors.HexColor('#475569'))
    c.drawString(14 * _RL_MM, ry(68),
        'Instructions: Fill the bubble COMPLETELY with blue/black pen. '
        'Do NOT tick, cross, or use pencil. Erase marks = wrong answer.')

    # ── Section labels ──
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#64748b'))
    prev_sec = None
    sec_starts = {}
    for idx, (sec_id, _) in enumerate(q_list[:_MAX_PER_COL * 2]):
        if sec_id != prev_sec:
            sec_starts[idx] = sec_id
            prev_sec = sec_id

    # ── Column headers ──
    def col_header(base_a_x, q_label_x):
        hy = _GRID_TOP - 6
        c.setFont('Helvetica-Bold', 8.5)
        c.setFillColor(colors.HexColor('#1e3c72'))
        c.drawRightString(q_label_x * _RL_MM, ry(hy) + 1, 'Q.')
        for j, opt in enumerate(['A', 'B', 'C', 'D']):
            c.drawCentredString((base_a_x + j * _OPT_STEP) * _RL_MM, ry(hy) + 1, opt)
        c.setStrokeColor(colors.HexColor('#94a3b8'))
        c.setLineWidth(0.3)
        c.line((q_label_x - 15) * _RL_MM, ry(_GRID_TOP - 2),
               (base_a_x + 3 * _OPT_STEP + 5) * _RL_MM, ry(_GRID_TOP - 2))

    col_header(_COL1_A_X, _COL1_Q_X)
    col_header(_COL2_A_X, _COL2_Q_X)

    # ── Bubbles ──
    for idx, (sec_id, q_no_str) in enumerate(q_list[:_MAX_PER_COL * 2]):
        is_tf   = (sec_id == 'B')
        col     = 0 if idx < _MAX_PER_COL else 1
        row     = idx if col == 0 else idx - _MAX_PER_COL
        q_lbl_x = _COL1_Q_X if col == 0 else _COL2_Q_X
        base_ax = _COL1_A_X if col == 0 else _COL2_A_X
        row_y   = _GRID_TOP + row * _ROW_H

        # Zebra stripe
        if row % 2 == 0:
            c.setFillColor(colors.HexColor('#f8fafc'))
            c.setStrokeColor(colors.transparent)
            c.rect((q_lbl_x - 15) * _RL_MM, ry(row_y + _ROW_H * 0.45),
                   84 * _RL_MM, _ROW_H * _RL_MM, fill=1, stroke=0)

        # Question label
        c.setFont('Helvetica', 7.5)
        c.setFillColor(colors.HexColor('#334155'))
        c.drawRightString(q_lbl_x * _RL_MM, ry(row_y) + 2, f'{idx + 1}.')

        # Section indicator for T/F
        if is_tf:
            c.setFont('Helvetica', 6)
            c.setFillColor(colors.HexColor('#7c3aed'))
            c.drawString(base_ax * _RL_MM, ry(row_y) - 3.5, 'T/F')

        # Draw 4 bubbles; shade unused ones (T/F only uses A and B)
        c.setLineWidth(0.7)
        for j in range(4):
            bx = base_ax + j * _OPT_STEP
            by = row_y
            unused = is_tf and j >= 2
            c.setFillColor(colors.HexColor('#e2e8f0') if unused else colors.white)
            c.setStrokeColor(colors.HexColor('#e2e8f0') if unused else colors.HexColor('#334155'))
            c.circle(bx * _RL_MM, ry(by), _BUBBLE_R * _RL_MM, fill=1, stroke=1)

    # ── Footer ──
    c.setFont('Helvetica', 7)
    c.setFillColor(colors.HexColor('#94a3b8'))
    c.drawCentredString(W / 2, ry(292.5),
        'PadhaiWithAI  ·  Do not fold, staple, or write outside designated areas')


@login_required
def download_omr_sheets(request, pk):
    """Download all students' OMR answer sheets as one multi-page PDF."""
    from ..models import AssignedPaper, Student

    if not (_HAS_REPORTLAB and _HAS_QRCODE):
        missing = [p for p, ok in [('reportlab', _HAS_REPORTLAB), ('qrcode', _HAS_QRCODE)] if not ok]
        messages.error(request,
            f'Missing packages: {", ".join(missing)}. '
            f'Run: pip install {" ".join(missing)}')
        return redirect('assignment_report', pk=pk)

    assignment = get_object_or_404(AssignedPaper, pk=pk, assigned_by=request.user)
    students   = Student.objects.filter(
        school=assignment.school, class_name=assignment.class_name, is_active=True
    ).order_by('roll_number')

    if not students.exists():
        messages.error(request, 'No active students found in this class.')
        return redirect('assignment_report', pk=pk)

    q_list = _collect_mcq(assignment.question_paper.paper_json)
    if not q_list:
        messages.error(request, 'This paper has no MCQ sections (A/B). OMR requires MCQ questions.')
        return redirect('assignment_report', pk=pk)

    centres = _bubble_centres_mm(min(len(q_list), _MAX_PER_COL * 2))
    buf     = io.BytesIO()
    c       = _rl_canvas.Canvas(buf, pagesize=_RL_A4)

    for student in students:
        _draw_one_sheet(c, assignment, student, q_list, centres)
        c.showPage()

    c.save()
    buf.seek(0)

    subj     = assignment.question_paper.subject.replace(' ', '_')
    filename = f'OMR_{subj}_Class{assignment.class_name}.pdf'
    resp     = HttpResponse(buf.read(), content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


# ── Image Processing Pipeline ───────────────────────────────────────────────

def _fix_exif_rotation(pil_img):
    try:
        exif = pil_img._getexif()
        if not exif:
            return pil_img
        for tag, val in exif.items():
            if ExifTags.TAGS.get(tag) == 'Orientation':
                rotations = {3: 180, 6: 270, 8: 90}
                if val in rotations:
                    return pil_img.rotate(rotations[val], expand=True)
    except Exception:
        pass
    return pil_img


def _sort_corners(pts):
    """Sort 4 (x, y) points → [TL, TR, BL, BR]."""
    by_y = sorted(pts, key=lambda p: p[1])
    top  = sorted(by_y[:2], key=lambda p: p[0])
    bot  = sorted(by_y[2:], key=lambda p: p[0])
    return [top[0], top[1], bot[0], bot[1]]


def _find_corner_marks(gray, img_w, img_h):
    """
    Find 4 registration mark centres.
    Returns [TL, TR, BL, BR] pixel coordinates, or None if any corner fails.

    Strategy: for each of the 4 image corners, find the circular blob that is
    CLOSEST to that corner within the relevant quadrant.
    This correctly ignores the QR code (which is further from the TR corner
    than the actual corner mark) and filled answer bubbles (which are central).
    """
    import math

    blurred = cv2.GaussianBlur(gray, (11, 11), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Corner marks are ~8 mm radius ≈ 200 mm² → at 10 px/mm ≈ 20 000 px².
    # At typical phone photo resolution (downscaled to 2800px max),
    # the inter-corner span fills most of the image, so scale accordingly.
    # Minimum: corner marks must be at least 0.03% of image area.
    min_area = max(400, img_w * img_h * 0.0003)

    circular_blobs = []  # (cx, cy, area)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue
        # Circularity: 1.0 = perfect circle. Use 0.60 to allow for printing artefacts.
        # A QR-code outer square has circularity ≈ 0.785, but its area is large;
        # we handle that below by preferring the blob CLOSEST to the image corner.
        if 4 * np.pi * area / (peri ** 2) > 0.60:
            M = cv2.moments(cnt)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                circular_blobs.append((cx, cy, area))

    if len(circular_blobs) < 4:
        return None

    # For each of the 4 image corners, search within the quadrant and pick
    # the blob NEAREST to that corner (not the largest).
    mx, my = img_w // 2, img_h // 2
    corner_targets = {
        'TL': (0,     0,     0,  0,  mx, my),
        'TR': (img_w, 0,     mx, 0,  img_w, my),
        'BL': (0,     img_h, 0,  my, mx, img_h),
        'BR': (img_w, img_h, mx, my, img_w, img_h),
    }

    corners = {}
    for label, (corner_x, corner_y, x1, y1, x2, y2) in corner_targets.items():
        best, best_dist = None, float('inf')
        for cx, cy, area in circular_blobs:
            if x1 <= cx < x2 and y1 <= cy < y2:
                dist = math.hypot(cx - corner_x, cy - corner_y)
                if dist < best_dist:
                    best_dist = dist
                    best = (cx, cy)
        if best:
            corners[label] = best

    if len(corners) < 4:
        return None

    return [corners['TL'], corners['TR'], corners['BL'], corners['BR']]


def _detect_with_opencv(image_bytes, paper_json):
    """
    OpenCV pipeline: QR decode → quadrant corner detection → perspective warp → bubble detection.
    Returns (roll_number, answers_dict, confidence_float, error_str_or_None).
    """
    if not _HAS_CV2:
        return None, {}, 0.0, 'opencv-python not installed — run: pip install opencv-python'

    # ── Load + EXIF-rotate + downscale ──
    pil = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    pil = _fix_exif_rotation(pil)
    w, h = pil.size
    if max(w, h) > 2800:
        scale = 2800 / max(w, h)
        pil   = pil.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        w, h  = pil.size

    img  = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Step 1: Decode QR code ──
    def _parse_qr_data(data):
        if data and data.startswith('PAI:'):
            parts = data.split(':')
            if len(parts) >= 3:
                return parts[2]
        return None

    def _qr_try_all(im):
        """
        Try every decode strategy on a numpy image (gray or BGR).
        Returns roll_number string or None.
        """
        detector = cv2.QRCodeDetector()

        # Build candidate images: original, gray, CLAHE, Otsu, inverted, upscaled
        if len(im.shape) == 3:
            g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        else:
            g = im
        candidates = [im, g]
        try:
            candidates.append(
                cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(g))
        except Exception:
            pass
        try:
            _, otsu = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            candidates += [otsu, cv2.bitwise_not(otsu)]
        except Exception:
            pass
        # Upscale small crops (phone photos make the QR tiny)
        if g.shape[0] < 500:
            try:
                sc = max(2, 500 // g.shape[0])
                candidates.append(
                    cv2.resize(g, (g.shape[1] * sc, g.shape[0] * sc),
                               interpolation=cv2.INTER_CUBIC))
            except Exception:
                pass

        for c in candidates:
            # OpenCV detector
            try:
                d, _, _ = detector.detectAndDecode(c)
                rn = _parse_qr_data(d)
                if rn:
                    logger.debug("QR decoded by OpenCV: %s", rn)
                    return rn
            except Exception:
                pass
            # pyzbar (needs `pip install pyzbar` + zbar DLL on Windows)
            if _HAS_PYZBAR:
                try:
                    for sym in _pyzbar.decode(c):
                        rn = _parse_qr_data(sym.data.decode('utf-8', errors='ignore'))
                        if rn:
                            logger.debug("QR decoded by pyzbar: %s", rn)
                            return rn
                except Exception:
                    pass
        return None

    roll_number = _qr_try_all(img)
    if not roll_number:
        logger.debug("QR not found on original image (size %dx%d)", w, h)

    # ── Step 2: Find corner registration marks (quadrant-based) ──
    corners_px = _find_corner_marks(gray, w, h)
    if corners_px is None:
        return roll_number, {}, 0.3, 'Corner marks not found in all 4 corners — re-print OMR sheet'

    # Validate: corners should form a roughly rectangular shape
    tl, tr, bl, br = corners_px
    top_width  = abs(tr[0] - tl[0])
    bot_width  = abs(br[0] - bl[0])
    left_height  = abs(bl[1] - tl[1])
    right_height = abs(br[1] - tr[1])

    if top_width < w * 0.3 or left_height < h * 0.3:
        return roll_number, {}, 0.3, 'Corner marks too close together — photograph entire sheet'

    width_ratio = min(top_width, bot_width) / max(top_width, bot_width)
    height_ratio = min(left_height, right_height) / max(left_height, right_height)
    if width_ratio < 0.7 or height_ratio < 0.7:
        return roll_number, {}, 0.35, 'Sheet appears tilted — photograph from directly above'

    # ── Step 3: Perspective warp ──
    src = np.float32(corners_px)
    dst = np.float32([[0, 0], [_WARP_W, 0], [0, _WARP_H], [_WARP_W, _WARP_H]])
    M_persp  = cv2.getPerspectiveTransform(src, dst)
    warped   = cv2.warpPerspective(gray, M_persp, (_WARP_W, _WARP_H))
    warped_c = cv2.warpPerspective(img,  M_persp, (_WARP_W, _WARP_H))  # color warp for QR

    # ── Step 3b: Retry QR on warped image if not found yet ──
    # After perspective correction the QR is axis-aligned and undistorted.
    if not roll_number:
        qr_px_x, qr_px_y   = _sheet_to_warp_px(_QR_X, _QR_Y)
        qr_px_x2, qr_px_y2 = _sheet_to_warp_px(_QR_X + _QR_SZ, _QR_Y + _QR_SZ)
        # 20% padding so quiet zone is fully included
        pad = int(_QR_SZ * _SCX * 0.20)
        y1c = max(0, qr_px_y - pad);  y2c = min(_WARP_H, qr_px_y2 + pad)
        x1c = max(0, qr_px_x - pad);  x2c = min(_WARP_W, qr_px_x2 + pad)
        qr_crop_color = warped_c[y1c:y2c, x1c:x2c]
        if qr_crop_color.size > 0:
            roll_number = _qr_try_all(qr_crop_color)
            if not roll_number:
                logger.debug("QR not found in warped crop [%d:%d, %d:%d]",
                             y1c, y2c, x1c, x2c)

    # ── Step 4: Adaptive threshold (handles uneven phone lighting) ──
    w_bin = cv2.adaptiveThreshold(
        cv2.GaussianBlur(warped, (5, 5), 0),
        255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
        blockSize=31, C=8,
    )

    # ── Step 5: Detect filled bubbles ──
    q_list  = _collect_mcq(paper_json)
    num_q   = min(len(q_list), _MAX_PER_COL * 2)
    centres = _bubble_centres_mm(num_q)
    r_px    = max(int(_BUBBLE_R * _SCX * 0.85), 6)   # slightly smaller than bubble

    raw, confidences = {}, []

    for idx in range(num_q):
        is_tf  = (q_list[idx][0] == 'B')
        opts   = ['A', 'B'] if is_tf else ['A', 'B', 'C', 'D']
        scores = []
        for opt in opts:
            bx_mm, by_mm = centres[idx][opt]
            bx_px, by_px = _sheet_to_warp_px(bx_mm, by_mm)
            x1 = max(0, bx_px - r_px)
            y1 = max(0, by_px - r_px)
            x2 = min(_WARP_W, bx_px + r_px)
            y2 = min(_WARP_H, by_px + r_px)
            roi  = w_bin[y1:y2, x1:x2]
            fill = float(np.sum(roi > 0)) / max(roi.size, 1)
            scores.append(fill)

        max_s  = max(scores) if scores else 0.0
        s_desc = sorted(scores, reverse=True)
        margin = (s_desc[0] - s_desc[1]) if len(s_desc) > 1 else s_desc[0]

        if max_s < 0.20:                          # nothing filled
            raw[idx] = None
            confidences.append(0.5)
        elif margin >= 0.12:                      # clear winner
            raw[idx] = opts[scores.index(max_s)]
            confidences.append(min(1.0, 0.6 + margin * 3))
        else:                                     # ambiguous — pick highest but low conf
            raw[idx] = opts[scores.index(max_s)]
            confidences.append(0.55)

    # ── Step 6: Map to answers dict ──
    TF_MAP  = {'A': 'True', 'B': 'False'}
    answers = {}
    for idx, (sec_id, q_no_str) in enumerate(q_list[:num_q]):
        answers.setdefault(sec_id, {})
        det = raw.get(idx)
        if det and sec_id == 'B':
            det = TF_MAP.get(det, det)
        answers[sec_id][q_no_str] = det or ''

    avg_conf = float(np.mean(confidences)) if confidences else 0.5
    return roll_number, answers, round(avg_conf, 2), None


def _detect_with_gpt4v(image_bytes, paper_json):
    """GPT-4V fallback: ask the model to extract marked answers from OMR image."""
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        return None, {}, 0.0, 'OPENAI_API_KEY not configured'

    q_list = _collect_mcq(paper_json)
    num_q  = min(len(q_list), _MAX_PER_COL * 2)
    q_desc = ', '.join(
        f"Q{i+1}({'T/F' if s == 'B' else 'A-D'})"
        for i, (s, _) in enumerate(q_list[:num_q])
    )
    prompt = (
        f"This is a PadhaiWithAI OMR answer sheet with {num_q} questions: {q_desc}. "
        "Identify which bubble is filled for each question. "
        "Return ONLY a compact JSON object, e.g. {\"1\":\"A\",\"2\":\"True\",\"3\":null} "
        f"with keys \"1\" to \"{num_q}\". Use null for unanswered. Nothing else."
    )
    b64 = base64.b64encode(image_bytes).decode()
    try:
        import openai as _oai
        resp = _oai.OpenAI(api_key=openai_key).chat.completions.create(
            model='gpt-4o-mini',
            messages=[{'role': 'user', 'content': [
                {'type': 'text',      'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
            ]}],
            temperature=0.0, max_tokens=600,
        )
        raw_text = resp.choices[0].message.content.strip()
        start    = raw_text.find('{')
        end      = raw_text.rfind('}') + 1
        gpt_map  = json.loads(raw_text[start:end]) if start >= 0 else {}
    except Exception as e:
        return None, {}, 0.0, f'GPT-4V error: {e}'

    TF_MAP  = {'True': 'True', 'False': 'False', 'A': 'True', 'B': 'False'}
    answers = {}
    for idx, (sec_id, q_no_str) in enumerate(q_list[:num_q]):
        answers.setdefault(sec_id, {})
        det = gpt_map.get(str(idx + 1))
        if det and sec_id == 'B':
            det = TF_MAP.get(str(det), str(det))
        answers[sec_id][q_no_str] = str(det) if det and det != 'None' else ''

    return None, answers, 0.75, None


def _process_omr(image_bytes, paper_json):
    """Orchestrate OpenCV → GPT-4V fallback. Returns (roll_no, answers, confidence, error)."""
    roll_no, answers, conf, err = _detect_with_opencv(image_bytes, paper_json)
    if not _HAS_CV2:
        return _detect_with_gpt4v(image_bytes, paper_json)
    if conf < 0.50 and os.getenv('OPENAI_API_KEY'):
        _, gpt_ans, gpt_conf, gpt_err = _detect_with_gpt4v(image_bytes, paper_json)
        if not gpt_err and gpt_conf > conf:
            return roll_no, gpt_ans, gpt_conf, None
    return roll_no, answers, conf, err


# ── Views ────────────────────────────────────────────────────────────────────

@login_required
def omr_upload_view(request, pk):
    """OMR upload / review page for a teacher."""
    from ..models import AssignedPaper, Student

    assignment = get_object_or_404(AssignedPaper, pk=pk, assigned_by=request.user)
    students   = list(Student.objects.filter(
        school=assignment.school, class_name=assignment.class_name, is_active=True,
    ).order_by('roll_number').values('id', 'name', 'roll_number'))

    q_list = _collect_mcq(assignment.question_paper.paper_json)

    return render(request, 'school_app/omr/omr_upload.html', {
        'assignment':    assignment,
        'students_json': json.dumps(students),
        'q_list_json':   json.dumps([
            {'idx': i, 'sec': s, 'q_no': q, 'is_tf': s == 'B'}
            for i, (s, q) in enumerate(q_list[:_MAX_PER_COL * 2])
        ]),
        'q_count':       min(len(q_list), _MAX_PER_COL * 2),
        'has_cv2':       _HAS_CV2,
        'has_reportlab': _HAS_REPORTLAB,
        'has_qrcode':    _HAS_QRCODE,
    })


@require_http_methods(['POST'])
@login_required
def omr_process_ajax(request, pk):
    """AJAX: receive one OMR image → return detected answers JSON."""
    try:
        from ..models import AssignedPaper, Student

        assignment = get_object_or_404(AssignedPaper, pk=pk, assigned_by=request.user)
        img_file   = request.FILES.get('image')
        if not img_file:
            return JsonResponse({'error': 'No image received'}, status=400)
        if img_file.size > 20 * 1024 * 1024:
            return JsonResponse({'error': 'Image too large (max 20 MB)'}, status=400)

        image_bytes = img_file.read()
        paper_json  = assignment.question_paper.paper_json
        q_list      = _collect_mcq(paper_json)
        num_q       = min(len(q_list), _MAX_PER_COL * 2)

        roll_no, answers, confidence, error = _process_omr(image_bytes, paper_json)

        # Resolve student from roll number
        student_id, student_name, manual_needed = None, None, True
        qr_status = 'not_detected'
        if roll_no:
            qr_status = 'detected'
            try:
                s = Student.objects.get(
                    roll_number=roll_no,
                    school=assignment.school,
                    class_name=assignment.class_name,
                    is_active=True,
                )
                student_id, student_name, manual_needed = s.pk, s.name, False
                qr_status = 'matched'
            except Student.DoesNotExist:
                qr_status = f'no_student_roll={roll_no}'

        # Build flat answer map {str(idx): option_str}
        flat = {}
        TF_DISPLAY = {'True': 'T', 'False': 'F'}
        for idx, (sec_id, q_no_str) in enumerate(q_list[:num_q]):
            det = answers.get(sec_id, {}).get(q_no_str, '')
            if sec_id == 'B' and det in TF_DISPLAY:
                det = TF_DISPLAY[det]
            flat[str(idx)] = det

        return JsonResponse({
            'roll_number':   roll_no,
            'student_id':    student_id,
            'student_name':  student_name,
            'manual_needed': manual_needed,
            'answers':       flat,
            'confidence':    confidence,
            'warning':       error,
            'qr_status':     qr_status,
        })

    except Exception as exc:
        logger.exception("omr_process_ajax unhandled error")
        return JsonResponse({'error': f'Processing failed: {exc}'}, status=500)


@require_http_methods(['POST'])
@login_required
def omr_confirm_ajax(request, pk):
    """AJAX: save confirmed OMR results → create/update StudentPaperAttempts."""
    from ..models import AssignedPaper, Student, StudentPaperAttempt
    from .assigned_paper import _auto_grade

    assignment = get_object_or_404(AssignedPaper, pk=pk, assigned_by=request.user)
    paper_json = assignment.question_paper.paper_json
    q_list     = _collect_mcq(paper_json)
    num_q      = min(len(q_list), _MAX_PER_COL * 2)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

    saved, skipped, errors = 0, 0, []
    TF_MAP = {'T': 'True', 'F': 'False', 'A': 'True', 'B': 'False'}

    for entry in payload:
        sid  = entry.get('student_id')
        flat = entry.get('answers', {})
        if not sid or not flat:
            skipped += 1
            continue

        try:
            student = Student.objects.get(
                pk=sid, school=assignment.school,
                class_name=assignment.class_name, is_active=True,
            )
        except Student.DoesNotExist:
            errors.append(f'Student id={sid} not found')
            continue

        attempt, _ = StudentPaperAttempt.objects.get_or_create(
            assigned_paper=assignment, student=student,
        )
        if attempt.is_submitted:
            skipped += 1
            continue

        # Rebuild section-based answers dict from flat {str(idx): option}
        answers = {}
        for idx, (sec_id, q_no_str) in enumerate(q_list[:num_q]):
            answers.setdefault(sec_id, {})
            opt = flat.get(str(idx), '')
            if opt and sec_id == 'B':
                opt = TF_MAP.get(opt, opt)
            answers[sec_id][q_no_str] = opt

        score, max_score, _ = _auto_grade(paper_json, answers)
        attempt.answers      = answers
        attempt.score        = score
        attempt.max_score    = max_score
        attempt.is_submitted = True
        attempt.submitted_at = timezone.now()
        attempt.save()
        saved += 1

    return JsonResponse({'saved': saved, 'skipped': skipped, 'errors': errors})
