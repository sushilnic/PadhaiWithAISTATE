"""
Forms module for PadhaiWithAI school management application.
Contains all Django form definitions.
"""
import mimetypes

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from captcha.fields import CaptchaField

from .models import Student, Marks, School, CustomUser, Test, State, District, Block, Topper


class LoginForm(forms.Form):
    """Form for user authentication. Accepts EITHER email OR username in
    the `identifier` field — auth backend decides how to match."""
    identifier = forms.CharField(
        max_length=254,
        label='Email or Username',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email or Username',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
        })
    )
    captcha = CaptchaField()

    def clean_identifier(self):
        # Normalise whitespace but keep original casing (backend does iexact)
        return (self.cleaned_data.get('identifier') or '').strip()


class StudentForm(forms.ModelForm):
    """Form for creating and editing student records."""
    class Meta:
        model = Student
        fields = ['name', 'roll_number', 'class_name', 'gender']


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
    """Validate that the uploaded file is a real PDF by checking magic bytes, not just extension."""
    # Read first 4 bytes — PDF files always start with %PDF
    header = file.read(4)
    file.seek(0)
    if header != b'%PDF':
        raise ValidationError("Only PDF files are allowed. The uploaded file does not appear to be a valid PDF.")
    # Secondary check: extension/MIME should also be PDF
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


# ─────────────────────────────────────────────────────────────────────────────
# Topper — weekly showcase upload form (district admin)
# ─────────────────────────────────────────────────────────────────────────────

TOPPER_IMAGE_MAX_BYTES = 2 * 1024 * 1024                       # 2 MB
TOPPER_IMAGE_ALLOWED = ('image/jpeg', 'image/png', 'image/webp')
TOPPER_MAGIC_JPEG = b'\xff\xd8\xff'
TOPPER_MAGIC_PNG  = b'\x89PNG\r\n\x1a\n'
TOPPER_MAGIC_WEBP_PREFIX = (b'RIFF', b'WEBP')


class TopperForm(forms.ModelForm):
    """Form used by district admins to upload/edit a topper."""

    class Meta:
        model = Topper
        fields = ['name', 'caption', 'school', 'image',
                  'week_start', 'week_end', 'is_active', 'order']
        widgets = {
            'name':       forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'caption':    forms.TextInput(attrs=FORM_CONTROL_ATTRS),
            'school':     forms.Select(attrs=FORM_CONTROL_ATTRS),
            'week_start': forms.DateInput(attrs={**FORM_CONTROL_ATTRS, 'type': 'date'}),
            'week_end':   forms.DateInput(attrs={**FORM_CONTROL_ATTRS, 'type': 'date'}),
            'order':      forms.NumberInput(attrs={**FORM_CONTROL_ATTRS, 'min': 0}),
        }

    def __init__(self, *args, district=None, **kwargs):
        """`district` limits the School dropdown to that district's schools."""
        super().__init__(*args, **kwargs)
        if district is not None:
            self.fields['school'].queryset = School.objects.filter(block__district=district).order_by('name')
        # Image is mandatory only on create; on edit, keep existing if user leaves it blank.
        if self.instance and self.instance.pk:
            self.fields['image'].required = False

    def clean(self):
        data = super().clean()
        ws = data.get('week_start')
        we = data.get('week_end')
        if ws and we and we < ws:
            raise ValidationError({'week_end': 'Week end must be on or after week start.'})
        return data

    def clean_image(self):
        img = self.cleaned_data.get('image')
        if not img:
            # Only allowed on edit (see __init__); the parent field enforcement covers create
            return img

        # Size cap
        if img.size > TOPPER_IMAGE_MAX_BYTES:
            raise ValidationError('Image must be smaller than 2 MB.')

        # Content-type check (browser-declared — weak but fast)
        ct = getattr(img, 'content_type', '') or mimetypes.guess_type(img.name)[0] or ''
        if ct not in TOPPER_IMAGE_ALLOWED:
            raise ValidationError('Only JPEG, PNG, or WEBP images are allowed.')

        # Magic-byte check — defence against renamed extensions
        head = img.read(16)
        img.seek(0)
        ok = (
            head.startswith(TOPPER_MAGIC_JPEG) or
            head.startswith(TOPPER_MAGIC_PNG) or
            (head[:4] == TOPPER_MAGIC_WEBP_PREFIX[0] and head[8:12] == TOPPER_MAGIC_WEBP_PREFIX[1])
        )
        if not ok:
            raise ValidationError('The uploaded file is not a valid image.')

        return img
