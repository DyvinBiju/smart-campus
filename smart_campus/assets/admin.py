from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_code",
        "name",
        "category",
        "building",
        "room",
        "status",
    )

    list_filter = (
        "category",
        "status",
        "building",
    )

    search_fields = (
        "asset_code",
        "name",
        "category",
    )

    ordering = ("asset_code",)