import csv
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import TemplateView, View

from smart_campus.assets.models import Asset
from smart_campus.complaints.models import Complaint, ComplaintHistory, MaintenanceRequest
from smart_campus.inventory.models import InventoryItem, StockTransaction
from smart_campus.users.models import User
from .models import Activity, Notification
from .helpers import (
    get_modules_info,
    get_assets_metrics,
    get_inventory_metrics,
    get_complaints_metrics,
    get_maintenance_staff_metrics,
    get_realtime_audit_activities,
    is_model_available,
    log_activity,
)

def get_current_role_and_user(request):
    """
    Determines user staff/admin status and returns (is_staff, user).
    """
    user = request.user
    if user.is_authenticated:
        is_staff = user.is_staff or user.is_superuser or user.is_admin_user or user.is_maintenance_staff
    else:
        user = AnonymousUser()
        is_staff = False
            
    return is_staff, user

class DashboardIndexView(LoginRequiredMixin, View):
    """
    Landing redirector. Directs Admins to Admin Operations dashboard, Maintenance Staff
    to Maintenance Staff dashboard, and regular student users to the Student portal.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_admin_user:
            return redirect("dashboard:admin")
        elif user.is_maintenance_staff:
            return redirect("dashboard:maintenance")
        return redirect("dashboard:student")


class MaintenanceDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dedicated operational workspace for Maintenance Staff.
    Provides personal assigned work, priority items, inventory/asset quick views,
    maintenance request status, and recent activity logs.
    """
    template_name = "dashboard/maintenance_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_maintenance_staff or request.user.is_admin_user or request.user.is_staff):
            return redirect("dashboard:student")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        modules = get_modules_info()
        staff_metrics = get_maintenance_staff_metrics(user)
        assets_stats = get_assets_metrics()
        inventory_stats = get_inventory_metrics()

        ComplaintModel = is_model_available("complaints", "Complaint")
        status_filter = self.request.GET.get("status", "").strip()

        assigned_complaints = ComplaintModel.objects.select_related("user", "asset").filter(assigned_to=user) if ComplaintModel else []
        if status_filter and assigned_complaints:
            assigned_complaints = assigned_complaints.filter(status=status_filter)

        needs_attention = (
            ComplaintModel.objects.select_related("user", "asset")
            .filter(assigned_to=user)
            .filter(models.Q(priority="High") | models.Q(status__in=["Submitted", "Under Review", "Assigned", "Action Required"]))[:5]
            if ComplaintModel
            else []
        )

        MaintReqModel = is_model_available("complaints", "MaintenanceRequest")
        my_requests = (
            MaintReqModel.objects.select_related("complaint", "inventory_item")
            .filter(requested_by=user)[:5]
            if MaintReqModel
            else []
        )

        HistoryModel = is_model_available("complaints", "ComplaintHistory")
        recent_activity = (
            HistoryModel.objects.select_related("complaint", "changed_by")
            .filter(changed_by=user)
            .order_by("-timestamp")[:8]
            if HistoryModel
            else []
        )

        context.update({
            "modules": modules,
            "staff_metrics": staff_metrics,
            "assets_stats": assets_stats,
            "inventory_stats": inventory_stats,
            "assigned_complaints": assigned_complaints,
            "needs_attention": needs_attention,
            "my_requests": my_requests,
            "recent_activity": recent_activity,
            "notifications": Notification.objects.filter(recipient=user)[:10],
            "unread_notifications_count": Notification.objects.filter(
                recipient=user, is_read=False
            ).count(),
            "status_filter": status_filter,
            "statuses": ComplaintModel.Status.choices if ComplaintModel else [],
            "preview_mode": False,
            "current_role": "maintenance",
        })
        return context


