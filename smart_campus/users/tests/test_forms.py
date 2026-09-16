"""Module for all Form Tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest
from django.test import RequestFactory
from django.utils.translation import gettext_lazy as _

from smart_campus.users.forms import MaintenanceStaffCreationForm
from smart_campus.users.forms import StudentSignupForm
from smart_campus.users.forms import UserAdminCreationForm
from smart_campus.users.forms import UserManagementCreateForm
from smart_campus.users.forms import UserSignupForm
from smart_campus.users.models import User

if TYPE_CHECKING:
    pass


class TestUserAdminCreationForm:
    def test_username_validation_error_msg(self, user: User):
        form = UserAdminCreationForm(
            {
                "username": user.username,
                "password1": user.password,
                "password2": user.password,
            },
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "username" in form.errors
        assert form.errors["username"][0] == _("This username has already been taken.")


class TestStudentSignupForm:
    def test_valid_student_signup(self, db):
        form = StudentSignupForm(
            data={
                "name": "Sarah Student",
                "campus_id": "CS202499",
                "email": "sarah@campus.edu",
                "department": "Computer Science",
                "year_or_semester": "4th Year / Sem 7",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            },
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.name == "Sarah Student"
        assert user.campus_id == "CS202499"
        assert user.email == "sarah@campus.edu"
        assert user.department == "Computer Science"
        assert user.year_or_semester == "4th Year / Sem 7"
        assert user.role == User.Role.STUDENT
        assert user.is_student is True
        assert user.check_password("SecureP@ssword123!")

    def test_student_signup_rejects_blank_name_and_whitespace_email(self, db):
        form = StudentSignupForm(
            data={
                "name": "   ",
                "campus_id": "CS202499",
                "email": "   ",
                "department": "Computer Science",
                "year_or_semester": "4th Year",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            },
        )
        assert not form.is_valid()
        assert "name" in form.errors
        assert "email" in form.errors

    def test_student_signup_password_mismatch(self, db):
        form = StudentSignupForm(
            data={
                "name": "Sarah Student",
                "campus_id": "CS202499",
                "email": "sarah@campus.edu",
                "department": "Computer Science",
                "year_or_semester": "4th Year",
                "password1": "SecureP@ssword123!",
                "password2": "DifferentPassword!",
            },
        )
        assert not form.is_valid()
        assert "password2" in form.errors

    def test_duplicate_email_rejected_case_insensitive(self, db):
        User.objects.create_user(
            username="existing-user",
            email="sarah@campus.edu",
            password="SecureP@ssword123!",
            name="Existing User",
        )
        form = StudentSignupForm(
            data={
                "name": "Sarah Student",
                "campus_id": "CS202500",
                "email": "SARAH@campus.edu",
                "department": "Computer Science",
                "year_or_semester": "4th Year",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            },
        )
        assert not form.is_valid()
        assert "email" in form.errors


class TestMaintenanceStaffCreationForm:
    def test_valid_maintenance_creation(self, db):
        form = MaintenanceStaffCreationForm(
            data={
                "name": "John Maintenance",
                "specialization": "Electrical",
                "campus_id": "STF888",
                "email": "john.staff@campus.edu",
                "department": "Electrical & HVAC",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            },
        )
        assert form.is_valid(), form.errors
        staff_user = form.save()
        assert staff_user.name == "John Maintenance"
        assert staff_user.campus_id == "STF888"
        assert staff_user.email == "john.staff@campus.edu"
        assert staff_user.role == User.Role.MAINTENANCE
        assert staff_user.is_maintenance_staff is True
        assert staff_user.is_staff is True
        assert staff_user.check_password("SecureP@ssword123!")




class TestSignupFormNoRoleDropdown:
    def test_student_form_has_no_role_field_and_supports_phone(self, db):
        form = StudentSignupForm(
            data={
                "name": "Student Phone",
                "campus_id": "STU999",
                "email": "stu.phone@campus.edu",
                "department": "Computer Science",
                "year_or_semester": "1st Year",
                "phone_number": "9876543210",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        assert "role" not in form.fields
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.role == User.Role.STUDENT
        assert user.phone_number == "9876543210"

    def test_student_signup_rejects_phone_number_longer_than_10_digits(self, db):
        form = StudentSignupForm(data={"phone_number": "12345678901"})

        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_student_signup_rejects_non_numeric_phone_number(self, db):
        form = StudentSignupForm(data={"phone_number": "98765abc10"})

        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_user_signup_form_has_no_role_field(self):
        form = UserSignupForm()
        assert "role" not in form.fields


def _valid_student_data(**overrides):
    data = {
        "name": "Validation Student",
        "campus_id": "CS202501",
        "email": "validation.student@campus.edu",
        "department": "Computer Science",
        "year_or_semester": "2nd Year",
        "password1": "SecureP@ssword123!",
        "password2": "SecureP@ssword123!",
    }
    data.update(overrides)
    return data


class TestPhoneNumberValidation:
    """Phone numbers must be empty or exactly 10 digits, numbers only."""

    def test_valid_10_digit_phone_accepted(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="9876543210"))
        assert form.is_valid(), form.errors
        assert form.cleaned_data["phone_number"] == "9876543210"

    def test_blank_phone_allowed_when_optional(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number=""))
        assert form.is_valid(), form.errors

    def test_short_phone_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="987654321"))
        assert not form.is_valid()
        assert "phone_number" in form.errors
        assert form.errors["phone_number"][0] == _(
            "Enter a valid 10-digit phone number containing numbers only."
        )

    def test_long_phone_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="98765432101"))
        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_phone_with_letters_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="98765abc10"))
        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_phone_with_spaces_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="98765 43210"))
        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_phone_with_hyphen_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="98765-43210"))
        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_phone_with_country_code_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(phone_number="+919876543210"))
        assert not form.is_valid()
        assert "phone_number" in form.errors

    def test_management_create_form_enforces_same_phone_rule(self, db):
        form = UserManagementCreateForm(
            data={
                "name": "Phone Check",
                "email": "phone.check@campus.edu",
                "role": User.Role.STUDENT,
                "phone_number": "98 7654321",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            }
        )
        assert not form.is_valid()
        assert "phone_number" in form.errors


class TestPasswordValidation:
    def test_short_password_rejected_with_clear_message(self, db):
        form = StudentSignupForm(
            data=_valid_student_data(password1="Abc123!", password2="Abc123!")
        )
        assert not form.is_valid()
        assert "password1" in form.errors
        assert form.errors["password1"][0] == _(
            "Password must contain at least 8 characters."
        )

    def test_password_mismatch_message(self, db):
        form = StudentSignupForm(
            data=_valid_student_data(
                password1="SecureP@ssword123!", password2="OtherP@ssword123!"
            )
        )
        assert not form.is_valid()
        assert form.errors["password2"][0] == _("Passwords do not match.")


class TestEmailAndRequiredTextValidation:
    def test_malformed_emails_rejected(self, db):
        for bad_email in ["example", "example@", "@example.com", "example@gmail", "example.com"]:
            form = StudentSignupForm(data=_valid_student_data(email=bad_email))
            assert not form.is_valid(), bad_email
            assert "email" in form.errors

    def test_whitespace_only_campus_id_rejected(self, db):
        form = StudentSignupForm(data=_valid_student_data(campus_id="   "))
        assert not form.is_valid()
        assert "campus_id" in form.errors



