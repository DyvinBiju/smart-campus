from django.db import models
from django.urls import reverse


class Location(models.Model):
    """
    Centralized model representing physical campus locations in a hierarchy:
    Campus -> Block/Building -> Department/Area -> Room/Hall/Lab/Office
    """

    LOCATION_TYPE_CHOICES = [
        ("CAMPUS", "Campus"),
        ("BLOCK", "Block / Building"),
        ("DEPARTMENT", "Department / Area"),
        ("CLASSROOM", "Classroom"),
        ("COMPUTER_LAB", "Computer Lab"),
        ("LABORATORY", "Laboratory"),
        ("HALL", "Seminar / Conference Hall"),
        ("OFFICE", "Office"),
        ("LIBRARY", "Library"),
        ("SERVER_ROOM", "Server Room"),
        ("STORE_ROOM", "Store Room"),
        ("MAINTENANCE_ROOM", "Maintenance Room"),
        ("STAFF_ROOM", "Staff Room"),
        ("OTHER", "Other Area"),
    ]

    name = models.CharField(
        max_length=150,
        help_text="Name of the campus location (e.g. Computer Science Block, Computer Lab 1)",
    )
    location_type = models.CharField(
        max_length=50,
        choices=LOCATION_TYPE_CHOICES,
        default="CLASSROOM",
        help_text="Category of campus location",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent building or block for hierarchical sorting",
    )
    description = models.TextField(
        blank=True,
        help_text="Additional notes or directions for this location",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this location is active and available for assignment.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Campus Location"
        verbose_name_plural = "Campus Locations"

    def get_full_path(self):
        """Returns string representation of location hierarchy (e.g. 'Computer Science Block → Computer Lab 1')."""
        if self.parent:
            return f"{self.parent.get_full_path()} → {self.name}"
        return self.name

    def __str__(self):
        return self.get_full_path()

    @property
    def asset_count(self):
        return self.assets.count()

    @property
    def complaint_count(self):
        return self.complaints.count()

    def get_absolute_url(self):
        return reverse("assets:location_detail", kwargs={"pk": self.pk})


class Asset(models.Model):
    """
    Asset Model represents physical items/resources owned by the campus.
    Examples: Computers, Projectors, Lab Microscopes, Classroom Desks.
    """

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("IN_STOCK", "In Stock"),
        ("UNDER_MAINTENANCE", "Under Maintenance"),
        ("DAMAGED", "Damaged"),
        ("RETIRED", "Retired"),
    ]

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
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
        help_text="Centralized campus location where the asset is registered",
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
        """Auto-generate asset code if not provided & sync building/room from location."""
        if self.location:
            if self.location.parent:
                self.building = self.location.parent.name
                self.room = self.location.name
            else:
                self.building = self.location.name
                if not self.room:
                    self.room = ""
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
