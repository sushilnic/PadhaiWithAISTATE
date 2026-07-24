"""
Topper management — district admins upload weekly toppers displayed on the
public login page. Access restricted to district admin (Collector) only.
"""
import io
from datetime import date, timedelta

from django.core.files.uploadedfile import InMemoryUploadedFile

from .utils import *
from ..forms import TopperForm
from ..models import Topper


TOPPER_IMAGE_SIZE = 400        # final square size, in pixels
TOPPER_JPEG_QUALITY = 85


def _process_topper_image(uploaded_file):
    """Auto-crop to square + resize to 400x400 + strip EXIF + convert to JPEG.

    Returns a new UploadedFile ready to assign to `Topper.image`, or the
    original file if processing fails (never blocks the upload — validation
    already ran in the form).
    """
    try:
        from PIL import Image, ImageOps
        # Use the decompression-bomb-safe helper
        img = open_image_safely(uploaded_file.read(), mode='RGB')
        uploaded_file.seek(0)
    except Exception:
        logger.exception('_process_topper_image: initial decode failed — keeping original')
        uploaded_file.seek(0)
        return uploaded_file

    try:
        # Honour EXIF rotation (phone photos)
        img = ImageOps.exif_transpose(img)

        # Center-crop to square (largest possible), then resize to target size
        img = ImageOps.fit(img, (TOPPER_IMAGE_SIZE, TOPPER_IMAGE_SIZE),
                            method=Image.Resampling.LANCZOS, centering=(0.5, 0.4))
        # centering=(0.5, 0.4) biases the crop slightly upward — better for portrait photos
        # (heads don't get chopped off)

        # Save as JPEG (no EXIF — privacy: strips GPS/device info)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=TOPPER_JPEG_QUALITY, optimize=True)
        buf.seek(0)

        # Rewrite the uploaded file name to .jpg
        original_name = uploaded_file.name.rsplit('.', 1)[0]
        new_name = f'{original_name}.jpg'

        return InMemoryUploadedFile(
            file=buf, field_name='image', name=new_name,
            content_type='image/jpeg', size=buf.getbuffer().nbytes, charset=None
        )
    except Exception:
        logger.exception('_process_topper_image: transform failed — keeping original')
        uploaded_file.seek(0)
        return uploaded_file


