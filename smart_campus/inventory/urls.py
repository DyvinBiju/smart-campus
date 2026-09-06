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
    path("<int:pk>/", views.inventory_detail, name="detail"),
    path("<int:pk>/edit/", views.inventory_update, name="update"),
    path("<int:pk>/delete/", views.inventory_delete, name="delete"),
    path("<int:pk>/stock/", views.stock_transaction_create, name="stock_transaction"),
    path("<int:pk>/use/", views.inventory_use_for_complaint, name="use_for_complaint"),
    path("<int:pk>/report-unavailable/", views.inventory_report_unavailable, name="report_unavailable"),
]