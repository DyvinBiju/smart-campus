from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ("username", "name", "email", "role", "department", "phone_number", "campus_id")
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "role" in self.fields:
            self.fields["role"].required = False
            self.fields["role"].initial = User.Role.STUDENT



class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Enforces that public registration can only assign general user roles (Student or Faculty)
    and prevents privilege escalation to Staff/Admin.
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
    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _("e.g. +91 9876543210")}),
    )

    def save(self, request):
        user = super().save(request)
        user.name = self.cleaned_data.get("name", "").strip()

        # Security check: never allow public escalation to STAFF or ADMIN
        selected_role = self.cleaned_data.get("role", User.Role.STUDENT.value)
        if selected_role not in [User.Role.STUDENT.value, User.Role.FACULTY.value]:
            selected_role = User.Role.STUDENT.value
        user.role = selected_role

        user.department = self.cleaned_data.get("department", "").strip()
        user.campus_id = self.cleaned_data.get("campus_id", "").strip()
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
        max_length=20,
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
    Role and administrative permissions are excluded to prevent privilege escalation.
    """

    class Meta:
        model = User
        fields = ["name", "phone_number", "department", "campus_id"]
        labels = {
            "name": _("Full Name"),
            "phone_number": _("Phone Number"),
            "department": _("Department / Program"),
            "campus_id": _("Campus / Roll ID"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Your Full Name")}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Contact Phone Number")}),
            "department": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Department or Branch")}),
            "campus_id": forms.TextInput(attrs={"class": "form-control", "placeholder": _("Roll Number or Employee ID")}),
        }

