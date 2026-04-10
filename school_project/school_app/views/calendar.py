"""
Academic calendar views.
"""
from .utils import *
from .utils import _get_user_district, _events_as_json


@login_required
def academic_calendar_view(request):
    """View calendar — block and school users see their district's events."""
    district = _get_user_district(request)
    if not district:
        messages.error(request, 'Unable to determine your district.')
        return redirect('dashboard')
    events = _events_as_json(district)
    return render(request, 'school_app/calendar/academic_calendar_page.html', {
        'district': district,
        'calendar_events_json': json.dumps(events),
        'can_manage': request.user.is_district_user,
    })


@login_required
def academic_calendar_manage(request):
    """Management page — district admin only."""
    if not request.user.is_district_user:
        messages.error(request, 'Only district admins can manage the calendar.')
        return redirect('academic_calendar')
    try:
        district = District.objects.get(admin=request.user)
    except District.DoesNotExist:
        messages.error(request, 'District not found.')
        return redirect('dashboard')
    events = AcademicCalendarEvent.objects.filter(district=district).order_by('start_date')
    return render(request, 'school_app/calendar/academic_calendar_manage.html', {
        'district': district,
        'events': events,
        'calendar_events_json': json.dumps(_events_as_json(district)),
        'event_types': AcademicCalendarEvent.EVENT_TYPES,
    })


@login_required
@require_http_methods(["POST"])
def academic_calendar_add(request):
    """AJAX — district admin adds an event."""
    if not request.user.is_district_user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)
    try:
        district = District.objects.get(admin=request.user)
        data = json.loads(request.body)
        title      = str(data.get('title', '')).strip()[:300]
        start_date = data.get('start_date')
        end_date   = data.get('end_date') or start_date
        event_type = data.get('event_type', 'teaching')
        if not title or not start_date:
            return JsonResponse({'error': 'Title and start date are required.'}, status=400)
        if event_type not in dict(AcademicCalendarEvent.EVENT_TYPES):
            event_type = 'other'
        event = AcademicCalendarEvent.objects.create(
            district=district, title=title,
            start_date=start_date, end_date=end_date,
            event_type=event_type, created_by=request.user,
        )
        color_map = {
            'teaching': '#1e3c72', 'exam': '#dc2626',
            'holiday': '#059669', 'meeting': '#d97706', 'other': '#6d28d9',
        }
        return JsonResponse({
            'success': True,
            'event': {
                'id': event.id, 'title': event.title,
                'start': str(event.start_date), 'end': str(event.end_date),
                'type': event.event_type, 'color': color_map.get(event.event_type, '#1e3c72'),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def academic_calendar_delete(request, event_id):
    """AJAX — district admin deletes an event."""
    if not request.user.is_district_user:
        return JsonResponse({'error': 'Permission denied.'}, status=403)
    try:
        district = District.objects.get(admin=request.user)
        event = get_object_or_404(AcademicCalendarEvent, id=event_id, district=district)
        event.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
