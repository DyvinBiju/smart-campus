from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import timezone
from smart_campus.users.models import User

from .forms import ComplaintForm
from .forms import ComplaintResourceForm
from .forms import ComplaintStatusUpdateForm
from .models import Complaint
from .models import ComplaintResource


@login_required
def complaint_create(request):
    """View to raise a new complaint (Requires Authentication)."""
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            # Server-side enforcement: owner is ALWAYS request.user
            complaint.user = request.user

            # Auto-fill location from affected asset if location is omitted
            if complaint.asset and not complaint.location:
                loc = complaint.asset.building
                if complaint.asset.room:
                    loc += f", {complaint.asset.room}"
                complaint.location = loc

            complaint.save()
            messages.success(
                request,
                f"Complaint submitted successfully! Complaint ID: {complaint.complaint_id}",
            )
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)
    else:
        form = ComplaintForm()

    return render(request, "complaints/complaint_form.html", {"form": form})


@login_required
def complaint_list(request):
    """View to list complaints with search, filtering, and role-based access control."""
    user = request.user
    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "").strip()
    priority_filter = request.GET.get("priority", "").strip()
    status_filter = request.GET.get("status", "").strip()
    scope_filter = request.GET.get("scope", "").strip()

    is_admin_or_staff = user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MAINTENANCE] or user.is_staff

    # Role-based Queryset filtering: Admin/Maintenance sees all complaints; regular users see only their own.
    if is_admin_or_staff:
        complaints = Complaint.objects.select_related("user", "asset", "assigned_to").all()
        if scope_filter == "my":
            complaints = complaints.filter(user=user)
        elif scope_filter == "assigned":
            complaints = complaints.filter(assigned_to=user)
    else:
        # Students & Faculty can only view their own submitted complaints
        complaints = Complaint.objects.select_related("user", "asset", "assigned_to").filter(user=user)

    if search_query:
        complaints = complaints.filter(
            Q(complaint_id__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(asset__name__icontains=search_query)
            | Q(asset__asset_code__icontains=search_query)
        )

    if category_filter:
        complaints = complaints.filter(category=category_filter)

    if priority_filter:
        complaints = complaints.filter(priority=priority_filter)

    if status_filter:
        complaints = complaints.filter(status=status_filter)

    has_active_filters = bool(
        search_query or category_filter or priority_filter or status_filter or scope_filter
    )

    context = {
        "complaints": complaints,
        "is_admin_or_staff": is_admin_or_staff,
        "search_query": search_query,
        "category_filter": category_filter,
        "priority_filter": priority_filter,
        "status_filter": status_filter,
        "scope_filter": scope_filter,
        "categories": Complaint.Category.choices,
        "priorities": Complaint.Priority.choices,
        "statuses": Complaint.Status.choices,
        "has_active_filters": has_active_filters,
    }
    return render(request, "complaints/complaint_list.html", context)


@login_required
def complaint_detail(request, complaint_id):
    """View to display details of a single complaint with ownership/role authorization."""
    complaint = get_object_or_404(
        Complaint.objects.select_related("user", "asset", "assigned_to").prefetch_related(
            "resources_used__inventory_item"
        ),
        complaint_id=complaint_id,
    )

    user = request.user
    # Authorization check: Students & Faculty can only view their own complaints
    if not (user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MAINTENANCE]):
        if complaint.user != user:
            raise PermissionDenied("You are not authorized to view this complaint.")

    resource_form = ComplaintResourceForm()
    return render(
        request,
        "complaints/complaint_detail.html",
        {
            "complaint": complaint,
            "resource_form": resource_form,
            "resources_used": complaint.resources_used.all(),
        },
    )


@login_required
def complaint_status_update(request, complaint_id):
    """View to update complaint status (Maintenance & Admin only)."""
    user = request.user
    if not (user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MAINTENANCE]):
        raise PermissionDenied("Only Maintenance Staff and Administrators can update complaint status.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = ComplaintStatusUpdateForm(request.POST, instance=complaint)
        if form.is_valid():
            updated_complaint = form.save(commit=False)

            # Auto update timestamp for technician assignment
            if updated_complaint.assigned_to and not updated_complaint.assigned_at:
                updated_complaint.assigned_at = timezone.now()

            # Auto update timestamp for resolution
            if updated_complaint.status == Complaint.Status.RESOLVED:
                if not updated_complaint.resolved_at:
                    updated_complaint.resolved_at = timezone.now()
                # If an asset is attached, update asset status back to ACTIVE
                if updated_complaint.asset:
                    updated_complaint.asset.status = "ACTIVE"
                    updated_complaint.asset.save(update_fields=["status", "updated_at"])
            elif updated_complaint.status in [Complaint.Status.IN_PROGRESS, Complaint.Status.UNDER_REVIEW]:
                # If an asset is attached, set asset status to UNDER_MAINTENANCE
                if updated_complaint.asset and updated_complaint.asset.status != "UNDER_MAINTENANCE":
                    updated_complaint.asset.status = "UNDER_MAINTENANCE"
                    updated_complaint.asset.save(update_fields=["status", "updated_at"])

            updated_complaint.save()
            messages.success(
                request,
                f"Complaint status updated successfully to '{updated_complaint.get_status_display()}'.",
            )
            return redirect("complaints:detail", complaint_id=updated_complaint.complaint_id)
    else:
        form = ComplaintStatusUpdateForm(instance=complaint)

    return render(
        request,
        "complaints/complaint_status_form.html",
        {"form": form, "complaint": complaint},
    )


@login_required
def complaint_add_resource(request, complaint_id):
    """View to record inventory resources used (Maintenance & Admin only)."""
    user = request.user
    if not (user.is_superuser or user.role in [User.Role.ADMIN, User.Role.MAINTENANCE]):
        raise PermissionDenied("Only Maintenance Staff and Administrators can log spare resources.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = ComplaintResourceForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                resource = form.save(commit=False)
                resource.complaint = complaint
                resource.save()

                # Deduct inventory stock
                inventory_item = resource.inventory_item
                inventory_item.quantity -= resource.quantity_used
                inventory_item.save(update_fields=["quantity", "updated_at"])

            messages.success(
                request,
                f"Added {resource.quantity_used} x {inventory_item.name} to complaint records and updated inventory stock.",
            )
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


