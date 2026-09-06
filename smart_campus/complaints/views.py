from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from smart_campus.inventory.models import StockTransaction
from smart_campus.users.models import User
from .forms import (
    AdminDecisionForm,
    ComplaintAssignForm,
    ComplaintForm,
    DirectInventoryUsageForm,
    MaintenanceInspectionForm,
    MaintenanceRequestForm,
)
from .models import Complaint, ComplaintHistory, ComplaintResource, MaintenanceRequest


@login_required
def complaint_create(request):
    """View for Student / Faculty to raise a new complaint."""
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            # Server-side enforcement: owner is ALWAYS request.user
            complaint.user = request.user
            complaint.status = Complaint.Status.SUBMITTED

            # Auto-fill location from affected asset if location is omitted
            if complaint.asset and not complaint.location:
                loc = complaint.asset.building
                if complaint.asset.room:
                    loc += f", {complaint.asset.room}"
                complaint.location = loc

            complaint.save()
            complaint.log_history(
                status=Complaint.Status.SUBMITTED,
                changed_by=request.user,
                comment="Complaint submitted.",
            )

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
    """View to list complaints with search, filtering, and role-based authorization."""
    user = request.user
    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "").strip()
    priority_filter = request.GET.get("priority", "").strip()
    status_filter = request.GET.get("status", "").strip()
    scope_filter = request.GET.get("scope", "").strip()

    is_admin = user.is_superuser or user.role == User.Role.ADMIN or user.is_staff
    is_staff = user.role == User.Role.MAINTENANCE

    if is_admin or is_staff:
        complaints = Complaint.objects.select_related("user", "asset", "assigned_to").all()
        if scope_filter == "my":
            complaints = complaints.filter(user=user)
        elif scope_filter == "assigned":
            complaints = complaints.filter(assigned_to=user)
        elif scope_filter == "unassigned":
            complaints = complaints.filter(assigned_to__isnull=True)
    else:
        # Students & Faculty can ONLY view their own submitted complaints
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
        "is_admin": is_admin,
        "is_staff": is_staff,
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
    """Detail view showing progress timeline history, assigned staff, and role actions."""
    complaint = get_object_or_404(
        Complaint.objects.select_related("user", "asset", "assigned_to").prefetch_related(
            "resources_used__inventory_item",
            "history__changed_by",
            "maintenance_requests__requested_by",
            "maintenance_requests__inventory_item",
        ),
        complaint_id=complaint_id,
    )

    user = request.user
    is_admin = user.is_superuser or user.role == User.Role.ADMIN or user.is_staff
    is_staff = user.role == User.Role.MAINTENANCE

    # Authorization check: Students & Faculty can only view their own complaints
    if not (is_admin or is_staff):
        if complaint.user != user:
            raise PermissionDenied("You are not authorized to view this complaint.")

    usage_form = DirectInventoryUsageForm()
    request_form = MaintenanceRequestForm()
    assign_form = ComplaintAssignForm(instance=complaint)
    inspect_form = MaintenanceInspectionForm(instance=complaint)

    context = {
        "complaint": complaint,
        "is_admin": is_admin,
        "is_staff": is_staff,
        "usage_form": usage_form,
        "request_form": request_form,
        "assign_form": assign_form,
        "inspect_form": inspect_form,
        "history": complaint.history.all(),
        "resources_used": complaint.resources_used.all(),
        "maintenance_requests": complaint.maintenance_requests.all(),
    }
    return render(request, "complaints/complaint_detail.html", context)


@login_required
def assigned_complaints(request):
    """View for Maintenance Staff to see complaints assigned to them."""
    user = request.user
    if not (user.role == User.Role.MAINTENANCE or user.is_superuser or user.is_staff or user.role == User.Role.ADMIN):
        raise PermissionDenied("Access restricted to Maintenance Staff.")

    assigned_list = Complaint.objects.select_related("user", "asset").filter(assigned_to=user)
    context = {
        "complaints": assigned_list,
    }
    return render(request, "complaints/assigned_complaints.html", context)


