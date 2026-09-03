from django.urls import path
from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list, name="list"),
    path("create/", views.complaint_create, name="create"),
    path("<str:complaint_id>/", views.complaint_detail, name="detail"),
    path("<str:complaint_id>/status/", views.complaint_status_update, name="status_update"),
    path("<str:complaint_id>/add-resource/", views.complaint_add_resource, name="add_resource"),
]
