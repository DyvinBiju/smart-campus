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
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def stock_status(self):
        if self.quantity == 0:
            return "Out of Stock"
        elif self.quantity <= self.minimum_quantity:
            return "Low Stock"
        return "Available"