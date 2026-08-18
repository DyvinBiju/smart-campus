from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from smart_campus.users.forms import UserProfileUpdateForm
from smart_campus.users.tests.factories import UserFactory
from smart_campus.users.views import UserRedirectView
from smart_campus.users.views import UserUpdateView
from smart_campus.users.views import user_detail_view

if TYPE_CHECKING:
    from django.test import RequestFactory

    from smart_campus.users.models import User

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.post("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserProfileUpdateForm(
            data={
                "name": "Updated Name",
                "phone_number": "9876543210",
                "department": "Mechanical",
                "campus_id": "ME202401",
            },
            instance=user,
        )
        assert form.is_valid()
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]
        assert user.name == "Updated Name"
        assert user.department == "Mechanical"


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == f"/users/{user.username}/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory.create()
        response = user_detail_view(request, username=user.username)

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"


class TestUserAuthenticationFlows:
    def test_login_valid_credentials(self, client, user: User):
        from allauth.account.models import EmailAddress

        user.set_password("CorrectP@ssword123!")
        user.save()
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.username,
                "password": "CorrectP@ssword123!",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        redirect_url = reverse("users:redirect")
        assert response.url == redirect_url

    def test_login_unverified_email_redirects_to_confirm(self, client, user: User):
        user.set_password("CorrectP@ssword123!")
        user.save()

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.username,
                "password": "CorrectP@ssword123!",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("account_email_verification_sent")

    def test_login_invalid_credentials(self, client, user: User):
        user.set_password("CorrectP@ssword123!")
        user.save()

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.username,
                "password": "WrongPassword!",
            },
        )
        assert response.status_code == HTTPStatus.OK
        assert "_auth_user_id" not in client.session

    def test_logout(self, client, user: User):
        client.force_login(user)
        logout_url = reverse("account_logout")

        # GET asks for confirmation or POST performs logout
        response = client.post(logout_url)
        assert response.status_code == HTTPStatus.FOUND
        assert "_auth_user_id" not in client.session

    def test_profile_update_client_flow(self, client, user: User):
        client.force_login(user)
        update_url = reverse("users:update")

        response = client.post(
            update_url,
            data={
                "name": "Updated via Client",
                "phone_number": "9876543210",
                "department": "Civil Engineering",
                "campus_id": "CIVIL2024",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == user.get_absolute_url()

        user.refresh_from_db()
        assert user.name == "Updated via Client"
        assert user.department == "Civil Engineering"
        assert user.campus_id == "CIVIL2024"
        assert user.phone_number == "9876543210"

    def test_profile_update_unauthenticated_redirects(self, client):
        update_url = reverse("users:update")
        response = client.get(update_url)
        assert response.status_code == HTTPStatus.FOUND
        login_url = reverse("account_login")
        assert response.url == f"{login_url}?next={update_url}"


