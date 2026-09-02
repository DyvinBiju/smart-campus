from django.db import models
from django.conf import settings
from django.utils import timezone

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
