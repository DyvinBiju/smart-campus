from django.urls import path
from . import views

app_name = "complaints"

urlpatterns = [
    path("", views.complaint_list, name="list"),
    path("create/", views.complaint_create, name="create"),
    path("<str:complaint_id>/", views.complaint_detail, name="detail"),
    path("<str:complaint_id>/status/", views.complaint_status_update, name="status_update"),
]
