from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for Smart Campus.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", _("Student")
        FACULTY = "FACULTY", _("Faculty / Teacher")
        MAINTENANCE = "MAINTENANCE", _("Maintenance Staff")
        ADMIN = "ADMIN", _("Administrator")

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text=_("Designates the campus role and authorization level of the user."),
    )
    phone_number = models.CharField(_("Phone Number"), blank=True, max_length=30)
    department = models.CharField(_("Department"), blank=True, max_length=100)
    campus_id = models.CharField(
        _("Campus / Roll / Employee ID"),
        blank=True,
        max_length=50,
        help_text=_("Student Roll Number or Faculty/Staff Employee ID."),
    )
    year_or_semester = models.CharField(
        _("Year / Semester"),
        blank=True,
        max_length=50,
        help_text=_("e.g. 3rd Year / Semester 5 (for students)."),
    )

    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    @property
    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role == self.Role.STUDENT

    @property
    def is_faculty(self) -> bool:
        """Check if user is faculty / teacher."""
        return self.role == self.Role.FACULTY

    @property
    def is_maintenance_staff(self) -> bool:
        """Check if user is a maintenance staff member or has Django staff status."""
        return self.role == self.Role.MAINTENANCE or self.is_staff

    @property
    def is_staff_member(self) -> bool:
        """Alias for is_maintenance_staff."""
        return self.is_maintenance_staff

    @property
    def is_admin_user(self) -> bool:
        """Check if user is campus admin or Django superuser."""
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def can_manage_campus_operations(self) -> bool:
        """Check if user has elevated permissions to manage campus assets, complaints, or inventory."""
        return self.is_maintenance_staff or self.is_admin_user

    def __str__(self) -> str:
        return self.name or self.username

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

