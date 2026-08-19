from django.contrib import admin
from .models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "complaint_id",
        "title",
        "category",
        "priority",
        "status",
        "created_at",
    )
    list_filter = ("status", "priority", "category", "created_at")
    search_fields = ("complaint_id", "title", "description", "location")
    readonly_fields = ("complaint_id", "created_at", "updated_at")
