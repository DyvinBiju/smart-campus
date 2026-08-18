from __future__ import annotations

from typing import TYPE_CHECKING

from django.urls import resolve
from django.urls import reverse

if TYPE_CHECKING:
    from smart_campus.users.models import User


def test_detail(user: User):
    assert (
        reverse("users:detail", kwargs={"username": user.username})
        == f"/users/{user.username}/"
    )
    assert resolve(f"/users/{user.username}/").view_name == "users:detail"


def test_update():
    assert reverse("users:update") == "/users/~update/"
    assert resolve("/users/~update/").view_name == "users:update"


def test_redirect():
    assert reverse("users:redirect") == "/users/~redirect/"
    assert resolve("/users/~redirect/").view_name == "users:redirect"


def test_student_signup_url():
    assert reverse("users:student_signup") == "/users/signup/student/"
    assert resolve("/users/signup/student/").view_name == "users:student_signup"


def test_faculty_signup_url():
    assert reverse("users:faculty_signup") == "/users/signup/faculty/"
    assert resolve("/users/signup/faculty/").view_name == "users:faculty_signup"


def test_student_dashboard_url():
    assert reverse("users:student_dashboard") == "/users/dashboard/student/"
    assert resolve("/users/dashboard/student/").view_name == "users:student_dashboard"


def test_faculty_dashboard_url():
    assert reverse("users:faculty_dashboard") == "/users/dashboard/faculty/"
    assert resolve("/users/dashboard/faculty/").view_name == "users:faculty_dashboard"


def test_maintenance_dashboard_url():
    assert reverse("users:maintenance_dashboard") == "/users/dashboard/maintenance/"
    assert resolve("/users/dashboard/maintenance/").view_name == "users:maintenance_dashboard"


def test_admin_dashboard_url():
    assert reverse("users:admin_dashboard") == "/users/dashboard/admin/"
    assert resolve("/users/dashboard/admin/").view_name == "users:admin_dashboard"

