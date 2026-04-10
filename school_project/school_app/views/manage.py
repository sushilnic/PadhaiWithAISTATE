"""
Hierarchical user management views (states, districts, blocks, schools).
"""
from .utils import *


@login_required
def manage_states(request):
    """List all states (admin only)."""
    if not request.user.is_system_admin:
        return render(request, 'school_app/errors/403.html', status=403)
    states = State.objects.all().order_by('name_english')
    items = []
    for s in states:
        items.append({
            'id': s.id,
            'name': s.name_english,
            'name_hindi': s.name_hindi,
            'admin_email': s.admin.email if s.admin else '—',
            'is_active': s.is_active,
            'created_at': s.created_at,
        })
    return render(request, 'school_app/manage/manage_list.html', {
        'title': 'Manage States',
        'items': items,
        'create_url': 'create_state',
        'edit_url_name': 'edit_state',
        'toggle_url_name': 'toggle_state',
        'entity_type': 'State',
    })


@login_required
def create_state(request):
    """Create a new state with admin user (admin only)."""
    if not request.user.is_system_admin:
        return render(request, 'school_app/errors/403.html', status=403)
    if request.method == 'POST':
        form = StateCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    admin_user = CustomUser.objects.create_user(
                        email=form.cleaned_data['admin_email'],
                        password=form.cleaned_data['admin_password'],
                    )
                    admin_user.is_school_user = False
                    admin_user.is_state_user = True
                    admin_user.save()
                    State.objects.create(
                        name_english=form.cleaned_data['name_english'],
                        name_hindi=form.cleaned_data['name_hindi'],
                        code=form.cleaned_data['code'].upper(),
                        admin=admin_user,
                    )
                messages.success(request, 'State created successfully.')
                return redirect('manage_states')
            except IntegrityError:
                messages.error(request, 'Error creating state. Email or code may already exist.')
    else:
        form = StateCreateForm()
    return render(request, 'school_app/manage/manage_form.html', {
        'title': 'Create State',
        'form': form,
        'submit_text': 'Create State',
        'cancel_url': 'manage_states',
    })


@login_required
def edit_state(request, state_id):
    """Edit state info (admin only)."""
    if not request.user.is_system_admin:
        return render(request, 'school_app/errors/403.html', status=403)
    state = get_object_or_404(State, id=state_id)
    if request.method == 'POST':
        form = StateEditForm(request.POST, instance=state)
        if form.is_valid():
            form.save()
            messages.success(request, 'State updated successfully.')
            return redirect('manage_states')
    else:
        form = StateEditForm(instance=state)
    return render(request, 'school_app/manage/manage_form.html', {
        'title': f'Edit State: {state.name_english}',
        'form': form,
        'submit_text': 'Save Changes',
        'cancel_url': 'manage_states',
    })


@login_required
def toggle_state(request, state_id):
    """Activate/deactivate a state and its admin user (admin only)."""
    if not request.user.is_system_admin:
        return render(request, 'school_app/errors/403.html', status=403)
    state = get_object_or_404(State, id=state_id)
    state.is_active = not state.is_active
    state.save()
    if state.admin:
        state.admin.is_active = state.is_active
        state.admin.save()
    status = 'activated' if state.is_active else 'deactivated'
    messages.success(request, f'State "{state.name_english}" {status} successfully.')
    return redirect('manage_states')


@login_required
def manage_districts(request):
    """List districts under the logged-in state user."""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_system_admin:
        districts = District.objects.all()
    else:
        state = get_object_or_404(State, admin=user)
        districts = District.objects.filter(state=state)
    items = []
    for d in districts:
        admin = d.admin
        is_locked = bool(
            admin and admin.locked_until and admin.locked_until > timezone.now()
        )
        items.append({
            'id': d.id,
            'name': d.name_english,
            'name_hindi': d.name_hindi,
            'admin_email': admin.email if admin else '—',
            'is_active': d.is_active,
            'created_at': d.created_at,
            'is_locked': is_locked,
        })
    return render(request, 'school_app/manage/manage_list.html', {
        'title': 'Manage Districts',
        'items': items,
        'create_url': 'create_district',
        'edit_url_name': 'edit_district',
        'toggle_url_name': 'toggle_district',
        'entity_type': 'District',
        'unlock_url_name': 'unlock_district_user',
        'reset_password_url_name': 'reset_district_password',
    })


