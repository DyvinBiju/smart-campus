from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class InventoryCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Inventory categories"

    def __str__(self):
        return self.name


class StorageLocation(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="e.g. STORE-001")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Storage Location"
        verbose_name_plural = "Storage Locations"

    def __str__(self):
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name

    @property
    def item_count(self):
        return self.items.count()


class InventoryItem(models.Model):
    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items",
    )
    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    minimum_quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
    )
    unit = models.CharField(max_length=50, default="pieces")
    location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items",
        help_text="Official inventory storage location",
    )
    storage_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Storage room or warehouse location (e.g. Central Store, Room 105)",
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.minimum_quantity:
            return "Low Stock"
        return "In Stock"

    def save(self, *args, **kwargs):
        if self.location:
            self.storage_location = self.location.name
        elif self.storage_location:
            matched = StorageLocation.objects.filter(name__iexact=self.storage_location.strip()).first()
            if matched:
                self.location = matched
                self.storage_location = matched.name
        super().save(*args, **kwargs)


class StockTransaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ("RECEIVE", "Stock Received / Added"),
        ("ISSUE", "Stock Issued / Consumed"),
        ("ADJUSTMENT", "Stock Adjustment"),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default="RECEIVE",
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of units for this transaction",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_transactions",
        help_text="Optional asset associated with this inventory usage",
    )
    notes = models.TextField(
        blank=True,
        help_text="Reason for issue, invoice number, or maintenance notes",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Stock Transaction"
        verbose_name_plural = "Stock Transactions"

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.quantity} {self.item.unit} of {self.item.name}"

    def clean(self):
        super().clean()
        if self.transaction_type == "ISSUE" and self.item_id:
            if self.item.quantity < self.quantity:
                raise ValidationError(
                    f"Insufficient stock for '{self.item.name}'. Available: {self.item.quantity} {self.item.unit}, requested issue: {self.quantity} {self.item.unit}."
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            self.full_clean()
            if self.transaction_type == "RECEIVE":
                self.item.quantity += self.quantity
            elif self.transaction_type == "ISSUE":
                self.item.quantity -= self.quantity
            elif self.transaction_type == "ADJUSTMENT":
                self.item.quantity = self.quantity
            self.item.save()
        super().save(*args, **kwargs)