from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from smart_campus.users.models import User
from smart_campus.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from django.test import RequestFactory

pytestmark = pytest.mark.django_db


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
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Account created successfully. Welcome to SmartCampus!" in content
        assert "_auth_user_id" in client.session

        user = User.objects.get(email="alex.student@campus.edu")
        assert user.role == User.Role.STUDENT
        assert user.is_student is True


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
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Account created successfully. Welcome to SmartCampus!" in content
        assert "_auth_user_id" in client.session

        user = User.objects.get(email="grace.hopper@campus.edu")
        assert user.role == User.Role.FACULTY
        assert user.is_faculty is True


class TestRoleRequiredMixin:
    def test_authenticated_allowed_role(self, rf: RequestFactory):
        from django.http import HttpResponse
        from django.views.generic import View

        from smart_campus.users.views import RoleRequiredMixin

        class SampleAuthorizedView(RoleRequiredMixin, View):
            allowed_roles = [User.Role.FACULTY.value]

            def get(self, request):
                return HttpResponse("OK")

        user = UserFactory(role=User.Role.FACULTY)
        request = rf.get("/")
        request.user = user
        response = SampleAuthorizedView.as_view()(request)
        assert response.status_code == HTTPStatus.OK

    def test_authenticated_disallowed_role_raises_permission_denied(self, rf: RequestFactory):
        from django.http import HttpResponse
        from django.views.generic import View

        from smart_campus.users.views import RoleRequiredMixin

        class SampleAuthorizedView(RoleRequiredMixin, View):
            allowed_roles = [User.Role.FACULTY.value]

            def get(self, request):
                return HttpResponse("OK")

        user = UserFactory(role=User.Role.STUDENT)
        request = rf.get("/")
        request.user = user
        with pytest.raises(PermissionDenied):
            SampleAuthorizedView.as_view()(request)


class TestUserAuthenticationFlows:
    def test_login_valid_credentials_with_username(self, client, user: User):
        user.role = User.Role.STUDENT
        user.set_password("CorrectP@ssword123!")
        user.save()

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.username,
                "password": "CorrectP@ssword123!",
            },
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        assert "_auth_user_id" in client.session
        assert f"Welcome back, {user.username}!" in response.content.decode()

    def test_login_valid_credentials_with_email(self, client, user: User):
        user.role = User.Role.STUDENT
        user.set_password("CorrectP@ssword123!")
        user.save()

        login_url = reverse("account_login")
        response = client.post(
            login_url,
            data={
                "login": user.email,
                "password": "CorrectP@ssword123!",
            },
            follow=True,
        )
        assert response.status_code == HTTPStatus.OK
        assert "_auth_user_id" in client.session
        assert f"Welcome back, {user.username}!" in response.content.decode()

    def test_login_redirects_student_to_student_dashboard(self, client):
        student = UserFactory(role=User.Role.STUDENT)
        student.set_password("StudentPass123!")
        student.save()

        response = client.post(
            reverse("account_login"),
            data={"login": student.username, "password": "StudentPass123!"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("dashboard:student")

    def test_login_redirects_admin_to_admin_dashboard(self, client):
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        admin.set_password("AdminPass123!")
        admin.save()

        response = client.post(
            reverse("account_login"),
            data={"login": admin.username, "password": "AdminPass123!"},
        )
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("dashboard:admin")

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
        assert "Invalid username/email or password." in response.content.decode()

    def test_logout(self, client, user: User):
        client.force_login(user)
        logout_url = reverse("account_logout")

        response = client.post(logout_url)
        assert response.status_code == HTTPStatus.FOUND
        assert "_auth_user_id" not in client.session


class TestLandingPageAndAuthTemplates:
    def test_landing_page_logged_out_navigation(self, client):
        response = client.get(reverse("home"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert reverse("account_login") in content
        assert reverse("users:student_signup") in content
        assert reverse("users:faculty_signup") in content
        assert "Raise Complaint" in content
        assert "My Complaints" in content

    def test_landing_page_logged_in_navigation(self, client, user: User):
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert reverse("account_logout") in content
        # User name is displayed in the navbar
        assert user.name or user.username in content

    def test_navbar_visibility_per_user_role(self, client):
        def get_main_menu(response):
            content = response.content.decode()
            start = content.find('<nav id="main-menu">')
            end = content.find('</nav>', start)
            return content[start:end]

        dash_link = f'href="{reverse("dashboard:index")}"'
        raise_complaint_link = f'href="{reverse("complaints:create")}"'
        assets_link = f'href="{reverse("assets:asset_list")}"'
        inventory_link = f'href="{reverse("inventory:list")}"'

        # 1. Logged-out user: Home, Raise Complaint, Complaints, About (No Dashboard, Assets, Inventory)
        resp = client.get(reverse("home"))
        menu = get_main_menu(resp)
        assert dash_link not in menu
        assert raise_complaint_link in menu
        assert assets_link not in menu
        assert inventory_link not in menu

        # 2. Student user: Home, Dashboard, Raise Complaint, Complaints, About (No Assets, Inventory)
        student = UserFactory(role=User.Role.STUDENT)
        client.force_login(student)
        resp = client.get(reverse("home"))
        menu = get_main_menu(resp)
        assert dash_link in menu
        assert raise_complaint_link in menu
        assert assets_link not in menu
        assert inventory_link not in menu

        # 3. Admin user: Home, Dashboard, Complaints, About (No Raise Complaint, Assets, Inventory)
        admin = UserFactory(role=User.Role.ADMIN, is_staff=True)
        client.force_login(admin)
        resp = client.get(reverse("home"))
        menu = get_main_menu(resp)
        assert dash_link in menu
        assert raise_complaint_link not in menu
        assert assets_link not in menu
        assert inventory_link not in menu

    def test_login_page_renders_bottom_signup_links(self, client):
        response = client.get(reverse("account_login"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Don&#x27;t have an account?" in content or "Don't have an account?" in content
        assert reverse("users:student_signup") in content
        assert reverse("users:faculty_signup") in content

    def test_account_signup_renders_role_selection(self, client):
        response = client.get(reverse("account_signup"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert reverse("users:student_signup") in content
        assert reverse("users:faculty_signup") in content
        assert reverse("account_login") in content

    def test_student_signup_page_bottom_signin_link(self, client):
        response = client.get(reverse("users:student_signup"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Already have an account?" in content
        assert reverse("account_login") in content

    def test_faculty_signup_page_bottom_signin_link(self, client):
        response = client.get(reverse("users:faculty_signup"))
        assert response.status_code == HTTPStatus.OK
        content = response.content.decode()
        assert "Already have an account?" in content
        assert reverse("account_login") in content