@login_required
def create_district(request):
    """Create a new district with admin user (state user only)."""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_state_user:
        state = get_object_or_404(State, admin=user)
    else:
        state = None
    if request.method == 'POST':
        form = DistrictCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    admin_user = CustomUser.objects.create_user(
                        email=form.cleaned_data['admin_email'],
                        password=form.cleaned_data['admin_password'],
                    )
                    admin_user.is_school_user = False
                    admin_user.is_district_user = True
                    admin_user.save()
                    District.objects.create(
                        name_english=form.cleaned_data['name_english'],
                        name_hindi=form.cleaned_data['name_hindi'],
                        state=state,
                        admin=admin_user,
                    )
                messages.success(request, 'District created successfully.')
                return redirect('manage_districts')
            except IntegrityError:
                messages.error(request, 'Error creating district. Email may already exist.')
    else:
        form = DistrictCreateForm()
    return render(request, 'school_app/manage/manage_form.html', {
        'title': 'Create District',
        'form': form,
        'submit_text': 'Create District',
        'cancel_url': 'manage_districts',
    })


@login_required
def edit_district(request, district_id):
    """Edit district info (state user or admin)."""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    district = get_object_or_404(District, id=district_id)
    if user.is_state_user:
        state = get_object_or_404(State, admin=user)
        if district.state != state:
            return render(request, 'school_app/errors/403.html', status=403)
    if request.method == 'POST':
        form = DistrictEditForm(request.POST, instance=district)
        if form.is_valid():
            form.save()
            messages.success(request, 'District updated successfully.')
            return redirect('manage_districts')
    else:
        form = DistrictEditForm(instance=district)
    return render(request, 'school_app/manage/manage_form.html', {
        'title': f'Edit District: {district.name_english}',
        'form': form,
        'submit_text': 'Save Changes',
        'cancel_url': 'manage_districts',
    })


@login_required
def toggle_district(request, district_id):
    """Activate/deactivate a district and its admin user."""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    district = get_object_or_404(District, id=district_id)
    if user.is_state_user:
        state = get_object_or_404(State, admin=user)
        if district.state != state:
            return render(request, 'school_app/errors/403.html', status=403)
    district.is_active = not district.is_active
    district.save()
    if district.admin:
        district.admin.is_active = district.is_active
        district.admin.save()
    status = 'activated' if district.is_active else 'deactivated'
    messages.success(request, f'District "{district.name_english}" {status} successfully.')
    return redirect('manage_districts')


@login_required
def unlock_district_user(request, district_id):
    """Unlock a district admin user account locked due to failed login attempts."""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    district = get_object_or_404(District, id=district_id)
    if user.is_state_user:
        state = get_object_or_404(State, admin=user)
        if district.state != state:
            return render(request, 'school_app/errors/403.html', status=403)
    if district.admin:
        district.admin.locked_until = None
        district.admin.failed_login_attempts = 0
        district.admin.save(update_fields=['locked_until', 'failed_login_attempts'])
        log_activity(request, 'EDIT', f'Unlocked district user account: {district.admin.email}')
        messages.success(request, f'Account for "{district.name_english}" has been unlocked.')
    else:
        messages.error(request, 'No admin user found for this district.')
    return redirect('manage_districts')


