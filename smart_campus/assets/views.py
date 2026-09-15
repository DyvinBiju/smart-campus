from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
    View,
)

from smart_campus.users.models import User
from smart_campus.users.views import RoleRequiredMixin
from .forms import AssetForm, LocationForm
from .models import Asset, Location


class AssetListView(LoginRequiredMixin, ListView):
    """
    Displays campus assets. Allowed for Administrators and Maintenance Staff.
    Denied for student roles.
    """

    model = Asset
    template_name = "assets/asset_list.html"
    context_object_name = "assets"
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_allowed = (
            getattr(request.user, "is_admin_user", False)
            or getattr(request.user, "is_maintenance_staff", False)
            or request.user.is_superuser
            or request.user.is_staff
        )
        if not is_allowed:
            raise PermissionDenied("Access denied. Asset records are restricted to Administrators and Maintenance Staff.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Filter assets based on search query, status, category, and location."""
        queryset = super().get_queryset().select_related("location", "location__parent")

        # 1. Search Query (matches asset code, name, building, room, location name)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(asset_code__icontains=query)
                | Q(name__icontains=query)
                | Q(building__icontains=query)
                | Q(room__icontains=query)
                | Q(category__icontains=query)
                | Q(location__name__icontains=query)
                | Q(location__parent__name__icontains=query)
            )

        # 2. Status Filter
        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        # 3. Category Filter
        category = self.request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)

        # 4. Location Filter
        loc_id = self.request.GET.get("location", "").strip()
        if loc_id and loc_id.isdigit():
            queryset = queryset.filter(Q(location_id=int(loc_id)) | Q(location__parent_id=int(loc_id)))

        return queryset

    def get_context_data(self, **kwargs):
        """Add summary statistics, role flags, and filter options to context."""
        context = super().get_context_data(**kwargs)

        all_assets = Asset.objects.all()
        context["total_count"] = all_assets.count()
        context["active_count"] = all_assets.filter(status="ACTIVE").count()
        context["maintenance_count"] = all_assets.filter(status="UNDER_MAINTENANCE").count()
        context["damaged_count"] = all_assets.filter(status="DAMAGED").count()
        context["retired_count"] = all_assets.filter(status="RETIRED").count()

        context["status_choices"] = Asset.STATUS_CHOICES
        context["category_choices"] = Asset.CATEGORY_CHOICES
        context["available_locations"] = Location.objects.filter(is_active=True)

        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["selected_location"] = self.request.GET.get("location", "")

        user = self.request.user
        context["is_admin"] = getattr(user, "is_admin_user", False) or user.is_superuser
        context["is_maintenance_staff"] = getattr(user, "is_maintenance_staff", False)

        return context


class AssetDetailView(LoginRequiredMixin, DetailView):
    """
    Displays full details for a single asset. Restricted to Admin and Maintenance Staff.
    """

    model = Asset
    template_name = "assets/asset_detail.html"
    context_object_name = "asset"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_allowed = (
            getattr(request.user, "is_admin_user", False)
            or getattr(request.user, "is_maintenance_staff", False)
            or request.user.is_superuser
            or request.user.is_staff
        )
        if not is_allowed:
            raise PermissionDenied("Access denied. You are not authorized to view asset details.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_admin"] = getattr(user, "is_admin_user", False) or user.is_superuser
        context["is_maintenance_staff"] = getattr(user, "is_maintenance_staff", False)
        context["related_complaints"] = self.object.complaints.select_related("user", "assigned_to").all()[:10]
        return context


class AssetCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Handles creating a new asset. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Asset
    form_class = AssetForm
    template_name = "assets/asset_form.html"
    success_url = reverse_lazy("assets:asset_list")
    success_message = "Asset '%(name)s' (%(asset_code)s) was successfully created!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add New Asset"
        context["button_text"] = "Create Asset"
        return context


class AssetUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Handles updating an existing asset. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Asset
    form_class = AssetForm
    template_name = "assets/asset_form.html"
    success_url = reverse_lazy("assets:asset_list")
    success_message = "Asset '%(name)s' (%(asset_code)s) was successfully updated!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Asset: {self.object.asset_code}"
        context["button_text"] = "Save Changes"
        return context


class AssetDeleteView(RoleRequiredMixin, DeleteView):
    """
    Handles removing an asset with confirmation feedback. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Asset
    template_name = "assets/asset_confirm_delete.html"
    context_object_name = "asset"
    success_url = reverse_lazy("assets:asset_list")

    def form_valid(self, form):
        asset_name = self.object.name
        asset_code = self.object.asset_code
        messages.success(
            self.request,
            f"Asset '{asset_name}' ({asset_code}) has been deleted successfully.",
        )
        return super().form_valid(form)


class AssetRetireView(RoleRequiredMixin, View):
    """
    POST action to safely retire an asset. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        asset = get_object_or_404(Asset, pk=pk)
        asset.status = "RETIRED"
        asset.save()
        messages.success(
            request,
            f"Asset '{asset.name}' ({asset.asset_code}) has been marked as RETIRED.",
        )
        return redirect("assets:asset_detail", pk=asset.pk)


