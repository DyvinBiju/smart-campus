from __future__ import annotations

from typing import TYPE_CHECKING

from smart_campus.users.models import User

if TYPE_CHECKING:
    pass


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


def test_user_str(user: User):
    user.name = "Jane Doe"
    assert str(user) == "Jane Doe"

    user.name = ""
    assert str(user) == user.username


def test_user_default_role():
    new_user = User(username="newstudent", email="student@campus.edu")
    assert new_user.role == User.Role.STUDENT
    assert new_user.is_student is True
    assert new_user.is_faculty is False
    assert new_user.is_staff_member is False
    assert new_user.is_admin_user is False
    assert new_user.can_manage_campus_operations is False


def test_user_roles_and_permissions():
    faculty = User(username="prof_smith", role=User.Role.FACULTY)
    assert faculty.is_faculty is True
    assert faculty.is_student is False
    assert faculty.can_manage_campus_operations is False

    staff = User(username="maintenance_bob", role=User.Role.STAFF)
    assert staff.is_staff_member is True
    assert staff.can_manage_campus_operations is True

    admin = User(username="campus_admin", role=User.Role.ADMIN)
    assert admin.is_admin_user is True
    assert admin.can_manage_campus_operations is True

    django_staff = User(username="dj_staff", is_staff=True)
    assert django_staff.is_staff_member is True
    assert django_staff.can_manage_campus_operations is True

    django_super = User(username="dj_super", is_superuser=True)
    assert django_super.is_admin_user is True
    assert django_super.can_manage_campus_operations is True

