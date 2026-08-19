from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Complaint(models.Model):
    class Category(models.TextChoices):
        ELECTRICAL = "Electrical", _("Electrical")
        PLUMBING = "Plumbing", _("Plumbing")
        FURNITURE = "Furniture", _("Furniture")
        CLEANLINESS = "Cleanliness", _("Cleanliness")
        IT_NETWORK = "IT / Network", _("IT / Network")
        OTHER = "Other", _("Other")

    class Priority(models.TextChoices):
        LOW = "Low", _("Low")
        MEDIUM = "Medium", _("Medium")
        HIGH = "High", _("High")

    class Status(models.TextChoices):
        SUBMITTED = "Submitted", _("Submitted")
        UNDER_REVIEW = "Under Review", _("Under Review")
        IN_PROGRESS = "In Progress", _("In Progress")
        RESOLVED = "Resolved", _("Resolved")

    complaint_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name=_("Complaint ID"),
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_("Title"),
    )
    description = models.TextField(
        verbose_name=_("Description"),
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name=_("Category"),
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_("Location"),
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name=_("Priority"),
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name=_("Status"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        verbose_name=_("Submitted By"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created Date"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated Date"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Complaint")
        verbose_name_plural = _("Complaints")

    def __str__(self):
        return f"{self.complaint_id} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.complaint_id:
            last_complaint = (
                Complaint.objects.filter(complaint_id__startswith="CMP-")
                .order_by("-id")
                .first()
            )
            if last_complaint and last_complaint.complaint_id:
                try:
                    num = int(last_complaint.complaint_id.replace("CMP-", "")) + 1
                except ValueError:
                    num = Complaint.objects.count() + 1
            else:
                num = 1
            self.complaint_id = f"CMP-{num:04d}"
        super().save(*args, **kwargs)
