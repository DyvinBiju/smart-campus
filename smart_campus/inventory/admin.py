from django.contrib import admin
from .models import InventoryCategory, InventoryItem, StockTransaction


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity", "unit", "minimum_quantity", "storage_location", "stock_status", "updated_at")
    list_filter = ("category", "storage_location")
    search_fields = ("name", "description", "storage_location")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "item", "transaction_type", "quantity", "asset", "created_by")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("item__name", "asset__asset_code", "asset__name", "notes")

