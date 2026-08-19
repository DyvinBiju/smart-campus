from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .forms import AssetForm
from .models import Asset


class AssetListView(ListView):
    """
    Displays a list of campus assets with search, status filtering,
    category filtering, and summary statistics.
    """

    model = Asset
    template_name = "assets/asset_list.html"
    context_object_name = "assets"
    paginate_by = 15

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
        """Add summary statistics and filter dropdown options to context."""
        context = super().get_context_data(**kwargs)

        # Summary statistics from the entire asset database
        all_assets = Asset.objects.all()
        context["total_count"] = all_assets.count()
        context["active_count"] = all_assets.filter(status="ACTIVE").count()
        context["maintenance_count"] = all_assets.filter(
            status="UNDER_MAINTENANCE"
        ).count()
        context["damaged_count"] = all_assets.filter(status="DAMAGED").count()

        # Dropdown options for filter forms
        context["status_choices"] = Asset.STATUS_CHOICES
        context["category_choices"] = Asset.CATEGORY_CHOICES

        # Current active filter values
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_category"] = self.request.GET.get("category", "")

        return context


class AssetDetailView(DetailView):
    """
    Displays full details for a single asset.
    """

    model = Asset
    template_name = "assets/asset_detail.html"
    context_object_name = "asset"


class AssetCreateView(SuccessMessageMixin, CreateView):
    """
    Handles creating a new asset with success feedback.
    """

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


class AssetUpdateView(SuccessMessageMixin, UpdateView):
    """
    Handles updating an existing asset with success feedback.
    """

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


class AssetDeleteView(DeleteView):
    """
    Handles removing an asset with confirmation and success feedback.
    """

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
