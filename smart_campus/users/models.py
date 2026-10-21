import hashlib
import hmac
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for Smart Campus.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    class Role(models.TextChoices):
        STUDENT = "STUDENT", _("Student")
        MAINTENANCE = "MAINTENANCE", _("Maintenance Staff")
        ADMIN = "ADMIN", _("Administrator")

    class Specialization(models.TextChoices):
        ELECTRICAL = "Electrical", _("Electrical")
        PLUMBING = "Plumbing", _("Plumbing")
        FURNITURE = "Furniture", _("Furniture")
        CLEANLINESS = "Cleanliness", _("Cleanliness")
        IT_NETWORK = "IT / Network", _("IT / Network")
        OTHER = "Other", _("Other")

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
    is_available = models.BooleanField(
        _("Available for Assignment"),
        default=True,
        help_text=_("Designates whether maintenance staff is available for new assignments."),
    )
    specialization = models.CharField(
        _("Specialization"),
        max_length=50,
        choices=Specialization.choices,
        default=Specialization.OTHER,
        blank=True,
        help_text=_("Maintenance specialization used for specialization-first staff assignment."),
    )

    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    @property
    def is_student(self) -> bool:
        """Check if user is a student."""
        return self.role == self.Role.STUDENT

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


class PasswordResetCode(models.Model):
    """Short-lived, single-use code issued by an administrator for password resets."""

    CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    CODE_LENGTH = 8
    VALIDITY_MINUTES = 15

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
    )
    code_hash = models.CharField(_("Code Hash"), max_length=64)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    expires_at = models.DateTimeField(_("Expires At"))
    used_at = models.DateTimeField(_("Used At"), null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reset code for {self.user.username}"

    @staticmethod
    def hash_code(code: str) -> str:
        return hashlib.sha256(code.strip().upper().encode()).hexdigest()

    @classmethod
    def issue_for(cls, user: "User") -> tuple["PasswordResetCode", str]:
        """Invalidate older codes, create a new one, and return (record, plaintext)."""
        code = "".join(secrets.choice(cls.CODE_ALPHABET) for _ in range(cls.CODE_LENGTH))
        cls.objects.filter(user=user, used_at__isnull=True).update(
            used_at=timezone.now()
        )
        record = cls.objects.create(
            user=user,
            code_hash=cls.hash_code(code),
            expires_at=timezone.now() + timedelta(minutes=cls.VALIDITY_MINUTES),
        )
        return record, code

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return self.used_at is None and not self.is_expired

    def matches(self, code: str) -> bool:
        return hmac.compare_digest(self.code_hash, self.hash_code(code))

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


