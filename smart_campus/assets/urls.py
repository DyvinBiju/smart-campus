from django.urls import path

from .views import (
    AssetCreateView,
    AssetDeleteView,
    AssetDetailView,
    AssetListView,
    AssetRetireView,
    AssetUpdateView,
    CampusLocationsView,
)

app_name = "assets"

urlpatterns = [
    # List all assets & search/filter
    path("", AssetListView.as_view(), name="asset_list"),
    # Campus Locations & Buildings/Rooms master view
    path("locations/", CampusLocationsView.as_view(), name="campus_locations"),
    # Add a new asset
    path("create/", AssetCreateView.as_view(), name="asset_create"),
    # View asset details
    path("<int:pk>/", AssetDetailView.as_view(), name="asset_detail"),
    # Edit an asset
    path("<int:pk>/edit/", AssetUpdateView.as_view(), name="asset_update"),
    # Retire an asset
    path("<int:pk>/retire/", AssetRetireView.as_view(), name="asset_retire"),
    # Delete an asset
    path("<int:pk>/delete/", AssetDeleteView.as_view(), name="asset_delete"),
]