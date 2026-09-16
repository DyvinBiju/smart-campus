from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class Activity(models.Model):
    ACTIVITY_TYPES = [
        ('COMPLAINT', 'Complaint'),
        ('ASSET', 'Asset'),
        ('INVENTORY', 'Inventory'),
        ('MAINTENANCE', 'Maintenance'),
        ('USER', 'User'),
        ('SYSTEM', 'System'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dashboard_activities'
    )
    user_name = models.CharField(max_length=255, blank=True) # Fallback / cached user name
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES, default='SYSTEM')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=50, blank=True) # e.g. "Pending", "Resolved", "Active", "Low Stock"
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name_plural = "Activities"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.activity_type} - {self.title}"


class Notification(models.Model):
    """
    User-specific notification for the maintenance workflow.
    Created by the backend when assignment or resource-request decisions occur.
    Recipient scoping keeps staff notifications private from students and peers.
    """

    class NotificationType(models.TextChoices):
        ASSIGNMENT = "ASSIGNMENT", _("New assignment")
        REASSIGNMENT = "REASSIGNMENT", _("Reassignment")
        REQUEST_APPROVED = "REQUEST_APPROVED", _("Request approved")
        REQUEST_REJECTED = "REQUEST_REJECTED", _("Request rejected")
        REQUEST_MORE_INFO = "REQUEST_MORE_INFO", _("More info requested")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="maintenance_notifications",
        verbose_name=_("Recipient"),
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.ASSIGNMENT,
        verbose_name=_("Type"),
    )
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    message = models.TextField(blank=True, verbose_name=_("Message"))
    link = models.CharField(max_length=500, blank=True, verbose_name=_("Link"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created Date"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient} - {self.title}"

    @classmethod
    def notify(cls, recipient, notification_type, title, message="", link=""):
        """Backend helper to create a user-specific notification."""
        if recipient is None:
            return None
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
        )
