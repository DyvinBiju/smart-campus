import re
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("username", "name", "email", "role", "department", "phone_number", "campus_id", "year_or_semester")
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "role" in self.fields:
            self.fields["role"].required = False
            self.fields["role"].initial = User.Role.STUDENT


def _generate_unique_username(email: str, campus_id: str) -> str:
    """Generate a clean and unique username based on campus_id or email prefix."""
    base = campus_id.strip().lower() if campus_id else email.split("@")[0].strip().lower()
    base = re.sub(r"[^a-zA-Z0-9_.]", "", base) or "user"
    username = base
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}_{counter}"
        counter += 1
    return username


class StudentSignupForm(forms.Form):
    """
    Registration form specifically for Students.
    """

    name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. John Doe"), "class": "form-control"}),
    )
    campus_id = forms.CharField(
        label=_("Student ID / Register Number"),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. CS2024001"), "class": "form-control"}),
    )
    email = forms.EmailField(
        label=_("College Email"),
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": _("e.g. student@campus.edu"), "class": "form-control"}),
    )
    department = forms.CharField(
        label=_("Department / Major"),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Computer Science & Engineering"), "class": "form-control"}),
    )
    year_or_semester = forms.CharField(
        label=_("Year / Semester"),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. 3rd Year / Semester 5"), "class": "form-control"}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Enter secure password"), "class": "form-control"}),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Confirm your password"), "class": "form-control"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", _("The two password fields did not match."))
            else:
                validate_password(password1)
        return cleaned_data

    def save(self) -> User:
        email = self.cleaned_data["email"]
        campus_id = self.cleaned_data["campus_id"].strip()
        username = _generate_unique_username(email, campus_id)

        user = User(
            username=username,
            email=email,
            name=self.cleaned_data["name"].strip(),
            role=User.Role.STUDENT,
            department=self.cleaned_data["department"].strip(),
            campus_id=campus_id,
            year_or_semester=self.cleaned_data["year_or_semester"].strip(),
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class FacultySignupForm(forms.Form):
    """
    Registration form specifically for Faculty / Teachers.
    """

    name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Dr. Jane Smith"), "class": "form-control"}),
    )
    campus_id = forms.CharField(
        label=_("Faculty / Teacher ID"),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. FAC202401"), "class": "form-control"}),
    )
    email = forms.EmailField(
        label=_("College Email"),
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": _("e.g. faculty@campus.edu"), "class": "form-control"}),
    )
    department = forms.CharField(
        label=_("Department"),
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Electrical Engineering"), "class": "form-control"}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Enter secure password"), "class": "form-control"}),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Confirm your password"), "class": "form-control"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", _("The two password fields did not match."))
            else:
                validate_password(password1)
        return cleaned_data

    def save(self) -> User:
        email = self.cleaned_data["email"]
        campus_id = self.cleaned_data["campus_id"].strip()
        username = _generate_unique_username(email, campus_id)

        user = User(
            username=username,
            email=email,
            name=self.cleaned_data["name"].strip(),
            role=User.Role.FACULTY,
            department=self.cleaned_data["department"].strip(),
            campus_id=campus_id,
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class MaintenanceStaffCreationForm(forms.Form):
    """
    Form for Administrators to create Maintenance Staff accounts.
    """

    name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Robert Taylor"), "class": "form-control"}),
    )
    campus_id = forms.CharField(
        label=_("Staff ID"),
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. STF001"), "class": "form-control"}),
    )
    email = forms.EmailField(
        label=_("Staff Email"),
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": _("e.g. staff.robert@campus.edu"), "class": "form-control"}),
    )
    department = forms.CharField(
        label=_("Department / Area"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Electrical Maintenance & HVAC"), "class": "form-control"}),
    )
    password1 = forms.CharField(
        label=_("Initial Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Set initial password"), "class": "form-control"}),
    )
    password2 = forms.CharField(
        label=_("Confirm Initial Password"),
        widget=forms.PasswordInput(attrs={"placeholder": _("Confirm initial password"), "class": "form-control"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account with this email already exists."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2:
            if password1 != password2:
                self.add_error("password2", _("The two password fields did not match."))
            else:
                validate_password(password1)
        return cleaned_data

    def save(self) -> User:
        email = self.cleaned_data["email"]
        campus_id = self.cleaned_data["campus_id"].strip()
        username = _generate_unique_username(email, campus_id)

        user = User(
            username=username,
            email=email,
            name=self.cleaned_data["name"].strip(),
            role=User.Role.MAINTENANCE,
            department=self.cleaned_data.get("department", "").strip(),
            campus_id=campus_id,
            is_staff=True,
        )
        user.set_password(self.cleaned_data["password1"])
        user.save()
        return user


class UserSignupForm(SignupForm):
    """
    Standard allauth signup form for general accounts (defaults to Student).
    """

    PUBLIC_ROLE_CHOICES = [
        (User.Role.STUDENT.value, _("Student")),
        (User.Role.FACULTY.value, _("Faculty / Teacher")),
    ]

    name = forms.CharField(
        label=_("Full Name"),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. John Doe")}),
    )
    role = forms.ChoiceField(
        label=_("Campus Role"),
        choices=PUBLIC_ROLE_CHOICES,
        initial=User.Role.STUDENT.value,
        required=True,
        help_text=_("Select your role on campus. Staff and Admin accounts are provisioned separately."),
    )
    department = forms.CharField(
        label=_("Department / Program"),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. Computer Science & Engineering")}),
    )
    campus_id = forms.CharField(
        label=_("Campus / Roll ID"),
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. CS2024001")}),
    )
    year_or_semester = forms.CharField(
        label=_("Year / Semester"),
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. 3rd Year / Semester 5")}),
    )
    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. +91 9876543210")}),
    )

    def save(self, request):
        user = super().save(request)
        user.name = self.cleaned_data.get("name", "").strip()

        selected_role = self.cleaned_data.get("role", User.Role.STUDENT.value)
        if selected_role not in [User.Role.STUDENT.value, User.Role.FACULTY.value]:
            selected_role = User.Role.STUDENT.value
        user.role = selected_role

        user.department = self.cleaned_data.get("department", "").strip()
        user.campus_id = self.cleaned_data.get("campus_id", "").strip()
        user.year_or_semester = self.cleaned_data.get("year_or_semester", "").strip()
        user.phone_number = self.cleaned_data.get("phone_number", "").strip()
        user.save()
        return user


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    """

    PUBLIC_ROLE_CHOICES = [
        (User.Role.STUDENT.value, _("Student")),
        (User.Role.FACULTY.value, _("Faculty / Teacher")),
    ]

    role = forms.ChoiceField(
        label=_("Campus Role"),
        choices=PUBLIC_ROLE_CHOICES,
        initial=User.Role.STUDENT.value,
        required=True,
    )
    department = forms.CharField(
        label=_("Department / Program"),
        max_length=100,
        required=False,
    )
    campus_id = forms.CharField(
        label=_("Campus / Roll ID"),
        max_length=50,
        required=False,
    )
    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=30,
        required=False,
    )

    def save(self, request):
        user = super().save(request)
        selected_role = self.cleaned_data.get("role", User.Role.STUDENT.value)
        if selected_role not in [User.Role.STUDENT.value, User.Role.FACULTY.value]:
            selected_role = User.Role.STUDENT.value
        user.role = selected_role
        user.department = self.cleaned_data.get("department", "").strip()
        user.campus_id = self.cleaned_data.get("campus_id", "").strip()
        user.phone_number = self.cleaned_data.get("phone_number", "").strip()
        user.save()
        return user


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for regular users to update their personal details.
    """

    class Meta:
        model = User
        fields = ["name", "phone_number", "department", "campus_id", "year_or_semester"]
        labels = {
            "name": _("Full Name"),
            "phone_number": _("Phone Number"),
            "department": _("Department / Program"),
            "campus_id": _("Campus / Roll ID"),
            "year_or_semester": _("Year / Semester"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Your Full Name")}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Contact Phone Number")}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Department or Branch")}),
            "campus_id": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Roll Number or Employee ID")}),
            "year_or_semester": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Year / Semester")}),
        }


