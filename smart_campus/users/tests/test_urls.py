from __future__ import annotations

from django.urls import resolve
from django.urls import reverse


def test_student_signup_url():
    assert reverse("users:student_signup") == "/users/signup/student/"
    assert resolve("/users/signup/student/").view_name == "users:student_signup"


def test_faculty_signup_url():
    assert reverse("users:faculty_signup") == "/users/signup/faculty/"
    assert resolve("/users/signup/faculty/").view_name == "users:faculty_signup"




