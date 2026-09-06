from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardIndexView.as_view(), name="index"),
    path("student/", views.StudentDashboardView.as_view(), name="student"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("maintenance/", views.MaintenanceDashboardView.as_view(), name="maintenance"),
    path("reports/", views.ReportExportView.as_view(), name="reports"),
    path("switch-role/", views.SwitchRoleView.as_view(), name="switch-role"),
    path("submit-complaint/", views.SubmitComplaintView.as_view(), name="submit-complaint"),
]

