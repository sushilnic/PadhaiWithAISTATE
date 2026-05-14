"""
State-level content administration: manage AISathiSubject and AISathiChapter.
Only accessible to state users and system admins.
"""
from .utils import *
from ..models import AISathiClass, AISathiSubject, AISathiChapter


def _require_state(request):
    """Return None if authorised, else an HttpResponse to return immediately."""
    u = request.user
    if u.is_authenticated and (u.is_state_user or u.is_system_admin):
        return None
    return HttpResponseForbidden("State access required.")


# ─── Subjects ────────────────────────────────────────────────────────────────

@login_required
def manage_subjects(request):
    guard = _require_state(request)
    if guard:
        return guard

    classes = AISathiClass.objects.order_by('number')
    sel_class = request.GET.get('class_id', '')
    subjects = AISathiSubject.objects.select_related('class_ref').order_by('class_ref__number', 'order', 'name')
    if sel_class:
        subjects = subjects.filter(class_ref_id=sel_class)

    msg = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add':
            class_id = request.POST.get('class_id', '').strip()
            name     = request.POST.get('name', '').strip()
            order    = int(request.POST.get('order', 0) or 0)
            if class_id and name:
                try:
                    cls = AISathiClass.objects.get(pk=class_id)
                    AISathiSubject.objects.get_or_create(
                        class_ref=cls, name=name,
                        defaults={'order': order, 'is_active': True}
                    )
                    msg = 'Subject added successfully.'
                except AISathiClass.DoesNotExist:
                    msg = 'Invalid class selected.'
                except Exception as e:
                    msg = f'Error: {e}'
            else:
                msg = 'Class and subject name are required.'

        elif action == 'edit':
            subj_id  = request.POST.get('subj_id', '')
            name     = request.POST.get('name', '').strip()
            order    = int(request.POST.get('order', 0) or 0)
            is_active = request.POST.get('is_active') == '1'
            try:
                subj = AISathiSubject.objects.get(pk=subj_id)
                subj.name      = name
                subj.order     = order
                subj.is_active = is_active
                subj.save()
                msg = 'Subject updated successfully.'
            except AISathiSubject.DoesNotExist:
                msg = 'Subject not found.'
            except Exception as e:
                msg = f'Error: {e}'

        elif action == 'delete':
            subj_id = request.POST.get('subj_id', '')
            try:
                subj = AISathiSubject.objects.get(pk=subj_id)
                count = subj.chapters.count()
                subj.delete()
                msg = f'Subject deleted (and {count} chapter(s) removed).'
            except AISathiSubject.DoesNotExist:
                msg = 'Subject not found.'

        return redirect(request.path + ('?class_id=' + sel_class if sel_class else ''))

    return render(request, 'school_app/state/manage_subjects.html', {
        'classes':   classes,
        'subjects':  subjects,
        'sel_class': sel_class,
        'msg':       msg,
    })


# ─── Chapters ────────────────────────────────────────────────────────────────

@login_required
def manage_chapters(request):
    guard = _require_state(request)
    if guard:
        return guard

    classes    = AISathiClass.objects.order_by('number')
    sel_class  = request.GET.get('class_id', '')
    sel_subj   = request.GET.get('subj_id', '')

    all_subjects = AISathiSubject.objects.select_related('class_ref').order_by('class_ref__number', 'name')
    if sel_class:
        all_subjects = all_subjects.filter(class_ref_id=sel_class)

    chapters = AISathiChapter.objects.select_related('subject', 'subject__class_ref').order_by(
        'subject__class_ref__number', 'subject__name', 'order', 'id'
    )
    if sel_subj:
        chapters = chapters.filter(subject_id=sel_subj)
    elif sel_class:
        chapters = chapters.filter(subject__class_ref_id=sel_class)

    msg = ''
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'add':
            subj_id     = request.POST.get('subj_id', '').strip()
            name        = request.POST.get('name', '').strip()
            order       = int(request.POST.get('order', 0) or 0)
            description = request.POST.get('description', '').strip()
            if subj_id and name:
                try:
                    subj = AISathiSubject.objects.get(pk=subj_id)
                    AISathiChapter.objects.create(
                        subject=subj, name=name, order=order,
                        description=description, is_active=True
                    )
                    msg = 'Chapter added successfully.'
                except AISathiSubject.DoesNotExist:
                    msg = 'Subject not found.'
                except Exception as e:
                    msg = f'Error: {e}'
            else:
                msg = 'Subject and chapter name are required.'

        elif action == 'edit':
            chap_id     = request.POST.get('chap_id', '')
            name        = request.POST.get('name', '').strip()
            order       = int(request.POST.get('order', 0) or 0)
            description = request.POST.get('description', '').strip()
            is_active   = request.POST.get('is_active') == '1'
            try:
                chap = AISathiChapter.objects.get(pk=chap_id)
                chap.name        = name
                chap.order       = order
                chap.description = description
                chap.is_active   = is_active
                chap.save()
                msg = 'Chapter updated successfully.'
            except AISathiChapter.DoesNotExist:
                msg = 'Chapter not found.'
            except Exception as e:
                msg = f'Error: {e}'

        elif action == 'delete':
            chap_id = request.POST.get('chap_id', '')
            try:
                AISathiChapter.objects.get(pk=chap_id).delete()
                msg = 'Chapter deleted.'
            except AISathiChapter.DoesNotExist:
                msg = 'Chapter not found.'

        qs = '?'
        if sel_class: qs += f'class_id={sel_class}&'
        if sel_subj:  qs += f'subj_id={sel_subj}'
        return redirect(request.path + qs)

    return render(request, 'school_app/state/manage_chapters.html', {
        'classes':      classes,
        'all_subjects': all_subjects,
        'chapters':     chapters,
        'sel_class':    sel_class,
        'sel_subj':     sel_subj,
        'msg':          msg,
    })