class CampusLocationsView(LoginRequiredMixin, ListView):
    """
    Master Location Directory and Admin Management view for campus blocks, rooms, labs, and offices.
    """

    model = Location
    template_name = "assets/campus_locations.html"
    context_object_name = "locations"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_allowed = (
            getattr(request.user, "is_admin_user", False)
            or getattr(request.user, "is_maintenance_staff", False)
            or request.user.is_superuser
            or request.user.is_staff
        )
        if not is_allowed:
            raise PermissionDenied("Access denied to campus locations directory.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Location.objects.select_related("parent").prefetch_related("assets", "complaints").all()

        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(parent__name__icontains=query)
                | Q(location_type__icontains=query)
            )

        loc_type = self.request.GET.get("type", "").strip()
        if loc_type:
            queryset = queryset.filter(location_type=loc_type)

        parent_id = self.request.GET.get("parent", "").strip()
        if parent_id and parent_id.isdigit():
            queryset = queryset.filter(parent_id=int(parent_id))

        status = self.request.GET.get("status", "").strip()
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_locations = Location.objects.all()

        context["total_locations"] = all_locations.count()
        context["active_locations"] = all_locations.filter(is_active=True).count()
        context["inactive_locations"] = all_locations.filter(is_active=False).count()
        context["total_assets"] = Asset.objects.count()

        context["location_types"] = Location.LOCATION_TYPE_CHOICES
        context["parent_locations"] = Location.objects.filter(parent__isnull=True, is_active=True)

        context["search_query"] = self.request.GET.get("q", "")
        context["selected_type"] = self.request.GET.get("type", "")
        context["selected_parent"] = self.request.GET.get("parent", "")
        context["selected_status"] = self.request.GET.get("status", "")

        user = self.request.user
        context["is_admin"] = getattr(user, "is_admin_user", False) or user.is_superuser
        context["is_maintenance_staff"] = getattr(user, "is_maintenance_staff", False)

        return context


class LocationCreateView(RoleRequiredMixin, SuccessMessageMixin, CreateView):
    """
    Handles creating a new campus location. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Location
    form_class = LocationForm
    template_name = "assets/location_form.html"
    success_url = reverse_lazy("assets:campus_locations")
    success_message = "Campus location '%(name)s' was created successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add New Campus Location"
        context["button_text"] = "Create Location"
        return context


class LocationUpdateView(RoleRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Handles editing an existing campus location. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Location
    form_class = LocationForm
    template_name = "assets/location_form.html"
    success_url = reverse_lazy("assets:campus_locations")
    success_message = "Campus location '%(name)s' was updated successfully!"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit Location: {self.object.name}"
        context["button_text"] = "Save Location Changes"
        return context


class LocationDetailView(LoginRequiredMixin, DetailView):
    """
    Displays full details for a location including parent hierarchy, assigned assets, and associated complaints.
    """

    model = Location
    template_name = "assets/location_detail.html"
    context_object_name = "location"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        is_allowed = (
            getattr(request.user, "is_admin_user", False)
            or getattr(request.user, "is_maintenance_staff", False)
            or request.user.is_superuser
            or request.user.is_staff
        )
        if not is_allowed:
            raise PermissionDenied("Access denied. You are not authorized to view location details.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_admin"] = getattr(user, "is_admin_user", False) or user.is_superuser
        context["is_maintenance_staff"] = getattr(user, "is_maintenance_staff", False)
        context["assigned_assets"] = self.object.assets.all()
        context["associated_complaints"] = self.object.complaints.select_related("user", "asset", "assigned_to").all()
        context["child_locations"] = self.object.children.filter(is_active=True)
        return context


class LocationToggleActiveView(RoleRequiredMixin, View):
    """
    Toggles the active state of a location. Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]

    def post(self, request, pk, *args, **kwargs):
        location = get_object_or_404(Location, pk=pk)
        location.is_active = not location.is_active
        location.save()
        status_str = "ACTIVATED" if location.is_active else "DEACTIVATED"
        messages.success(request, f"Location '{location.name}' has been {status_str}.")
        return redirect("assets:campus_locations")


class LocationDeleteView(RoleRequiredMixin, DeleteView):
    """
    Deletes a location if safe (no linked assets or complaints). Admin-only.
    """

    allowed_roles = [User.Role.ADMIN]
    model = Location
    template_name = "assets/location_confirm_delete.html"
    context_object_name = "location"
    success_url = reverse_lazy("assets:campus_locations")

    def form_valid(self, form):
        location = self.get_object()
        if location.assets.exists() or location.complaints.exists():
            messages.error(
                self.request,
                f"Cannot delete location '{location.name}' because it has {location.asset_count} linked asset(s) and {location.complaint_count} complaint(s). Deactivate it instead to preserve audit records.",
            )
            return redirect("assets:campus_locations")

        messages.success(self.request, f"Location '{location.name}' deleted successfully.")
        return super().form_valid(form)
