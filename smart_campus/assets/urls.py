from django.urls import path

from .views import (
    AssetCreateView,
    AssetDeleteView,
    AssetDetailView,
    AssetListView,
    AssetUpdateView,
)

app_name = "assets"

urlpatterns = [
    # List all assets & search/filter
    path("", AssetListView.as_view(), name="asset_list"),
    # Add a new asset
    path("create/", AssetCreateView.as_view(), name="asset_create"),
    # View asset details
    path("<int:pk>/", AssetDetailView.as_view(), name="asset_detail"),
    # Edit an asset
    path("<int:pk>/edit/", AssetUpdateView.as_view(), name="asset_update"),
    # Delete an asset
    path("<int:pk>/delete/", AssetDeleteView.as_view(), name="asset_delete"),
]