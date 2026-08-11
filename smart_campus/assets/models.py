from django.db import models

from django.db import models


class Asset(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("IN_STOCK", "In Stock"),
        ("UNDER_MAINTENANCE", "Under Maintenance"),
        ("DAMAGED", "Damaged"),
        ("RETIRED", "Retired"),
    ]

    asset_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    building = models.CharField(max_length=100)
    room = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )
    purchase_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.asset_code} - {self.name}"
