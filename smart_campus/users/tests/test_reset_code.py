"""Tests for the admin-issued password reset code flow."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from smart_campus.users.forms import CodePasswordResetForm
from smart_campus.users.models import PasswordResetCode
from smart_campus.users.models import User
from smart_campus.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_reset_cache():
    cache.clear()
    yield
    cache.clear()


def _issue_code(client, target) -> str:
    response = client.post(reverse("users:issue_reset_code", args=[target.pk]))
    assert response.status_code == 200
    return response.context["reset_code"]


def _reset(client, username, code, password="NewSecure123!"):
    return client.post(
        reverse("demo_password_reset"),
        {
            "username": username,
            "code": code,
            "password1": password,
            "password2": password,
        },
    )


@pytest.mark.django_db
class TestAdminIssuedResetCode:
    def test_login_and_signup_pages_link_to_demo_reset(self, client):
        for url in (
            reverse("account_login"),
            reverse("users:student_signup"),
        ):
            response = client.get(url)
            assert response.status_code == 200
            assert reverse("demo_password_reset") in response.content.decode()

    def test_admin_issues_code_and_student_resets_password(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)

        code = _issue_code(client, student)

        record = PasswordResetCode.objects.get(user=student)
        assert record.code_hash != code
        assert record.matches(code)
        assert record.is_usable

        client.logout()
        response = _reset(client, student.username, code.lower())

        assert response.status_code == 302
        student.refresh_from_db()
        assert student.check_password("NewSecure123!")
        record.refresh_from_db()
        assert record.used_at is not None

    def test_student_can_reset_with_email(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(
            email="student.demo@gmail.com",
            password="OldSecure123!",
        )
        client.force_login(admin)
        code = _issue_code(client, student)
        client.logout()

        response = _reset(client, "Student.Demo@Gmail.com", code)

        assert response.status_code == 302
        student.refresh_from_db()
        assert student.check_password("NewSecure123!")

    def test_code_is_single_use(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)
        code = _issue_code(client, student)
        client.logout()

        assert _reset(client, student.username, code).status_code == 302
        response = _reset(client, student.username, code, password="Another123!")

        assert response.status_code == 200
        assert response.context["form"].non_field_errors()

    def test_wrong_code_is_rejected(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)
        _issue_code(client, student)
        client.logout()

        response = _reset(client, student.username, "WRONG123")

        assert response.status_code == 200
        assert response.context["form"].non_field_errors()
        student.refresh_from_db()
        assert student.check_password("OldSecure123!")

    def test_expired_code_is_rejected(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)
        code = _issue_code(client, student)
        client.logout()

        PasswordResetCode.objects.filter(user=student).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )

        response = _reset(client, student.username, code)

        assert response.status_code == 200
        assert response.context["form"].non_field_errors()

    def test_issuing_new_code_invalidates_previous_one(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)

        first_code = _issue_code(client, student)
        second_code = _issue_code(client, student)
        client.logout()

        assert _reset(client, student.username, first_code).status_code == 200
        assert _reset(client, student.username, second_code).status_code == 302

    def test_short_password_is_rejected(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        student = UserFactory(password="OldSecure123!")
        client.force_login(admin)
        code = _issue_code(client, student)
        client.logout()

        response = _reset(client, student.username, code, password="Abc123!")

        assert response.status_code == 200
        errors = response.context["form"].errors
        assert "password1" in errors or "password2" in errors
        student.refresh_from_db()
        assert student.check_password("OldSecure123!")

    def test_non_admin_cannot_issue_code(self, client):
        student = UserFactory(password="OldSecure123!")
        other_student = UserFactory(password="OldSecure123!")
        client.force_login(student)

        response = client.post(
            reverse("users:issue_reset_code", args=[other_student.pk])
        )

        assert response.status_code == 403
        assert not PasswordResetCode.objects.filter(user=other_student).exists()

    def test_admin_account_cannot_receive_code(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        other_admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        client.force_login(admin)

        response = client.post(
            reverse("users:issue_reset_code", args=[other_admin.pk])
        )

        assert response.status_code == 302
        assert not PasswordResetCode.objects.filter(user=other_admin).exists()

    def test_repeated_failures_are_rate_limited(self, client):
        student = UserFactory(password="OldSecure123!")

        for _ in range(CodePasswordResetForm.MAX_ATTEMPTS):
            assert _reset(client, student.username, "WRONG123").status_code == 200

        response = _reset(client, student.username, "WRONG123")
        assert response.status_code == 200
        errors = " ".join(response.context["form"].non_field_errors())
        assert "Too many failed attempts" in errors
