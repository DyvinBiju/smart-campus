"""Tests for the self-service password reset (forgot password) flow."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest
from django.core import mail
from django.urls import reverse

from smart_campus.users.models import User


def _reset_path_from_email(message) -> str:
    match = re.search(
        r"https?://[^\s]+/accounts/password/reset/key/[^\s]+",
        message.body,
    )
    assert match, f"No reset link found in email:\n{message.body}"
    return urlparse(match.group(0)).path


def _open_reset_form(client, path: str) -> str:
    """Follow allauth's token redirect and return the form URL."""
    response = client.get(path, follow=True)
    assert response.status_code == 200
    return response.wsgi_request.path


@pytest.mark.django_db
class TestPasswordReset:
    def test_login_page_shows_forgot_password_link(self, client):
        response = client.get(reverse("account_login"))

        assert response.status_code == 200
        assert reverse("account_reset_password") in response.content.decode()

    def test_student_signup_page_shows_forgot_password_link(self, client):
        response = client.get(reverse("users:student_signup"))

        assert response.status_code == 200
        assert reverse("account_reset_password") in response.content.decode()

    def test_reset_email_is_sent_and_password_can_be_changed(self, client):
        user = User.objects.create_user(
            username="reset_student",
            email="reset.student@campus.edu",
            password="OldSecure123!",
        )
        mail.outbox.clear()

        response = client.post(
            reverse("account_reset_password"),
            {"email": "reset.student@campus.edu"},
        )

        assert response.status_code == 302
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["reset.student@campus.edu"]

        form_path = _open_reset_form(client, _reset_path_from_email(mail.outbox[0]))

        response = client.post(
            form_path,
            {"password1": "NewSecure123!", "password2": "NewSecure123!"},
        )

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.check_password("NewSecure123!")

    def test_unknown_email_gives_same_response_without_reset_link(self, client):
        mail.outbox.clear()

        response = client.post(
            reverse("account_reset_password"),
            {"email": "nobody@campus.edu"},
        )

        assert response.status_code == 302
        assert len(mail.outbox) == 1
        assert "/accounts/password/reset/key/" not in mail.outbox[0].body

    def test_reset_rejects_password_shorter_than_eight_characters(self, client):
        User.objects.create_user(
            username="short_reset",
            email="short.reset@campus.edu",
            password="OldSecure123!",
        )
        mail.outbox.clear()
        client.post(
            reverse("account_reset_password"),
            {"email": "short.reset@campus.edu"},
        )
        form_path = _open_reset_form(client, _reset_path_from_email(mail.outbox[0]))

        response = client.post(
            form_path,
            {"password1": "Abc123!", "password2": "Abc123!"},
        )

        assert response.status_code == 200
        errors = response.context["form"].errors
        assert "password2" in errors or "password1" in errors
