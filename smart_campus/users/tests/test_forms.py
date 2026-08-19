"""Module for all Form Tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest
from django.test import RequestFactory
from django.utils.translation import gettext_lazy as _

from smart_campus.users.forms import FacultySignupForm
from smart_campus.users.forms import MaintenanceStaffCreationForm
from smart_campus.users.forms import StudentSignupForm
from smart_campus.users.forms import UserAdminCreationForm
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


class TestFacultySignupForm:
    def test_valid_faculty_signup(self, db):
        form = FacultySignupForm(
            data={
                "name": "Prof. Alan Turing",
                "campus_id": "FAC1001",
                "email": "turing@campus.edu",
                "department": "Mathematics & CS",
                "password1": "SecureP@ssword123!",
                "password2": "SecureP@ssword123!",
            },
        )
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.name == "Prof. Alan Turing"
        assert user.campus_id == "FAC1001"
        assert user.email == "turing@campus.edu"
        assert user.department == "Mathematics & CS"
        assert user.role == User.Role.FACULTY
        assert user.is_faculty is True
        assert user.check_password("SecureP@ssword123!")


class TestMaintenanceStaffCreationForm:
    def test_valid_maintenance_creation(self, db):
        form = MaintenanceStaffCreationForm(
            data={
                "name": "John Maintenance",
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
                "phone_number": "+91 9876543210",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        assert "role" not in form.fields
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.role == User.Role.STUDENT
        assert user.phone_number == "+91 9876543210"

    def test_faculty_form_has_no_role_field_and_supports_phone(self, db):
        form = FacultySignupForm(
            data={
                "name": "Faculty Phone",
                "campus_id": "FAC999",
                "email": "fac.phone@campus.edu",
                "department": "Physics",
                "phone_number": "+91 9123456780",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!",
            },
        )
        assert "role" not in form.fields
        assert form.is_valid(), form.errors
        user = form.save()
        assert user.role == User.Role.FACULTY
        assert user.phone_number == "+91 9123456780"

    def test_user_signup_form_has_no_role_field(self):
        form = UserSignupForm()
        assert "role" not in form.fields



