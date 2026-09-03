import csv
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.timezone import now
from django.views.generic import TemplateView, View

from smart_campus.users.models import User
from .models import Activity
from .helpers import (
    get_modules_info,
    get_assets_metrics,
    get_inventory_metrics,
    get_complaints_metrics,
    seed_mock_activities,
    log_activity,
)

def get_current_role_and_user(request):
    """
    Determines user staff/admin status and returns (is_staff, user).
    """
    seed_mock_activities()
    user = request.user
    if user.is_authenticated:
        is_staff = user.is_staff or user.is_superuser or user.is_admin_user or user.is_maintenance_staff
    else:
        user = AnonymousUser()
        is_staff = False
            
    return is_staff, user

class DashboardIndexView(LoginRequiredMixin, View):
    """
    Landing redirector. Directs staff/admins to the Admin Operations dashboard,
    and regular users (Students/Faculty) to the Student portal dashboard.
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        if user.is_admin_user or user.is_maintenance_staff:
            return redirect("dashboard:admin")
        return redirect("dashboard:student")

class StudentDashboardView(LoginRequiredMixin, TemplateView):
    """
    Portal for regular campus users (Students / non-admin staff).
    Displays personal stats, raised complaints summaries, and recent activity updates.
    """
    template_name = "dashboard/student_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        is_staff, user = get_current_role_and_user(self.request)
        
        # Retrieve modules info
        modules = get_modules_info()
        
        # Retrieve complaints metrics for this specific user
        complaints_stats = get_complaints_metrics(user=user)
        
        # Get recent updates relevant to COMPLAINTS for this user
        recent_updates = Activity.objects.filter(
            activity_type__in=['COMPLAINT', 'MAINTENANCE']
        )
        if user.is_authenticated or not isinstance(user, AnonymousUser):
            recent_updates = recent_updates.filter(user=user)
        recent_updates = recent_updates.order_by('-timestamp')[:5]
        
        context.update({
            "modules": modules,
            "complaints_stats": complaints_stats,
            "user_stats": {
                "date_joined": user.date_joined if hasattr(user, 'date_joined') else now(),
                "email": user.email if hasattr(user, 'email') else "student1@campus.edu",
                "name": user.name if hasattr(user, 'name') and user.name else (user.username if hasattr(user, 'username') else "John Student"),
            },
            "recent_updates": recent_updates,
            "quick_links": [
                {"name": "View My Complaints", "url": "#complaint-log-section", "icon": "fa-list-check"},
                {"name": "My Profile Settings", "url": f"/users/{user.username}/" if hasattr(user, 'username') else "#", "icon": "fa-user-gear"},
                {"name": "Help & Support", "url": "/about/", "icon": "fa-circle-question"},
            ],
            "preview_mode": not self.request.user.is_authenticated,
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
        if not (request.user.is_admin_user or request.user.is_maintenance_staff or request.user.is_staff):
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
        
        # Query recent activities audit feed
        recent_activities = Activity.objects.all()
        if start_date:
            recent_activities = recent_activities.filter(timestamp__gte=start_date)
            
        if category_filter != "all":
            recent_activities = recent_activities.filter(activity_type__iexact=category_filter)
        if status_filter != "all":
            recent_activities = recent_activities.filter(status__iexact=status_filter)
            
        recent_activities = recent_activities.order_by('-timestamp')[:8]
        
        # Calculate trend chart values (last 7 days counts)
        trend_dates = []
        complaints_trend = []
        assets_trend = []
        for i in range(6, -1, -1):
            d = today_date - timedelta(days=i)
            trend_dates.append(d.strftime("%b %d"))
            
            c_count = Activity.objects.filter(
                activity_type__in=['COMPLAINT', 'MAINTENANCE'],
                timestamp__date=d.date()
            ).count()
            
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
        if not (request.user.is_admin_user or request.user.is_maintenance_staff or request.user.is_staff):
            return redirect("dashboard:student")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Ensure database is seeded
        seed_mock_activities()
        
        export_format = request.GET.get("format", "print")
        date_filter = request.GET.get("date_range", "all")
        activity_type_filter = request.GET.get("type", "all")
        
        today_date = now()
        start_date = None
        if date_filter == "today":
            start_date = today_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_filter == "7_days":
            start_date = today_date - timedelta(days=7)
        elif date_filter == "30_days":
            start_date = today_date - timedelta(days=30)
            
        # Query activities
        activities_qs = Activity.objects.all()
        if start_date:
            activities_qs = activities_qs.filter(timestamp__gte=start_date)
        if activity_type_filter != "all":
            activities_qs = activities_qs.filter(activity_type__iexact=activity_type_filter)
            
        activities = activities_qs.order_by('-timestamp')
        total_activities = activities.count()
        complaint_count = activities.filter(activity_type='COMPLAINT').count()
        maintenance_count = activities.filter(activity_type='MAINTENANCE').count()
        asset_count = activities.filter(activity_type='ASSET').count()
        inventory_count = activities.filter(activity_type='INVENTORY').count()
        
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
                    act.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    act.get_activity_type_display(),
                    act.user_name or "System",
                    act.title,
                    act.description,
                    act.status or "N/A"
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

class SwitchRoleView(LoginRequiredMixin, View):
    """
    Enables authenticated user to switch between views if authorized.
    """
    def get(self, request, *args, **kwargs):
        new_role = request.GET.get("role", "admin")
        if new_role == "admin" and (request.user.is_admin_user or request.user.is_maintenance_staff or request.user.is_staff):
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