def _current_week():
    """Return (monday, sunday) of the current week."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday, monday + timedelta(days=6)


def _require_district(request):
    """Return the District object for the current user or raise 403.
    District admin only for upload; block/school admins fall through to their own scope
    (view-only) but this is currently locked to district admin per product decision.
    """
    if not (request.user.is_authenticated and request.user.is_district_user):
        return None
    try:
        return District.objects.get(admin=request.user)
    except District.DoesNotExist:
        return None


def _district_toppers(district):
    """All toppers belonging to schools in this district."""
    return Topper.objects.filter(school__block__district=district).select_related('school')


@login_required
def topper_list(request):
    """List toppers uploaded for this district."""
    district = _require_district(request)
    if district is None:
        return render(request, 'school_app/errors/403.html', status=403)

    q_status = request.GET.get('status', 'all')  # all / active / inactive
    q_school = request.GET.get('school', '')

    qs = _district_toppers(district)
    if q_status == 'active':
        qs = qs.filter(is_active=True)
    elif q_status == 'inactive':
        qs = qs.filter(is_active=False)
    if q_school:
        qs = qs.filter(school_id=q_school)

    today = date.today()
    for t in qs:
        t.is_now = t.is_active and t.week_start <= today <= t.week_end

    schools = School.objects.filter(block__district=district).order_by('name')

    return render(request, 'school_app/district/topper_list.html', {
        'toppers':   qs,
        'schools':   schools,
        'q_status':  q_status,
        'q_school':  q_school,
        'today':     today,
    })


@login_required
def topper_upload(request):
    """District admin uploads a new topper."""
    district = _require_district(request)
    if district is None:
        return render(request, 'school_app/errors/403.html', status=403)

    if request.method == 'POST':
        form = TopperForm(request.POST, request.FILES, district=district)
        if form.is_valid():
            topper = form.save(commit=False)
            topper.created_by = request.user
            # Belt-and-braces: even if a district admin picks a school outside their
            # district somehow (tampered request), block it here.
            if topper.school and topper.school.block.district_id != district.id:
                messages.error(request, "That school is not in your district.")
                return render(request, 'school_app/district/topper_form.html',
                              {'form': form, 'mode': 'upload'})
            # Auto-crop to square 400x400, strip EXIF, save as JPEG
            if form.cleaned_data.get('image'):
                topper.image = _process_topper_image(form.cleaned_data['image'])
            topper.save()
            log_activity(request, 'TOPPER_CREATE',
                         f'Topper uploaded: {topper.name} ({topper.week_start}→{topper.week_end})',
                         district=district)
            messages.success(request, f'Topper "{topper.name}" uploaded successfully.')
            return redirect('topper_list')
    else:
        ws, we = _current_week()
        form = TopperForm(district=district, initial={
            'week_start': ws,
            'week_end':   we,
            'is_active':  True,
            'order':      0,
        })

    return render(request, 'school_app/district/topper_form.html',
                  {'form': form, 'mode': 'upload'})


@login_required
def topper_edit(request, pk):
    """District admin edits an existing topper (only within their district)."""
    district = _require_district(request)
    if district is None:
        return render(request, 'school_app/errors/403.html', status=403)

    topper = get_object_or_404(_district_toppers(district), pk=pk)

    if request.method == 'POST':
        form = TopperForm(request.POST, request.FILES, instance=topper, district=district)
        if form.is_valid():
            saved = form.save(commit=False)
            if saved.school and saved.school.block.district_id != district.id:
                messages.error(request, "That school is not in your district.")
                return render(request, 'school_app/district/topper_form.html',
                              {'form': form, 'mode': 'edit', 'topper': topper})
            # Only re-process if a new image was uploaded
            if 'image' in form.changed_data and form.cleaned_data.get('image'):
                saved.image = _process_topper_image(form.cleaned_data['image'])
            saved.save()
            log_activity(request, 'TOPPER_EDIT',
                         f'Topper edited: {saved.name} (id={saved.pk})',
                         district=district)
            messages.success(request, f'Topper "{saved.name}" updated.')
            return redirect('topper_list')
    else:
        form = TopperForm(instance=topper, district=district)

    return render(request, 'school_app/district/topper_form.html',
                  {'form': form, 'mode': 'edit', 'topper': topper})


@login_required
@require_POST
def topper_toggle(request, pk):
    """Show/hide a topper without deleting it."""
    district = _require_district(request)
    if district is None:
        return render(request, 'school_app/errors/403.html', status=403)

    topper = get_object_or_404(_district_toppers(district), pk=pk)
    topper.is_active = not topper.is_active
    topper.save(update_fields=['is_active'])
    log_activity(request, 'TOPPER_TOGGLE',
                 f'Topper {topper.name} → is_active={topper.is_active}',
                 district=district)
    messages.success(request, f'Topper "{topper.name}" is now {"active" if topper.is_active else "hidden"}.')
    return redirect('topper_list')


@login_required
@require_POST
def topper_delete(request, pk):
    """Permanently delete a topper and its image file."""
    district = _require_district(request)
    if district is None:
        return render(request, 'school_app/errors/403.html', status=403)

    topper = get_object_or_404(_district_toppers(district), pk=pk)
    name = topper.name
    # Delete the image file from storage too (Django doesn't do it automatically)
    if topper.image:
        try:
            topper.image.delete(save=False)
        except Exception:
            logger.exception('topper_delete: image delete failed pk=%s', pk)
    topper.delete()
    log_activity(request, 'TOPPER_DELETE', f'Topper deleted: {name}', district=district)
    messages.success(request, f'Topper "{name}" deleted.')
    return redirect('topper_list')


@login_required
def api_school_students(request, school_id):
    """AJAX: return students of a school, scoped to district admin's district.

    Used by the topper form's cascading School → Student dropdown to avoid
    typing mistakes in the topper's name.
    """
    district = _require_district(request)
    if district is None:
        return JsonResponse({'error': 'forbidden'}, status=403)

    # Belt-and-braces: only allow schools inside the caller's district.
    try:
        school = School.objects.select_related('block__district').get(pk=school_id)
    except School.DoesNotExist:
        return JsonResponse({'error': 'not_found'}, status=404)
    if school.block.district_id != district.id:
        return JsonResponse({'error': 'forbidden'}, status=403)

    students = (Student.objects.filter(school=school)
                .order_by('class_name', 'name')
                .values('id', 'name', 'roll_number', 'class_name'))
    return JsonResponse({'students': list(students)})


def get_current_toppers(limit=20):
    """Public helper: return active toppers whose week overlaps today.
    Used by the login page.
    """
    today = date.today()
    return Topper.objects.filter(
        is_active=True,
        week_start__lte=today,
        week_end__gte=today,
    ).order_by('order', '-created_at')[:limit]
