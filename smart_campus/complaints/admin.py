from django.contrib import admin
from .models import Complaint, ComplaintHistory, ComplaintResource, MaintenanceRequest


class ComplaintHistoryInline(admin.TabularInline):
    model = ComplaintHistory
    extra = 0
    readonly_fields = ("status", "changed_by", "comment", "timestamp")


class ComplaintResourceInline(admin.TabularInline):
    model = ComplaintResource
    extra = 0
    raw_id_fields = ("inventory_item",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "complaint_id",
        "title",
        "category",
        "priority",
        "status",
        "assigned_to",
        "created_at",
    )
    list_filter = ("status", "priority", "category", "created_at")
    search_fields = ("complaint_id", "title", "description", "location")
    readonly_fields = ("complaint_id", "created_at", "updated_at")
    inlines = [ComplaintHistoryInline, ComplaintResourceInline]


@admin.register(ComplaintHistory)
class ComplaintHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "status", "changed_by", "timestamp")
    list_filter = ("status", "timestamp")
    search_fields = ("complaint__complaint_id", "comment")


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ("complaint", "request_type", "status", "requested_by", "created_at")
    list_filter = ("request_type", "status", "created_at")
    search_fields = ("complaint__complaint_id", "reason", "admin_notes")


@admin.register(ComplaintResource)
class ComplaintResourceAdmin(admin.ModelAdmin):
    list_display = ("complaint", "inventory_item", "quantity_used", "used_at")
    search_fields = ("complaint__complaint_id", "inventory_item__name")

