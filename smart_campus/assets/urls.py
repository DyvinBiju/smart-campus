from django.urls import path

from .views import (
    AssetCreateView,
    AssetDeleteView,
    AssetDetailView,
    AssetListView,
    AssetRetireView,
    AssetUpdateView,
    CampusLocationsView,
    LocationCreateView,
    LocationDeleteView,
    LocationDetailView,
    LocationToggleActiveView,
    LocationUpdateView,
)

app_name = "assets"

urlpatterns = [
    # Asset Management Routes
    path("", AssetListView.as_view(), name="asset_list"),
    path("create/", AssetCreateView.as_view(), name="asset_create"),
    path("<int:pk>/", AssetDetailView.as_view(), name="asset_detail"),
    path("<int:pk>/edit/", AssetUpdateView.as_view(), name="asset_update"),
    path("<int:pk>/retire/", AssetRetireView.as_view(), name="asset_retire"),
    path("<int:pk>/delete/", AssetDeleteView.as_view(), name="asset_delete"),
    # Location Management Routes
    path("locations/", CampusLocationsView.as_view(), name="campus_locations"),
    path("locations/create/", LocationCreateView.as_view(), name="location_create"),
    path("locations/<int:pk>/", LocationDetailView.as_view(), name="location_detail"),
    path("locations/<int:pk>/edit/", LocationUpdateView.as_view(), name="location_update"),
    path("locations/<int:pk>/toggle-active/", LocationToggleActiveView.as_view(), name="location_toggle_active"),
    path("locations/<int:pk>/delete/", LocationDeleteView.as_view(), name="location_delete"),
]