class StudentDashboardView(LoginRequiredMixin, TemplateView):
    """
    Portal for regular campus users (Students / non-admin staff).
    Displays personal stats, raised complaints summaries, and recent activity updates.
    """
    template_name = "dashboard/student_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_complaints = Complaint.objects.filter(user=user)
        recent_complaints = user_complaints.select_related("asset", "location_record").order_by(
            "-updated_at", "-created_at"
        )[:8]
        public_status_labels = {
            Complaint.Status.SUBMITTED: "Complaint Submitted",
            Complaint.Status.UNDER_REVIEW: "Under Review",
            Complaint.Status.ASSIGNED: "Assigned to Maintenance Staff",
            Complaint.Status.UNDER_INSPECTION: "Under Inspection",
            Complaint.Status.IN_PROGRESS: "In Progress",
            Complaint.Status.ACTION_REQUIRED: "Awaiting Resources",
            Complaint.Status.RESOLVED: "Resolved",
            Complaint.Status.CLOSED: "Closed",
        }
        recent_updates = [
            {
                "complaint": update.complaint,
                "timestamp": update.timestamp,
                "title": public_status_labels[update.status],
                "status": public_status_labels[update.status],
                "description": "Your complaint progress has been updated.",
            }
            for update in ComplaintHistory.objects.filter(
                complaint__user=user,
                status__in=public_status_labels,
            ).select_related("complaint").order_by("-timestamp")[:5]
        ]

        complaints_stats = {
            "total": user_complaints.count(),
            "submitted": user_complaints.filter(status=Complaint.Status.SUBMITTED).count(),
            "under_review": user_complaints.filter(status=Complaint.Status.UNDER_REVIEW).count(),
            "in_progress": user_complaints.filter(
                status__in=[
                    Complaint.Status.ASSIGNED,
                    Complaint.Status.UNDER_INSPECTION,
                    Complaint.Status.IN_PROGRESS,
                    Complaint.Status.ACTION_REQUIRED,
                ]
            ).count(),
            "resolved": user_complaints.filter(
                status__in=[Complaint.Status.RESOLVED, Complaint.Status.CLOSED]
            ).count(),
        }
        role_label = user.get_role_display()

        context.update({
            "complaints_stats": complaints_stats,
            "recent_complaints": recent_complaints,
            "user_stats": {
                "date_joined": user.date_joined,
                "email": user.email,
                "name": user.name or user.username,
                "username": user.username,
                "role": role_label,
                "campus_id": user.campus_id,
                "department": user.department,
                "year_or_semester": user.year_or_semester,
            },
            "recent_updates": recent_updates,
            "role_label": role_label,
            "preview_mode": False,
            "current_role": "student"
        })
        return context

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """
    Operations dashboard for Admin/Staff. Provides campus-wide metrics,
    charts, interactive filters (date range, category, status), and module health status.
    """
    template_name = "dashboard/admin_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin_user or request.user.is_superuser):
            return redirect("dashboard:student")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_staff, user = get_current_role_and_user(self.request)
        
        # Retrieve filter parameters
        date_filter = self.request.GET.get("date_range", "all")
        category_filter = self.request.GET.get("category", "all")
        status_filter = self.request.GET.get("status", "all")
        
        # Calculate date range limits
        today_date = now()
        start_date = None
        if date_filter == "today":
            start_date = today_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "7_days":
            start_date = today_date - timedelta(days=7)
        elif date_filter == "30_days":
            start_date = today_date - timedelta(days=30)
            
        # Compile filters dict to pass to metrics helpers
        filters = {
            "start_date": start_date,
            "category": category_filter if category_filter != "all" else None,
            "status": status_filter if status_filter != "all" else None,
        }
        
        # Retrieve stats from Activity model
        modules = get_modules_info()
        assets_stats = get_assets_metrics(filters=filters)
        inventory_stats = get_inventory_metrics(filters=filters)
        complaints_stats = get_complaints_metrics(filters=filters)
        
        # User Stats
        total_users = User.objects.count()
        staff_users = User.objects.filter(models.Q(is_staff=True) | models.Q(role__in=[User.Role.ADMIN, User.Role.MAINTENANCE])).count()
        student_users = total_users - staff_users
        
        # Query real-time system audit activity feed across all active models
        recent_activities = get_realtime_audit_activities(
            start_date=start_date,
            category_filter=category_filter,
            status_filter=status_filter,
            limit=12,
        )
        
        ComplaintModel = is_model_available("complaints", "Complaint")
        AssetModel = is_model_available("assets", "Asset")
        HistoryModel = is_model_available("complaints", "ComplaintHistory")
        StockTxModel = is_model_available("inventory", "StockTransaction")

        # Calculate trend chart values (last 7 days counts from real DB)
        trend_dates = []
        complaints_trend = []
        assets_trend = []
        for i in range(6, -1, -1):
            d = today_date - timedelta(days=i)
            trend_dates.append(d.strftime("%b %d"))
            
            c_count = 0
            if ComplaintModel:
                c_count += ComplaintModel.objects.filter(created_at__date=d.date()).count()
            if HistoryModel:
                c_count += HistoryModel.objects.filter(timestamp__date=d.date()).count()
            if not ComplaintModel and not HistoryModel:
                c_count = Activity.objects.filter(
                    activity_type__in=['COMPLAINT', 'MAINTENANCE'],
                    timestamp__date=d.date()
                ).count()

            a_count = 0
            if AssetModel:
                a_count += AssetModel.objects.filter(models.Q(created_at__date=d.date()) | models.Q(updated_at__date=d.date())).count()
            if StockTxModel:
                a_count += StockTxModel.objects.filter(created_at__date=d.date()).count()
            if not AssetModel and not StockTxModel:
                a_count = Activity.objects.filter(
                    activity_type='ASSET',
                    timestamp__date=d.date()
                ).count()
            
            complaints_trend.append(c_count)
            assets_trend.append(a_count)
            
        context.update({
            "modules": modules,
            "assets_stats": assets_stats,
            "inventory_stats": inventory_stats,
            "complaints_stats": complaints_stats,
            "total_users": total_users,
            "staff_users": staff_users,
            "student_users": student_users,
            "filters": {
                "date_range": date_filter,
                "category": category_filter,
                "status": status_filter,
            },
            "trends": {
                "labels": trend_dates,
                "complaints": complaints_trend,
                "assets": assets_trend,
            },
            "recent_activities": recent_activities,
            "preview_mode": False,
            "current_role": "admin"
        })
        return context

