from django.urls import path

from .views import admin_dashboard_view
from .views import faculty_dashboard_view
from .views import faculty_signup_view
from .views import maintenance_dashboard_view
from .views import student_dashboard_view
from .views import student_signup_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("signup/student/", view=student_signup_view, name="student_signup"),
    path("signup/faculty/", view=faculty_signup_view, name="faculty_signup"),
    path("dashboard/student/", view=student_dashboard_view, name="student_dashboard"),
    path("dashboard/faculty/", view=faculty_dashboard_view, name="faculty_dashboard"),
    path("dashboard/maintenance/", view=maintenance_dashboard_view, name="maintenance_dashboard"),
    path("dashboard/admin/", view=admin_dashboard_view, name="admin_dashboard"),
    path("<str:username>/", view=user_detail_view, name="detail"),
]