@login_required
def reset_district_password(request, district_id):
    """Reset district admin password to default: nic*12345"""
    user = request.user
    if not (user.is_state_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    district = get_object_or_404(District, id=district_id)
    if user.is_state_user:
        state = get_object_or_404(State, admin=user)
        if district.state != state:
            return render(request, 'school_app/errors/403.html', status=403)
    if district.admin:
        district.admin.set_password('nic*12345')
        district.admin.failed_login_attempts = 0
        district.admin.locked_until = None
        district.admin.must_change_password = True
        district.admin.save(update_fields=['password', 'failed_login_attempts', 'locked_until', 'must_change_password'])
        log_activity(request, 'EDIT', f'Reset password to default for district user: {district.admin.email}')
        messages.success(request, f'Password for "{district.name_english}" reset to default (nic*12345). User must change it on next login.')
    else:
        messages.error(request, 'No admin user found for this district.')
    return redirect('manage_districts')


@login_required
def manage_blocks(request):
    """List blocks under the logged-in district user."""
    user = request.user
    if not (user.is_district_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_system_admin:
        blocks = Block.objects.all()
    else:
        district = get_object_or_404(District, admin=user)
        blocks = Block.objects.filter(district=district)
    items = []
    for b in blocks:
        items.append({
            'id': b.id,
            'name': b.name_english,
            'name_hindi': b.name_hindi,
            'admin_email': b.admin.email if b.admin else '—',
            'is_active': b.is_active,
            'created_at': b.created_at,
        })
    return render(request, 'school_app/manage/manage_list.html', {
        'title': 'Manage Blocks',
        'items': items,
        'create_url': 'create_block',
        'edit_url_name': 'edit_block',
        'toggle_url_name': 'toggle_block',
        'entity_type': 'Block',
    })


@login_required
def create_block(request):
    """Create a new block with admin user (district user only)."""
    user = request.user
    if not (user.is_district_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
    else:
        district = None
    if request.method == 'POST':
        form = BlockCreateForm(request.POST)
        if user.is_district_user:
            form.fields['district'].queryset = District.objects.filter(id=district.id)
        else:
            form.fields['district'].queryset = District.objects.all()
        if form.is_valid():
            try:
                with transaction.atomic():
                    admin_user = CustomUser.objects.create_user(
                        email=form.cleaned_data['admin_email'],
                        password=form.cleaned_data['admin_password'],
                    )
                    admin_user.is_school_user = False
                    admin_user.is_block_user = True
                    admin_user.save()
                    block_obj = Block.objects.create(
                        name_english=form.cleaned_data['name_english'],
                        name_hindi=form.cleaned_data['name_hindi'],
                        district=form.cleaned_data['district'],
                        admin=admin_user,
                    )
                log_activity(request, 'CREATE', f'Block created: {block_obj.name_english}', district=form.cleaned_data['district'])
                messages.success(request, 'Block created successfully.')
                return redirect('manage_blocks')
            except IntegrityError:
                messages.error(request, 'Error creating block. Email may already exist.')
    else:
        form = BlockCreateForm()
        if user.is_district_user:
            form.fields['district'].queryset = District.objects.filter(id=district.id)
            form.fields['district'].initial = district
        else:
            form.fields['district'].queryset = District.objects.all()
    return render(request, 'school_app/manage/manage_form.html', {
        'title': 'Create Block',
        'form': form,
        'submit_text': 'Create Block',
        'cancel_url': 'manage_blocks',
    })


@login_required
def edit_block(request, block_id):
    """Edit block info (district user or admin)."""
    user = request.user
    if not (user.is_district_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    block = get_object_or_404(Block, id=block_id)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
        if block.district != district:
            return render(request, 'school_app/errors/403.html', status=403)
    if request.method == 'POST':
        form = BlockEditForm(request.POST, instance=block)
        if form.is_valid():
            form.save()
            log_activity(request, 'EDIT', f'Block edited: {block.name_english}', district=block.district)
            messages.success(request, 'Block updated successfully.')
            return redirect('manage_blocks')
    else:
        form = BlockEditForm(instance=block)
    return render(request, 'school_app/manage/manage_form.html', {
        'title': f'Edit Block: {block.name_english}',
        'form': form,
        'submit_text': 'Save Changes',
        'cancel_url': 'manage_blocks',
    })


@login_required
def toggle_block(request, block_id):
    """Activate/deactivate a block and its admin user."""
    user = request.user
    if not (user.is_district_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    block = get_object_or_404(Block, id=block_id)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
        if block.district != district:
            return render(request, 'school_app/errors/403.html', status=403)
    block.is_active = not block.is_active
    block.save()
    if block.admin:
        block.admin.is_active = block.is_active
        block.admin.save()
    status = 'activated' if block.is_active else 'deactivated'
    log_activity(request, 'TOGGLE', f'Block {status}: {block.name_english}', district=block.district)
    messages.success(request, f'Block "{block.name_english}" {status} successfully.')
    return redirect('manage_blocks')


@login_required
def manage_schools(request):
    """List schools filtered by district or block."""
    user = request.user
    if not (user.is_district_user or user.is_block_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_system_admin:
        schools = School.objects.all()
    elif user.is_district_user:
        district = get_object_or_404(District, admin=user)
        schools = School.objects.filter(block__district=district)
    else:
        block = get_object_or_404(Block, admin=user)
        schools = School.objects.filter(block=block)
    items = []
    for s in schools:
        items.append({
            'id': s.id,
            'name': s.name,
            'name_hindi': '',
            'admin_email': s.admin.email if s.admin else '—',
            'is_active': s.is_active,
            'created_at': s.created_at,
        })
    return render(request, 'school_app/manage/manage_list.html', {
        'title': 'Manage Schools',
        'items': items,
        'create_url': 'create_school_manage',
        'edit_url_name': 'edit_school',
        'toggle_url_name': 'toggle_school',
        'entity_type': 'School',
    })


@login_required
def create_school_manage(request):
    """Create a new school with admin user (district or block user)."""
    user = request.user
    if not (user.is_district_user or user.is_block_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
        block_qs = Block.objects.filter(district=district)
    elif user.is_block_user:
        block = get_object_or_404(Block, admin=user)
        block_qs = Block.objects.filter(id=block.id)
    else:
        block_qs = Block.objects.all()
    if request.method == 'POST':
        form = SchoolCreateForm(request.POST)
        form.fields['block'].queryset = block_qs
        if form.is_valid():
            try:
                with transaction.atomic():
                    admin_user = CustomUser.objects.create_user(
                        email=form.cleaned_data['admin_email'],
                        password=form.cleaned_data['admin_password'],
                    )
                    # create_user sets is_school_user=True by default
                    school_obj = School.objects.create(
                        name=form.cleaned_data['name'],
                        block=form.cleaned_data['block'],
                        nic_code=form.cleaned_data.get('nic_code', ''),
                        admin=admin_user,
                        created_by=user,
                    )
                log_activity(request, 'CREATE', f'School created: {school_obj.name}', district=form.cleaned_data['block'].district)
                messages.success(request, 'School created successfully.')
                return redirect('manage_schools')
            except IntegrityError:
                messages.error(request, 'Error creating school. Email may already exist.')
    else:
        form = SchoolCreateForm()
        form.fields['block'].queryset = block_qs
        if user.is_block_user:
            form.fields['block'].initial = get_object_or_404(Block, admin=user)
    return render(request, 'school_app/manage/manage_form.html', {
        'title': 'Create School',
        'form': form,
        'submit_text': 'Create School',
        'cancel_url': 'manage_schools',
    })


@login_required
def edit_school(request, school_id):
    """Edit school info (district, block, or admin)."""
    user = request.user
    if not (user.is_district_user or user.is_block_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    school = get_object_or_404(School, id=school_id)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
        if school.block.district != district:
            return render(request, 'school_app/errors/403.html', status=403)
    elif user.is_block_user:
        block = get_object_or_404(Block, admin=user)
        if school.block != block:
            return render(request, 'school_app/errors/403.html', status=403)
    if request.method == 'POST':
        form = SchoolEditForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            log_activity(request, 'EDIT', f'School edited: {school.name}', district=school.block.district if school.block else None)
            messages.success(request, 'School updated successfully.')
            return redirect('manage_schools')
    else:
        form = SchoolEditForm(instance=school)
    return render(request, 'school_app/manage/manage_form.html', {
        'title': f'Edit School: {school.name}',
        'form': form,
        'submit_text': 'Save Changes',
        'cancel_url': 'manage_schools',
    })


@login_required
def toggle_school(request, school_id):
    """Activate/deactivate a school and its admin user."""
    user = request.user
    if not (user.is_district_user or user.is_block_user or user.is_system_admin):
        return render(request, 'school_app/errors/403.html', status=403)
    school = get_object_or_404(School, id=school_id)
    if user.is_district_user:
        district = get_object_or_404(District, admin=user)
        if school.block.district != district:
            return render(request, 'school_app/errors/403.html', status=403)
    elif user.is_block_user:
        block = get_object_or_404(Block, admin=user)
        if school.block != block:
            return render(request, 'school_app/errors/403.html', status=403)
    school.is_active = not school.is_active
    school.save()
    if school.admin:
        school.admin.is_active = school.is_active
        school.admin.save()
    status = 'activated' if school.is_active else 'deactivated'
    log_activity(request, 'TOGGLE', f'School {status}: {school.name}', district=school.block.district if school.block else None)
    messages.success(request, f'School "{school.name}" {status} successfully.')
    return redirect('manage_schools')
