"""
Hierarchy utility functions for user-based data scoping.
"""
from .utils import *


def get_user_hierarchy(user):
    """
    Get the complete hierarchy data for a user based on their role.
    Returns: dict with state, districts, blocks, schools, students querysets
    Hierarchy: State → District → Block → School → Student
    """
    result = {
        'state': None,
        'districts': District.objects.none(),
        'blocks': Block.objects.none(),
        'schools': School.objects.none(),
        'students': Student.objects.none(),
        'role': 'unknown'
    }

    try:
        if user.is_system_admin:
            # Only ACTIVE districts (and everything cascading from them) show up
            # in higher-level scoping. Inactive districts remain in the DB but
            # are hidden from every list/aggregation view that goes through
            # this helper. To reactivate them, use the "Manage Districts" page.
            active_districts = District.objects.filter(is_active=True)
            result['districts'] = active_districts
            result['blocks'] = Block.objects.filter(district__in=active_districts)
            result['schools'] = School.objects.filter(block__district__in=active_districts)
            result['students'] = Student.objects.filter(school__block__district__in=active_districts)
            result['role'] = 'system_admin'

        elif user.is_state_user:
            state = State.objects.get(admin=user)
            result['state'] = state
            active_districts = District.objects.filter(state=state, is_active=True)
            result['districts'] = active_districts
            result['blocks'] = Block.objects.filter(district__in=active_districts)
            result['schools'] = School.objects.filter(block__district__in=active_districts)
            result['students'] = Student.objects.filter(school__block__district__in=active_districts)
            result['role'] = 'state'

        elif user.is_district_user:
            district = District.objects.get(admin=user)
            result['state'] = district.state
            result['districts'] = District.objects.filter(id=district.id)
            result['blocks'] = Block.objects.filter(district=district)
            result['schools'] = School.objects.filter(block__district=district)
            result['students'] = Student.objects.filter(school__block__district=district)
            result['role'] = 'district'

        elif user.is_block_user:
            block = Block.objects.get(admin=user)
            result['state'] = block.district.state if block.district else None
            result['districts'] = District.objects.filter(id=block.district_id)
            result['blocks'] = Block.objects.filter(id=block.id)
            result['schools'] = School.objects.filter(block=block)
            result['students'] = Student.objects.filter(school__block=block)
            result['role'] = 'block'

        elif user.is_school_user:
            school = School.objects.get(admin=user)
            result['state'] = school.block.district.state if school.block and school.block.district else None
            result['districts'] = District.objects.filter(id=school.block.district_id) if school.block else District.objects.none()
            result['blocks'] = Block.objects.filter(id=school.block_id) if school.block else Block.objects.none()
            result['schools'] = School.objects.filter(id=school.id)
            result['students'] = Student.objects.filter(school=school)
            result['role'] = 'school'

    except (State.DoesNotExist, District.DoesNotExist, Block.DoesNotExist, School.DoesNotExist):
        pass

    return result


def get_user_schools(user):
    """
    Get schools accessible to a user based on their role.
    Returns a queryset of School objects the user has access to.
    Hierarchy: State → District → Block → School
    """
    hierarchy = get_user_hierarchy(user)
    return hierarchy['schools']


def get_user_students(user):
    """
    Get students accessible to a user based on their role.
    Returns a queryset of Student objects the user has access to.
    """
    hierarchy = get_user_hierarchy(user)
    return hierarchy['students']


def get_user_block(user):
    """Get the block associated with a block user."""
    return Block.objects.get(admin=user)


def get_user_district(user):
    """Get the district associated with a district user."""
    return District.objects.get(admin=user)


def get_user_state(user):
    """Get the state associated with a state user."""
    return State.objects.get(admin=user)
