from __future__ import annotations

from django.urls import resolve
from django.urls import reverse


def test_student_signup_url():
    assert reverse("users:student_signup") == "/users/signup/student/"
    assert resolve("/users/signup/student/").view_name == "users:student_signup"




