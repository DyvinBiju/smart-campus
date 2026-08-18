"""Module for all Form Tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest
from django.test import RequestFactory
from django.utils.translation import gettext_lazy as _

from smart_campus.users.forms import UserAdminCreationForm
from smart_campus.users.forms import UserProfileUpdateForm
from smart_campus.users.forms import UserSignupForm
from smart_campus.users.models import User

if TYPE_CHECKING:
    pass


class TestUserAdminCreationForm:
    """
    Test class for all tests related to the UserAdminCreationForm
    """

    def test_username_validation_error_msg(self, user: User):
        """
        Tests UserAdminCreation Form's unique validator functions correctly by testing:
            1) A new user with an existing username cannot be added.
            2) Only 1 error is raised by the UserCreation Form
            3) The desired error message is raised
        """
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


class TestUserSignupForm:
    def _prepare_request(self, rf: RequestFactory) -> HttpRequest:
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware

        request = rf.post("/accounts/signup/")
        SessionMiddleware(lambda req: None).process_request(request)
        MessageMiddleware(lambda req: None).process_request(request)
        return request

    def test_valid_signup_student(self, rf: RequestFactory, db):
        request = self._prepare_request(rf)
        form = UserSignupForm(
            data={
                "username": "alice_student",
                "email": "alice@campus.edu",
                "password1": "StrongP@ssw0rd123!",
                "password2": "StrongP@ssw0rd123!",
                "name": "Alice Wonderland",
                "role": User.Role.STUDENT.value,
                "department": "Computer Science",
                "campus_id": "CS2024001",
                "phone_number": "1234567890",
            },
        )
        assert form.is_valid(), form.errors
        user = form.save(request)
        assert user.username == "alice_student"
        assert user.name == "Alice Wonderland"
        assert user.role == User.Role.STUDENT
        assert user.department == "Computer Science"
        assert user.campus_id == "CS2024001"
        assert user.phone_number == "1234567890"
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_valid_signup_faculty(self, rf: RequestFactory, db):
        request = self._prepare_request(rf)
        form = UserSignupForm(
            data={
                "username": "dr_smith",
                "email": "smith@campus.edu",
                "password1": "StrongP@ssw0rd123!",
                "password2": "StrongP@ssw0rd123!",
                "name": "Dr. Smith",
                "role": User.Role.FACULTY.value,
                "department": "Physics",
                "campus_id": "FAC9901",
                "phone_number": "9876543210",
            },
        )
        assert form.is_valid(), form.errors
        user = form.save(request)
        assert user.role == User.Role.FACULTY
        assert user.is_faculty is True

    def test_signup_prevents_admin_privilege_escalation(self, rf: RequestFactory, db):
        """Ensures that attempting to submit ADMIN or STAFF role through signup is not allowed."""
        form = UserSignupForm(
            data={
                "username": "sneaky_user",
                "email": "sneaky@campus.edu",
                "password1": "StrongP@ssw0rd123!",
                "password2": "StrongP@ssw0rd123!",
                "name": "Sneaky User",
                "role": "ADMIN",
                "department": "IT",
            },
        )
        assert not form.is_valid()
        assert "role" in form.errors


class TestUserProfileUpdateForm:
    def test_valid_profile_update(self, user: User):
        form = UserProfileUpdateForm(
            data={
                "name": "Updated Name",
                "phone_number": "+1234567890",
                "department": "Electrical Engineering",
                "campus_id": "EE2024042",
            },
            instance=user,
        )
        assert form.is_valid(), form.errors
        updated_user = form.save()
        assert updated_user.name == "Updated Name"
        assert updated_user.phone_number == "+1234567890"
        assert updated_user.department == "Electrical Engineering"
        assert updated_user.campus_id == "EE2024042"

