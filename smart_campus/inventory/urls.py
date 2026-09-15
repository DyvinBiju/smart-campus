from django.urls import path

from . import views


app_name = "inventory"


urlpatterns = [
    path("", views.inventory_list, name="list"),
    path("add/", views.inventory_create, name="create"),
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_create, name="category_create"),
    path("categories/<int:pk>/edit/", views.category_update, name="category_update"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("locations/", views.storage_location_list, name="storage_location_list"),
    path("locations/add/", views.storage_location_create, name="storage_location_create"),
    path("locations/<int:pk>/", views.storage_location_detail, name="storage_location_detail"),
    path("locations/<int:pk>/edit/", views.storage_location_update, name="storage_location_update"),
    path("locations/<int:pk>/toggle-active/", views.storage_location_toggle_active, name="storage_location_toggle_active"),
    path("locations/<int:pk>/delete/", views.storage_location_delete, name="storage_location_delete"),
    path("<int:pk>/", views.inventory_detail, name="detail"),
    path("<int:pk>/edit/", views.inventory_update, name="update"),
    path("<int:pk>/delete/", views.inventory_delete, name="delete"),
    path("<int:pk>/stock/", views.stock_transaction_create, name="stock_transaction"),
    path("<int:pk>/use/", views.inventory_use_for_complaint, name="use_for_complaint"),
    path("<int:pk>/report-unavailable/", views.inventory_report_unavailable, name="report_unavailable"),
]