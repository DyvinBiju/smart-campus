from django.urls import path

from .views import (
    AssetCreateView,
    AssetDeleteView,
    AssetListView,
    AssetUpdateView,
)

app_name = "assets"

urlpatterns = [
    path("", AssetListView.as_view(), name="asset_list"),
    path("create/", AssetCreateView.as_view(), name="asset_create"),
    path("<int:pk>/edit/", AssetUpdateView.as_view(), name="asset_update"),
    path("<int:pk>/delete/", AssetDeleteView.as_view(), name="asset_delete"),
]