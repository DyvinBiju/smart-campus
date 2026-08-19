from django.contrib import admin
from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    """
    Admin configuration for managing campus assets.
    """

    list_display = (
        "asset_code",
        "name",
        "category",
        "building",
        "room",
        "status",
        "purchase_date",
        "created_at",
    )
    list_filter = (
        "status",
        "category",
        "building",
    )
    search_fields = (
        "asset_code",
        "name",
        "building",
        "room",
        "description",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"