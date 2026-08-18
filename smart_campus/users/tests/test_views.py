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
from smart_campus.users.models import User
from smart_campus.users.tests.factories import UserFactory
from smart_campus.users.views import UserRedirectView
from smart_campus.users.views import UserUpdateView
from smart_campus.users.views import user_detail_view

if TYPE_CHECKING:
    from django.test import RequestFactory

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


class TestStudentSignupView:
    def test_get_student_signup_page(self, client):
        response = client.get(reverse("users:student_signup"))
        assert response.status_code == HTTPStatus.OK
        assert "Student Registration" in response.content.decode()

    def test_post_student_signup(self, client):
        response = client.post(
            reverse("users:student_signup"),
            data={
                "name": "Alex Student",
                "campus_id": "STU101",
                "email": "alex.student@campus.edu",
                "department": "Computer Science",
                "year_or_semester": "3rd Year",
                "password1": "SecureP@ss123!",
                "password2": "SecureP@ss123!",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("users:student_dashboard")

        user = User.objects.get(email="alex.student@campus.edu")
        assert user.role == User.Role.STUDENT
        assert user.is_student is True
        assert "_auth_user_id" in client.session


class TestFacultySignupView:
    def test_get_faculty_signup_page(self, client):
        response = client.get(reverse("users:faculty_signup"))
        assert response.status_code == HTTPStatus.OK
        assert "Faculty & Teacher Registration" in response.content.decode()

    def test_post_faculty_signup(self, client):
        response = client.post(
            reverse("users:faculty_signup"),
            data={
                "name": "Dr. Grace Hopper",
                "campus_id": "FAC505",
                "email": "grace.hopper@campus.edu",
                "department": "Computer Science",
                "password1": "SecureP@ss123!",
                "password2": "SecureP@ss123!",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("users:faculty_dashboard")

        user = User.objects.get(email="grace.hopper@campus.edu")
        assert user.role == User.Role.FACULTY
        assert user.is_faculty is True
        assert "_auth_user_id" in client.session


class TestRoleDashboardViewsAndAccessControl:
    def test_student_dashboard_access(self, client):
        student = User.objects.create_user(
            username="stu_user", email="stu@campus.edu", password="password", role=User.Role.STUDENT
        )
        client.force_login(student)

        # Student accessing Student Dashboard -> OK
        res = client.get(reverse("users:student_dashboard"))
        assert res.status_code == HTTPStatus.OK

        # Student attempting to access other dashboards -> 403 Forbidden
        res = client.get(reverse("users:faculty_dashboard"))
        assert res.status_code == HTTPStatus.FORBIDDEN

        res = client.get(reverse("users:maintenance_dashboard"))
        assert res.status_code == HTTPStatus.FORBIDDEN

        res = client.get(reverse("users:admin_dashboard"))
        assert res.status_code == HTTPStatus.FORBIDDEN

    def test_faculty_dashboard_access(self, client):
        faculty = User.objects.create_user(
            username="fac_user", email="fac@campus.edu", password="password", role=User.Role.FACULTY
        )
        client.force_login(faculty)

        # Faculty accessing Faculty Dashboard -> OK
        res = client.get(reverse("users:faculty_dashboard"))
        assert res.status_code == HTTPStatus.OK

        # Faculty accessing Student Dashboard -> 403 Forbidden
        res = client.get(reverse("users:student_dashboard"))
        assert res.status_code == HTTPStatus.FORBIDDEN

    def test_maintenance_dashboard_access(self, client):
        maintenance = User.objects.create_user(
            username="maint_user", email="maint@campus.edu", password="password", role=User.Role.MAINTENANCE
        )
        client.force_login(maintenance)

        # Maintenance staff accessing Maintenance Dashboard -> OK
        res = client.get(reverse("users:maintenance_dashboard"))
        assert res.status_code == HTTPStatus.OK

        # Maintenance accessing Admin Dashboard -> 403 Forbidden
        res = client.get(reverse("users:admin_dashboard"))
        assert res.status_code == HTTPStatus.FORBIDDEN

    def test_admin_dashboard_access_and_staff_creation(self, client):
        admin_user = User.objects.create_superuser(
            username="super_admin", email="admin@campus.edu", password="password", role=User.Role.ADMIN
        )
        client.force_login(admin_user)

        # Admin accessing Admin Dashboard -> OK
        res = client.get(reverse("users:admin_dashboard"))
        assert res.status_code == HTTPStatus.OK

        # Admin creating a Maintenance Staff account via the dashboard form
        res = client.post(
            reverse("users:admin_dashboard"),
            data={
                "name": "Tom Plumber",
                "campus_id": "STF777",
                "email": "tom.plumber@campus.edu",
                "department": "Plumbing & Water Systems",
                "password1": "SecureStaffP@ss1!",
                "password2": "SecureStaffP@ss1!",
            },
        )
        assert res.status_code == HTTPStatus.FOUND
        assert res.url == reverse("users:admin_dashboard")

        staff = User.objects.get(email="tom.plumber@campus.edu")
        assert staff.role == User.Role.MAINTENANCE
        assert staff.is_maintenance_staff is True
        assert staff.is_staff is True

    def test_unauthenticated_dashboard_access_redirects(self, client):
        res = client.get(reverse("users:student_dashboard"))
        assert res.status_code == HTTPStatus.FOUND
        login_url = reverse("account_login")
        assert login_url in res.url


class TestUserRedirectView:
    def test_student_redirect(self, client):
        student = User.objects.create_user(username="stu_red", role=User.Role.STUDENT)
        client.force_login(student)
        res = client.get(reverse("users:redirect"))
        assert res.status_code == HTTPStatus.FOUND
        assert res.url == reverse("users:student_dashboard")

    def test_faculty_redirect(self, client):
        faculty = User.objects.create_user(username="fac_red", role=User.Role.FACULTY)
        client.force_login(faculty)
        res = client.get(reverse("users:redirect"))
        assert res.status_code == HTTPStatus.FOUND
        assert res.url == reverse("users:faculty_dashboard")

    def test_maintenance_redirect(self, client):
        maintenance = User.objects.create_user(username="maint_red", role=User.Role.MAINTENANCE)
        client.force_login(maintenance)
        res = client.get(reverse("users:redirect"))
        assert res.status_code == HTTPStatus.FOUND
        assert res.url == reverse("users:maintenance_dashboard")

    def test_admin_redirect(self, client):
        admin = User.objects.create_superuser(username="admin_red", role=User.Role.ADMIN)
        client.force_login(admin)
        res = client.get(reverse("users:redirect"))
        assert res.status_code == HTTPStatus.FOUND
        assert res.url == reverse("users:admin_dashboard")



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
    def test_login_valid_credentials_with_username(self, client, user: User):
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
        redirect_url = reverse("users:redirect")
        assert response.url == redirect_url
        assert "_auth_user_id" in client.session

    def test_login_valid_credentials_with_email(self, client, user: User):
        user.set_password("CorrectP@ssword123!")
        user.save()

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.email,
                "password": "CorrectP@ssword123!",
            },
        )
        assert response.status_code == HTTPStatus.FOUND
        redirect_url = reverse("users:redirect")
        assert response.url == redirect_url
        assert "_auth_user_id" in client.session


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


