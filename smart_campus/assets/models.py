from django.db import models
from django.urls import reverse


class Asset(models.Model):
    """
    Asset Model represents physical items/resources owned by the campus.
    Examples: Computers, Projectors, Lab Microscopes, Classroom Desks.
    """

    # Status choices to track the operational state of an asset
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("IN_STOCK", "In Stock"),
        ("UNDER_MAINTENANCE", "Under Maintenance"),
        ("DAMAGED", "Damaged"),
        ("RETIRED", "Retired"),
    ]

    # Predefined category choices for organized sorting
    CATEGORY_CHOICES = [
        ("IT & Computers", "IT & Computers"),
        ("Lab Equipment", "Lab Equipment"),
        ("Classroom & Furniture", "Classroom & Furniture"),
        ("Audio / Visual", "Audio / Visual"),
        ("Electrical & Utilities", "Electrical & Utilities"),
        ("Other", "Other"),
    ]

    asset_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        help_text="Unique asset identifier (e.g. AST-0001). Leave blank to auto-generate.",
    )
    name = models.CharField(
        max_length=100,
        help_text="Name or model of the asset (e.g. Dell Desktop PC)",
    )
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default="IT & Computers",
        help_text="Department or category of asset",
    )
    building = models.CharField(
        max_length=100,
        help_text="Campus building where the asset is located (e.g. Main Block)",
    )
    room = models.CharField(
        max_length=50,
        blank=True,
        help_text="Room or Lab number (e.g. Room 204, Lab 3B)",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="ACTIVE",
        help_text="Current condition and availability status",
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this asset was acquired",
    )
    description = models.TextField(
        blank=True,
        help_text="Additional specifications or notes about the asset",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Auto-generate asset code if not provided."""
        if not self.asset_code:
            count = Asset.objects.count() + 1
            code = f"AST-{count:04d}"
            while Asset.objects.filter(asset_code=code).exists():
                count += 1
                code = f"AST-{count:04d}"
            self.asset_code = code
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Asset"
        verbose_name_plural = "Assets"

    def __str__(self):
        return f"{self.asset_code} - {self.name}"

    def get_absolute_url(self):
        """Returns the detail page URL for this asset."""
        return reverse("assets:asset_detail", kwargs={"pk": self.pk})

    @property
    def status_badge_class(self):
        """Helper to return appropriate Bootstrap 5 badge color classes."""
        badge_map = {
            "ACTIVE": "bg-success",
            "IN_STOCK": "bg-info text-dark",
            "UNDER_MAINTENANCE": "bg-warning text-dark",
            "DAMAGED": "bg-danger",
            "RETIRED": "bg-secondary",
        }
        return badge_map.get(self.status, "bg-secondary")
