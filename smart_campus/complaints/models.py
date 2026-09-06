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
        ASSIGNED = "Assigned", _("Assigned")
        UNDER_INSPECTION = "Under Inspection", _("Under Inspection")
        ACTION_REQUIRED = "Action Required", _("Action Required")
        IN_PROGRESS = "In Progress", _("In Progress")
        RESOLVED = "Resolved", _("Resolved")
        CLOSED = "Closed", _("Closed")

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
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
        verbose_name=_("Affected Asset"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
        verbose_name=_("Assigned To"),
    )
    assigned_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Assigned Date"),
    )
    inspection_notes = models.TextField(
        blank=True,
        verbose_name=_("Inspection Notes"),
    )
    resolution_notes = models.TextField(
        blank=True,
        verbose_name=_("Resolution Notes"),
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Resolved Date"),
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

    def log_history(self, status, changed_by=None, comment=""):
        """Utility method to log a status transition into history."""
        ComplaintHistory.objects.create(
            complaint=self,
            status=status,
            changed_by=changed_by,
            comment=comment,
        )


class ComplaintHistory(models.Model):
    """
    Tracks every status transition and work update throughout the complaint lifecycle.
    """

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="history",
        verbose_name=_("Complaint"),
    )
    status = models.CharField(
        max_length=30,
        verbose_name=_("Status"),
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By"),
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_("Notes / Comment"),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Timestamp"),
    )

    class Meta:
        ordering = ["timestamp"]
        verbose_name = _("Complaint History")
        verbose_name_plural = _("Complaint Histories")

    def __str__(self):
        return f"{self.complaint.complaint_id} - {self.status} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class MaintenanceRequest(models.Model):
    """
    Represents requests by Maintenance Staff when an inventory item is unavailable
    or when an asset requires administrative action (repair, replacement, retirement).
    """

    class RequestType(models.TextChoices):
        UNAVAILABLE_RESOURCE = "UNAVAILABLE_RESOURCE", _("Unavailable Inventory Resource Required")
        PURCHASE = "PURCHASE", _("Purchase New Item / Resource")
        ASSET_REPAIR = "ASSET_REPAIR", _("Asset Repair Required")
        ASSET_REPLACE = "ASSET_REPLACE", _("Asset Replacement Recommended")
        ASSET_RETIRE = "ASSET_RETIRE", _("Asset Retirement Recommended")
        OTHER = "OTHER", _("Other Administrative Action Required")

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Admin Decision")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        MORE_INFO = "MORE_INFO", _("More Info Requested")

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="maintenance_requests",
        verbose_name=_("Complaint"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests_made",
        verbose_name=_("Requested By"),
    )
    request_type = models.CharField(
        max_length=30,
        choices=RequestType.choices,
        default=RequestType.UNAVAILABLE_RESOURCE,
        verbose_name=_("Request Type"),
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenance_requests",
        verbose_name=_("Requested Inventory Item"),
    )
    quantity_requested = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity Requested"),
    )
    reason = models.TextField(
        verbose_name=_("Reason / Findings"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Status"),
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name=_("Administrator Notes"),
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_maintenance_requests",
        verbose_name=_("Decided By"),
    )
    decided_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Decided Date"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created Date"),
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Maintenance Request")
        verbose_name_plural = _("Maintenance Requests")

    def __str__(self):
        return f"{self.get_request_type_display()} for {self.complaint.complaint_id} ({self.status})"


class ComplaintResource(models.Model):
    """
    Junction model tracking inventory items consumed to resolve a complaint.
    """

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="resources_used",
        verbose_name=_("Complaint"),
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="complaint_usages",
        verbose_name=_("Inventory Item"),
    )
    quantity_used = models.PositiveIntegerField(
        default=1,
        verbose_name=_("Quantity Used"),
    )
    used_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date Used"),
    )

    class Meta:
        verbose_name = _("Complaint Resource")
        verbose_name_plural = _("Complaint Resources")
        ordering = ["-used_at"]

    def __str__(self):
        return f"{self.quantity_used} x {self.inventory_item.name} ({self.complaint.complaint_id})"

