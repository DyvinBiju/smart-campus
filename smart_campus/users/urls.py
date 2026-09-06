from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("signup/student/", view=views.student_signup_view, name="student_signup"),
    path("signup/faculty/", view=views.faculty_signup_view, name="faculty_signup"),
    # User Management Console Routes
    path("manage/", view=views.UserManagementListView.as_view(), name="manage"),
    path("create/", view=views.UserManagementCreateView.as_view(), name="create"),
    path("<int:pk>/", view=views.UserManagementDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", view=views.UserManagementEditView.as_view(), name="edit"),
    path("<int:pk>/toggle-active/", view=views.UserManagementToggleActiveView.as_view(), name="toggle_active"),
    # Staff Management Routes
    path("staff/", view=views.MaintenanceStaffListView.as_view(), name="staff"),
    path("staff/<int:pk>/toggle-availability/", view=views.MaintenanceStaffToggleAvailabilityView.as_view(), name="toggle_staff_availability"),
]