@login_required
def admin_complaint_manage(request):
    """Administrator management hub showing unassigned complaints & pending requests."""
    user = request.user
    if not (user.is_superuser or user.role == User.Role.ADMIN or user.is_staff):
        raise PermissionDenied("Only Administrators can access complaint management.")

    unassigned_complaints = Complaint.objects.select_related("user", "asset").filter(assigned_to__isnull=True)
    pending_requests = MaintenanceRequest.objects.select_related("complaint", "requested_by", "inventory_item").filter(status="PENDING")
    all_complaints = Complaint.objects.select_related("user", "asset", "assigned_to").all()[:30]

    context = {
        "unassigned_complaints": unassigned_complaints,
        "pending_requests": pending_requests,
        "all_complaints": all_complaints,
    }
    return render(request, "complaints/admin_complaint_manage.html", context)


@login_required
def admin_assign_staff(request, complaint_id):
    """Administrator assigns an available Maintenance Staff member."""
    user = request.user
    if not (user.is_superuser or user.role == User.Role.ADMIN or user.is_staff):
        raise PermissionDenied("Only Administrators can assign staff.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = ComplaintAssignForm(request.POST, instance=complaint)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.assigned_at = timezone.now()
            if updated.status == Complaint.Status.SUBMITTED or updated.status == Complaint.Status.UNDER_REVIEW:
                updated.status = Complaint.Status.ASSIGNED
            updated.save()

            staff_name = updated.assigned_to.name or updated.assigned_to.username if updated.assigned_to else "Staff"
            updated.log_history(
                status=updated.status,
                changed_by=request.user,
                comment=f"Assigned to Maintenance Staff member {staff_name}.",
            )

            messages.success(request, f"Assigned Maintenance Staff member {staff_name} to complaint {complaint.complaint_id}.")
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)
    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_inspect(request, complaint_id):
    """Maintenance Staff records inspection findings and updates operational progress."""
    user = request.user
    if not (user.role == User.Role.MAINTENANCE or user.is_superuser or user.is_staff or user.role == User.Role.ADMIN):
        raise PermissionDenied("Only Maintenance Staff can update inspection progress.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = MaintenanceInspectionForm(request.POST, instance=complaint)
        if form.is_valid():
            updated = form.save(commit=False)
            if updated.status == Complaint.Status.RESOLVED:
                updated.resolved_at = timezone.now()
                if updated.asset:
                    updated.asset.status = "ACTIVE"
                    updated.asset.save(update_fields=["status", "updated_at"])
            elif updated.status in [Complaint.Status.IN_PROGRESS, Complaint.Status.UNDER_INSPECTION]:
                if updated.asset and updated.asset.status != "UNDER_MAINTENANCE":
                    updated.asset.status = "UNDER_MAINTENANCE"
                    updated.asset.save(update_fields=["status", "updated_at"])

            updated.save()
            updated.log_history(
                status=updated.status,
                changed_by=request.user,
                comment=f"Inspection/Progress update: {updated.inspection_notes or updated.resolution_notes or updated.get_status_display()}",
            )

            messages.success(request, f"Inspection progress updated to '{updated.get_status_display()}'.")
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_use_inventory(request, complaint_id):
    """
    Direct Available Inventory Usage by Maintenance Staff.
    Deducts available inventory, creates StockTransaction, and logs history.
    """
    user = request.user
    if not (user.role == User.Role.MAINTENANCE or user.is_superuser or user.is_staff or user.role == User.Role.ADMIN):
        raise PermissionDenied("Only Maintenance Staff can issue inventory for maintenance.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = DirectInventoryUsageForm(request.POST)
        if form.is_valid():
            inventory_item = form.cleaned_data["inventory_item"]
            quantity_used = form.cleaned_data["quantity_used"]

            with transaction.atomic():
                # 1. Record ComplaintResource
                resource = form.save(commit=False)
                resource.complaint = complaint
                resource.save()

                # 2. Record StockTransaction in inventory app
                StockTransaction.objects.create(
                    item=inventory_item,
                    transaction_type="ISSUE",
                    quantity=quantity_used,
                    asset=complaint.asset,
                    notes=f"Used for complaint {complaint.complaint_id} ({complaint.title})",
                    created_by=request.user,
                )

                # 3. Log history
                complaint.log_history(
                    status=complaint.status,
                    changed_by=request.user,
                    comment=f"Used {quantity_used} {inventory_item.unit} of {inventory_item.name} for repair.",
                )

            messages.success(
                request,
                f"Successfully issued {quantity_used} {inventory_item.unit} of {inventory_item.name} and updated inventory stock."
            )
        else:
            for error_list in form.errors.values():
                for error in error_list:
                    messages.error(request, error)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_request_action(request, complaint_id):
    """
    Maintenance Staff submits request when inventory is unavailable or asset needs repair/replace/retire.
    """
    user = request.user
    if not (user.role == User.Role.MAINTENANCE or user.is_superuser or user.is_staff or user.role == User.Role.ADMIN):
        raise PermissionDenied("Only Maintenance Staff can submit resource/asset action requests.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = MaintenanceRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.complaint = complaint
            req.requested_by = request.user
            req.status = "PENDING"
            req.save()

            complaint.status = Complaint.Status.ACTION_REQUIRED
            complaint.save(update_fields=["status", "updated_at"])
            complaint.log_history(
                status=Complaint.Status.ACTION_REQUIRED,
                changed_by=request.user,
                comment=f"Submitted Maintenance Request ({req.get_request_type_display()}): {req.reason}",
            )

            messages.success(request, "Maintenance request submitted to Administrator successfully.")
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def admin_request_decide(request, request_id):
    """Administrator reviews and decides on pending maintenance resource/asset requests."""
    user = request.user
    if not (user.is_superuser or user.role == User.Role.ADMIN or user.is_staff):
        raise PermissionDenied("Only Administrators can decide on maintenance requests.")

    req = get_object_or_404(MaintenanceRequest.objects.select_related("complaint", "inventory_item"), pk=request_id)
    complaint = req.complaint

    if request.method == "POST":
        form = AdminDecisionForm(request.POST, instance=req)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.decided_by = request.user
            decision.decided_at = timezone.now()

            if decision.status == "APPROVED":
                with transaction.atomic():
                    # Handle specific decision action types
                    if req.request_type == MaintenanceRequest.RequestType.UNAVAILABLE_RESOURCE and req.inventory_item:
                        if req.inventory_item.quantity >= req.quantity_requested:
                            # Create StockTransaction
                            StockTransaction.objects.create(
                                item=req.inventory_item,
                                transaction_type="ISSUE",
                                quantity=req.quantity_requested,
                                asset=complaint.asset,
                                notes=f"Admin approved issue for {complaint.complaint_id}",
                                created_by=request.user,
                            )
                            ComplaintResource.objects.create(
                                complaint=complaint,
                                inventory_item=req.inventory_item,
                                quantity_used=req.quantity_requested,
                            )
                        else:
                            messages.error(request, f"Cannot approve inventory issue. Requested: {req.quantity_requested}, Available: {req.inventory_item.quantity}.")
                            return redirect("complaints:detail", complaint_id=complaint.complaint_id)

                    elif req.request_type == MaintenanceRequest.RequestType.ASSET_REPAIR and complaint.asset:
                        complaint.asset.status = "UNDER_MAINTENANCE"
                        complaint.asset.save(update_fields=["status", "updated_at"])

                    elif req.request_type in [MaintenanceRequest.RequestType.ASSET_REPLACE, MaintenanceRequest.RequestType.ASSET_RETIRE] and complaint.asset:
                        complaint.asset.status = "RETIRED"
                        complaint.asset.save(update_fields=["status", "updated_at"])

                    decision.save()
                    complaint.status = Complaint.Status.IN_PROGRESS
                    complaint.save(update_fields=["status", "updated_at"])
                    complaint.log_history(
                        status=Complaint.Status.IN_PROGRESS,
                        changed_by=request.user,
                        comment=f"Admin approved request ({req.get_request_type_display()}). Notes: {decision.admin_notes}",
                    )
            else:
                decision.save()
                complaint.log_history(
                    status=complaint.status,
                    changed_by=request.user,
                    comment=f"Admin decided '{decision.get_status_display()}' on request. Notes: {decision.admin_notes}",
                )

            messages.success(request, f"Decision recorded for maintenance request.")
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


# Backward compatibility aliases
complaint_status_update = maintenance_inspect
complaint_add_resource = maintenance_use_inventory



