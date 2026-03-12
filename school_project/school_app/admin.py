"""
Admin module for PadhaiWithAI school management application.
Configures Django admin interface for all models.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import (
    CustomUser, School, Student, Marks, Attendance, Block, District, Test, State
)


# Site configuration
admin.site.site_header = 'PadhaiwithAI'
admin.site.site_title = 'PadhaiwithAI'


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    """Admin configuration for Test model."""
    list_display = [
        'test_number', 'test_name', 'subject_name', 'test_date',
        'is_active', 'created_by', 'created_at', 'max_marks',
        'pdf_file_questions_preview', 'pdf_file_answers_preview'
    ]
    list_filter = ['is_active', 'test_date', 'subject_name', 'created_by']
    search_fields = ['test_name', 'subject_name', 'created_by__username']
    date_hierarchy = 'test_date'
    actions = ['make_active', 'make_inactive']

    fieldsets = (
        (None, {
            'fields': (
                'test_name', 'subject_name', 'test_date',
                'pdf_file_questions', 'pdf_file_answers', 'is_active', 'max_marks'
            )
        }),
        ('Creator Info', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['created_at']

    @admin.action(description="Mark selected tests as Active")
    def make_active(self, request, queryset):
        """Activate selected tests."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} tests marked as active.")

    @admin.action(description="Mark selected tests as Inactive")
    def make_inactive(self, request, queryset):
        """Deactivate selected tests."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} tests marked as inactive.")

    @admin.display(description='Question PDF')
    def pdf_file_questions_preview(self, obj):
        """Display clickable link to question PDF."""
        if obj.pdf_file_questions:
            return format_html(
                '<a href="{}" target="_blank">View Question PDF</a>',
                obj.pdf_file_questions.url
            )
        return "No file"

    @admin.display(description='Answer PDF')
    def pdf_file_answers_preview(self, obj):
        """Display clickable link to answer PDF."""
        if obj.pdf_file_answers:
            return format_html(
                '<a href="{}" target="_blank">View Answer PDF</a>',
                obj.pdf_file_answers.url
            )
        return "No file"


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    """Admin configuration for State model."""
    list_display = ('name_english', 'name_hindi', 'code', 'admin', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name_english', 'name_hindi', 'code')
    autocomplete_fields = ['admin']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser model."""
    model = CustomUser
    list_display = (
        'email', 'is_staff', 'is_system_admin', 'is_state_user',
        'is_district_user', 'is_block_user', 'is_school_user'
    )
    list_filter = (
        'is_staff', 'is_system_admin', 'is_state_user',
        'is_district_user', 'is_block_user', 'is_school_user'
    )
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permissions', {
            'fields': (
                'is_staff', 'is_system_admin', 'is_active',
                'groups', 'user_permissions',
                'is_state_user', 'is_district_user', 'is_block_user', 'is_school_user'
            )
        }),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'is_staff', 'is_system_admin', 'is_active',
                'is_state_user', 'is_district_user', 'is_block_user', 'is_school_user'
            )
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """Admin configuration for School model."""
    list_display = ('name', 'admin', 'block', 'created_by', 'created_at')
    list_filter = ('block', 'created_at')
    search_fields = ('name', 'admin__email', 'nic_code')
    autocomplete_fields = ['admin', 'block']


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Admin configuration for Student model."""
    list_display = ('name', 'roll_number', 'class_name', 'school')
    list_filter = ('school', 'class_name')
    search_fields = ('name', 'roll_number')
    autocomplete_fields = ['school']


@admin.register(Marks)
class MarksAdmin(admin.ModelAdmin):
    """Admin configuration for Marks model."""
    list_display = ('id', 'student', 'test', 'marks', 'date')
    list_filter = ('test', 'date')
    search_fields = ('student__name', 'test__test_name')
    autocomplete_fields = ['student', 'test']


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """Admin configuration for Attendance model."""
    list_display = ('student', 'date', 'is_present')
    list_filter = ('date', 'is_present')
    search_fields = ('student__name',)
    autocomplete_fields = ['student']


@admin.register(Block)
class BlockAdmin(admin.ModelAdmin):
    """Admin configuration for Block model."""
    list_display = ('name_english', 'name_hindi', 'district')
    list_filter = ('district',)
    search_fields = ('name_english', 'name_hindi')
    autocomplete_fields = ['district']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    """Admin configuration for District model."""
    list_display = ('name_english', 'name_hindi', 'state', 'admin')
    list_filter = ('state',)
    search_fields = ('name_english', 'name_hindi')
    autocomplete_fields = ['state', 'admin']
