from django.urls import path
from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list, name="list"),
    path("create/", views.complaint_create, name="create"),
    path("assigned/", views.assigned_complaints, name="assigned"),
    path("admin-manage/", views.admin_complaint_manage, name="admin_manage"),
    path("requests/<int:request_id>/decide/", views.admin_request_decide, name="request_decide"),
    path("<str:complaint_id>/", views.complaint_detail, name="detail"),
    path("<str:complaint_id>/assign/", views.admin_assign_staff, name="assign_staff"),
    path("<str:complaint_id>/inspect/", views.maintenance_inspect, name="inspect"),
    path("<str:complaint_id>/use-inventory/", views.maintenance_use_inventory, name="use_inventory"),
    path("<str:complaint_id>/request-action/", views.maintenance_request_action, name="request_action"),
    path("<str:complaint_id>/status/", views.complaint_status_update, name="status_update"),
    path("<str:complaint_id>/add-resource/", views.complaint_add_resource, name="add_resource"),
]