class ReportExportView(LoginRequiredMixin, View):
    """
    Generates operational reports displaying all project activities.
    Supports print layout and CSV export.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_admin_user or request.user.is_superuser):
            return redirect("dashboard:student")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        export_format = request.GET.get("format", "print")
        date_filter = request.GET.get("date_range", "all")
        activity_type_filter = request.GET.get("type", "all").upper()

        valid_date_filters = {"all", "today", "7_days", "30_days"}
        valid_activity_types = {"all", "COMPLAINT", "MAINTENANCE", "ASSET", "INVENTORY"}
        if date_filter not in valid_date_filters:
            date_filter = "all"
        if activity_type_filter not in valid_activity_types:
            activity_type_filter = "all"
        
        today_date = now()
        start_date = None
        if date_filter == "today":
            start_date = today_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "7_days":
            start_date = today_date - timedelta(days=7)
        elif date_filter == "30_days":
            start_date = today_date - timedelta(days=30)
            
        activities = []

        def add_activity(activity_type, display, timestamp, user_name, title, description, status):
            if start_date and timestamp < start_date:
                return
            if activity_type_filter != "all" and activity_type != activity_type_filter:
                return
            activities.append({
                "timestamp": timestamp,
                "activity_type": activity_type,
                "activity_type_display": display,
                "user_name": user_name or "Not recorded",
                "title": title,
                "description": description or "Not specified",
                "status": status or "Not specified",
            })

        complaints = Complaint.objects.select_related("user", "assigned_to", "asset", "location_record")
        for complaint in complaints:
            submitted_by = complaint.user.name or complaint.user.username if complaint.user else "Not recorded"
            add_activity(
                "COMPLAINT",
                "Complaint",
                complaint.created_at,
                submitted_by,
                f"{complaint.complaint_id}: {complaint.title}",
                complaint.description,
                complaint.get_status_display(),
            )

        histories = ComplaintHistory.objects.select_related("complaint", "changed_by")
        for history in histories:
            changed_by = history.changed_by.name or history.changed_by.username if history.changed_by else "Not recorded"
            add_activity(
                "MAINTENANCE",
                "Maintenance",
                history.timestamp,
                changed_by,
                f"{history.complaint.complaint_id}: {history.complaint.title}",
                history.comment or f"Status changed to {history.status}",
                history.status,
            )

        maintenance_requests = MaintenanceRequest.objects.select_related("complaint", "requested_by")
        for request_item in maintenance_requests:
            requested_by = request_item.requested_by.name or request_item.requested_by.username if request_item.requested_by else "Not recorded"
            add_activity(
                "MAINTENANCE",
                "Maintenance",
                request_item.created_at,
                requested_by,
                f"{request_item.get_request_type_display()}: {request_item.complaint.complaint_id}",
                request_item.reason,
                request_item.get_status_display(),
            )

        assets = Asset.objects.select_related("location")
        for asset in assets:
            location = asset.location.get_full_path() if asset.location else asset.building or "Not specified"
            add_activity(
                "ASSET",
                "Asset",
                asset.updated_at,
                "Not recorded",
                f"{asset.asset_code}: {asset.name}",
                f"Location: {location}; Category: {asset.get_category_display()}",
                asset.get_status_display(),
            )

        inventory_items = InventoryItem.objects.select_related("category", "location")
        for item in inventory_items:
            location = item.location.name if item.location else item.storage_location or "Not specified"
            add_activity(
                "INVENTORY",
                "Inventory",
                item.updated_at,
                "Not recorded",
                item.name,
                f"Category: {item.category.name}; Quantity: {item.quantity} {item.unit}; Location: {location}",
                item.stock_status,
            )

        stock_transactions = StockTransaction.objects.select_related("item", "created_by")
        for transaction in stock_transactions:
            created_by = transaction.created_by.name or transaction.created_by.username if transaction.created_by else "Not recorded"
            add_activity(
                "INVENTORY",
                "Inventory",
                transaction.created_at,
                created_by,
                f"{transaction.get_transaction_type_display()}: {transaction.item.name}",
                f"{transaction.quantity} {transaction.item.unit}; {transaction.notes or 'Stock transaction recorded'}",
                transaction.item.stock_status,
            )

        activities.sort(key=lambda activity: activity["timestamp"], reverse=True)
        total_activities = len(activities)
        complaint_count = sum(activity["activity_type"] == "COMPLAINT" for activity in activities)
        maintenance_count = sum(activity["activity_type"] == "MAINTENANCE" for activity in activities)
        asset_count = sum(activity["activity_type"] == "ASSET" for activity in activities)
        inventory_count = sum(activity["activity_type"] == "INVENTORY" for activity in activities)
        
        if export_format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="smart_campus_activities_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(["Smart Campus - All Project Activities Audit Report"])
            writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(["Filters Applied", f"Date Range: {date_filter}, Type: {activity_type_filter}"])
            writer.writerow(["Total Activities Found", total_activities])
            writer.writerow([])
            
            writer.writerow(["--- Activity Type Summaries ---"])
            writer.writerow(["Type", "Count"])
            writer.writerow(["Complaints", complaint_count])
            writer.writerow(["Maintenance Tasks", maintenance_count])
            writer.writerow(["Assets Updates", asset_count])
            writer.writerow(["Inventory Updates", inventory_count])
            writer.writerow([])
            
            writer.writerow(["--- Detailed Activity Audit Logs ---"])
            writer.writerow(["Timestamp", "Activity Type", "Logged By", "Title", "Description", "Status"])
            for act in activities:
                writer.writerow([
                    act["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                    act["activity_type_display"],
                    act["user_name"],
                    act["title"],
                    act["description"],
                    act["status"],
                ])
                
            return response
            
        else: # Print format
            context = {
                "generated_at": now(),
                "date_range": date_filter,
                "type_filter": activity_type_filter,
                "activities": activities,
                "summary": {
                    "total": total_activities,
                    "complaints": complaint_count,
                    "maintenance": maintenance_count,
                    "assets": asset_count,
                    "inventory": inventory_count,
                }
            }
            from django.shortcuts import render
            return render(request, "dashboard/reports_export.html", context)

class NotificationMarkReadView(LoginRequiredMixin, View):
    """
    Marks a single notification as read. Recipient scoping ensures users can
    only touch their own notifications (others get 404, leaking nothing).
    """

    def post(self, request, pk, *args, **kwargs):
        from django.shortcuts import get_object_or_404

        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return redirect(request.META.get("HTTP_REFERER", reverse("dashboard:maintenance")))


class SwitchRoleView(LoginRequiredMixin, View):
    """
    Enables authenticated user to switch between views if authorized.
    """
    def get(self, request, *args, **kwargs):
        new_role = request.GET.get("role", "admin")
        if new_role == "admin" and (request.user.is_admin_user or request.user.is_superuser):
            return redirect("dashboard:admin")
        return redirect("dashboard:student")

class SubmitComplaintView(LoginRequiredMixin, View):
    """
    Handles complaint submission from the Home page or Student Portal.
    """
    def post(self, request, *args, **kwargs):
        title = request.POST.get("title", "").strip()
        category = request.POST.get("category", "COMPLAINT").upper()
        description = request.POST.get("description", "").strip()
        user_name = request.POST.get("user_name", "").strip()
        
        if not title:
            messages.error(request, "Complaint title is required.")
            return redirect(request.META.get("HTTP_REFERER", "/#raise-complaint"))
            
        user = request.user
        if not user_name:
            user_name = user.name or user.username
                
        # Save activity
        log_activity(
            user=user,
            activity_type=category if category in ['COMPLAINT', 'MAINTENANCE', 'ASSET', 'INVENTORY'] else 'COMPLAINT',
            title=title,
            description=description,
            status="Pending",
            user_name=user_name
        )
        
        messages.success(request, f"Complaint '{title}' successfully logged! Tracking status: Pending.")
        return redirect(request.META.get("HTTP_REFERER", "/#raise-complaint"))

