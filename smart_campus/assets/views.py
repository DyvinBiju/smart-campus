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
from .forms import AssetForm
from .models import Asset


class AssetListView(LoginRequiredMixin, ListView):
    """
    Displays campus assets. Allowed for Administrators and Maintenance Staff.
    Denied for Student/Faculty roles.
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
        """Filter assets based on search query, status, and category."""
        queryset = super().get_queryset()

        # 1. Search Query (matches asset code, name, building, room)
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(asset_code__icontains=query)
                | Q(name__icontains=query)
                | Q(building__icontains=query)
                | Q(room__icontains=query)
                | Q(category__icontains=query)
            )

        # 2. Status Filter
        status = self.request.GET.get("status", "").strip()
        if status:
            queryset = queryset.filter(status=status)

        # 3. Category Filter
        category = self.request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)

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

        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_category"] = self.request.GET.get("category", "")

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
        context["related_complaints"] = self.object.complaints.all()[:10]
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
    Campus Management view grouping buildings, rooms, and physical asset distribution.
    """

    model = Asset
    template_name = "assets/campus_locations.html"
    context_object_name = "assets"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_assets = Asset.objects.all()

        buildings_dict = {}
        for asset in all_assets:
            b_name = asset.building or "Unspecified Building"
            r_name = asset.room or "General Space"

            if b_name not in buildings_dict:
                buildings_dict[b_name] = {
                    "building_name": b_name,
                    "total_assets": 0,
                    "active_assets": 0,
                    "maintenance_assets": 0,
                    "rooms": set(),
                }

            b_entry = buildings_dict[b_name]
            b_entry["total_assets"] += 1
            if asset.status == "ACTIVE":
                b_entry["active_assets"] += 1
            elif asset.status == "UNDER_MAINTENANCE":
                b_entry["maintenance_assets"] += 1

            if r_name:
                b_entry["rooms"].add(r_name)

        buildings_list = []
        for b_name, data in sorted(buildings_dict.items()):
            data["rooms_list"] = sorted(list(data["rooms"]))
            data["room_count"] = len(data["rooms"])
            buildings_list.append(data)

        context["buildings"] = buildings_list
        context["total_buildings"] = len(buildings_list)
        context["total_assets"] = all_assets.count()
        return context


