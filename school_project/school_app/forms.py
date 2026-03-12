"""
Forms module for PadhaiWithAI school management application.
Contains all Django form definitions.
"""
import mimetypes

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from captcha.fields import CaptchaField

from .models import Student, Marks, School, CustomUser, Test, State, District, Block


class LoginForm(forms.Form):
    """Form for user authentication with email and CAPTCHA."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Login email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    captcha = CaptchaField()


class StudentForm(forms.ModelForm):
    """Form for creating and editing student records."""
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'class_name']


class MarksForm(forms.ModelForm):
    """Form for recording student test marks."""
    class Meta:
        model = Marks
        fields = ['student', 'marks', 'test']


class SchoolForm(forms.ModelForm):
    """Basic form for school creation."""
    class Meta:
        model = School
        fields = ['name']


class SchoolAdminRegistrationForm(forms.ModelForm):
    """Form for creating a school with its admin user."""
    admin_email = forms.EmailField()
    admin_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = School
        fields = ['name', 'admin_email', 'admin_password']

    def save(self, commit=True, created_by=None):
        school = super().save(commit=False)

        # Create school admin user
        admin_user = CustomUser.objects.create_user(
            email=self.cleaned_data['admin_email'],
            password=self.cleaned_data['admin_password'],
        )

        school.admin = admin_user
        school.created_by = created_by

        if commit:
            school.save()
        return school


def validate_pdf(file):
    """Validate that the uploaded file is a PDF."""
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type != 'application/pdf':
        raise ValidationError("Only PDF files are allowed.")
    return file


class TestForm(forms.ModelForm):
    """Form for creating and managing tests with PDF uploads."""

    # Validators
    alphanumeric_validator = RegexValidator(
        regex=r'^[A-Za-z0-9 ]+$',
        message='This field should only contain letters, numbers, and spaces.'
    )

    # Form fields
    test_name = forms.CharField(
        required=True,
        max_length=100,
        validators=[alphanumeric_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Test Name',
            'style': 'font-size: 1.1em; padding: 10px; text-transform: capitalize;',
        })
    )

    subject_name = forms.CharField(
        required=True,
        max_length=100,
        validators=[alphanumeric_validator],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Subject Name',
            'style': 'font-size: 1.1em; padding: 10px; text-transform: capitalize;',
        })
    )

    test_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': 'Select Test date',
        }),
    )

    pdf_file_questions = forms.FileField(
        required=True,
        validators=[validate_pdf],
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'placeholder': 'Select Questions file',
        })
    )

    pdf_file_answers = forms.FileField(
        required=True,
        validators=[validate_pdf],
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf',
            'placeholder': 'Select Answer file',
        })
    )

    max_marks = forms.FloatField(
        max_value=500,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max marks of the test'
        }),
        label="Max Marks"
    )

    class Meta:
        model = Test
        fields = [
            'test_name', 'subject_name', 'pdf_file_questions',
            'pdf_file_answers', 'test_date', 'max_marks'
        ]

    def clean_max_marks(self):
        """Validate that max_marks is a positive number."""
        max_marks = self.cleaned_data.get('max_marks')
        if max_marks is not None and max_marks <= 0:
            raise ValidationError('Max marks must be greater than zero.')
        return max_marks


class ExcelFileUploadForm(forms.Form):
    """Form for uploading Excel files for bulk data import."""
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls'
        })
    )


# ===== Hierarchical User Management Forms =====

FORM_CONTROL_ATTRS = {'class': 'form-control'}
PASSWORD_ATTRS = {'class': 'form-control', 'type': 'password'}


class StateCreateForm(forms.Form):
    """Form for creating a State with its admin user."""
    name_english = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'State name in English'}),
        label='State Name (English)'
    )
    name_hindi = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'State name in Hindi'}),
        label='State Name (Hindi)'
    )
    code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'e.g. RJ'}),
        label='State Code'
    )
    admin_email = forms.EmailField(
        widget=forms.EmailInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin email'}),
        label='Admin Email'
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin password'}),
        label='Admin Password'
    )

    def clean_code(self):
        code = self.cleaned_data['code'].upper()
        if State.objects.filter(code=code).exists():
            raise ValidationError('A state with this code already exists.')
        return code

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email


class StateEditForm(forms.ModelForm):
    """Form for editing State info (no password)."""
    class Meta:
        model = State
        fields = ['name_english', 'name_hindi', 'code']
        widgets = {
            'name_english': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'name_hindi': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'code': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
        }


class DistrictCreateForm(forms.Form):
    """Form for creating a District with its admin user."""
    name_english = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'District name in English'}),
        label='District Name (English)'
    )
    name_hindi = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'District name in Hindi'}),
        label='District Name (Hindi)'
    )
    admin_email = forms.EmailField(
        widget=forms.EmailInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin email'}),
        label='Admin Email'
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin password'}),
        label='Admin Password'
    )

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email


class DistrictEditForm(forms.ModelForm):
    """Form for editing District info (no password)."""
    class Meta:
        model = District
        fields = ['name_english', 'name_hindi']
        widgets = {
            'name_english': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'name_hindi': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
        }


class BlockCreateForm(forms.Form):
    """Form for creating a Block with its admin user."""
    name_english = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Block name in English'}),
        label='Block Name (English)'
    )
    name_hindi = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Block name in Hindi'}),
        label='Block Name (Hindi)'
    )
    district = forms.ModelChoiceField(
        queryset=District.objects.none(),
        widget=forms.Select(attrs=FORM_CONTROL_ATTRS),
        label='District'
    )
    admin_email = forms.EmailField(
        widget=forms.EmailInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin email'}),
        label='Admin Email'
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin password'}),
        label='Admin Password'
    )

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email


class BlockEditForm(forms.ModelForm):
    """Form for editing Block info (no password)."""
    class Meta:
        model = Block
        fields = ['name_english', 'name_hindi']
        widgets = {
            'name_english': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'name_hindi': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
        }


class SchoolCreateForm(forms.Form):
    """Form for creating a School with its admin user."""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'School name'}),
        label='School Name'
    )
    block = forms.ModelChoiceField(
        queryset=Block.objects.none(),
        widget=forms.Select(attrs=FORM_CONTROL_ATTRS),
        label='Block'
    )
    nic_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'NIC Code (optional)'}),
        label='NIC Code'
    )
    admin_email = forms.EmailField(
        widget=forms.EmailInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin email'}),
        label='Admin Email'
    )
    admin_password = forms.CharField(
        widget=forms.PasswordInput(attrs={**FORM_CONTROL_ATTRS, 'placeholder': 'Admin password'}),
        label='Admin Password'
    )

    def clean_admin_email(self):
        email = self.cleaned_data['admin_email']
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email


class SchoolEditForm(forms.ModelForm):
    """Form for editing School info (no password)."""
    class Meta:
        model = School
        fields = ['name', 'nic_code']
        widgets = {
            'name': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'nic_code': forms.TextInput(attrs=FORM_CONTROL_ATTRS),
        }
