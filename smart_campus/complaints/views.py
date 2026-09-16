from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from smart_campus.dashboard.models import Notification
from smart_campus.inventory.models import StockTransaction
from smart_campus.users.models import User
from .forms import (
    AdminDecisionForm,
    ComplaintAssignForm,
    ComplaintForm,
    DirectInventoryUsageForm,
    MaintenanceInspectionForm,
    MaintenanceRejectionForm,
    MaintenanceRequestForm,
)
from .models import Complaint, ComplaintHistory, ComplaintResource, MaintenanceRequest


# Public-facing student tracker configuration. Internal operational details
# (staff names, reasons, inventory, procurement) are never exposed here.
STUDENT_TRACKER_STAGES = [
    "Submitted",
    "Under Review",
    "Maintenance Started",
    "In Progress",
    "Resolved",
]

# Maps internal complaint status -> (stage index, public title, public update).
STUDENT_PUBLIC_STATUS = {
    Complaint.Status.SUBMITTED: (0, "Submitted", "Your complaint has been received."),
    Complaint.Status.UNDER_REVIEW: (1, "Under Review", "Our team is reviewing your complaint."),
    Complaint.Status.ASSIGNED: (2, "Maintenance Started", "A maintenance team has been assigned and work will begin shortly."),
    Complaint.Status.ACCEPTED: (2, "Maintenance Accepted", "The maintenance team has accepted the work."),
    Complaint.Status.REJECTED: (1, "Under Review", "The assigned team could not take up this request; it is being reassigned."),
    Complaint.Status.UNDER_INSPECTION: (3, "In Progress", "The maintenance team is inspecting the reported issue."),
    Complaint.Status.ACTION_REQUIRED: (3, "Awaiting Resources", "Work is paused while the required resources are being arranged."),
    Complaint.Status.IN_PROGRESS: (3, "In Progress", "Maintenance work is in progress."),
    Complaint.Status.RESOLVED: (4, "Resolved", "Your complaint has been resolved."),
    Complaint.Status.CLOSED: (4, "Resolved", "This complaint is closed."),
}


def _student_tracker_context(complaint):
    """
    Builds a student-safe context: only public stages/updates derived from
    status values. Raw history comments, staff identities, reasons, inventory
    and request records are deliberately excluded (backend-enforced).
    """
    stage_index, public_title, _ = STUDENT_PUBLIC_STATUS.get(
        complaint.status, (1, "Under Review", "")
    )
    public_timeline = []
    for entry in complaint.history.all():
        mapped = STUDENT_PUBLIC_STATUS.get(entry.status)
        if not mapped:
            continue
        entry_stage, entry_title, entry_update = mapped
        public_timeline.append(
            {
                "stage": entry_stage,
                "title": entry_title,
                "update": entry_update,
                "timestamp": entry.timestamp,
            }
        )
    return {
        "complaint": complaint,
        "public_title": public_title,
        "stage_index": stage_index,
        "stages": STUDENT_TRACKER_STAGES,
        "public_timeline": public_timeline,
        "is_resolved": complaint.status in (Complaint.Status.RESOLVED, Complaint.Status.CLOSED),
    }


def _resolved_guard(request, complaint):
    """
    Rejects modifying maintenance actions on Resolved complaints.
    Returns a redirect response for refused POSTs, else None.
    Details and history stay readable; only modifications are refused.
    """
    if complaint.status == Complaint.Status.RESOLVED and request.method == "POST":
        messages.error(
            request,
            "This complaint is Resolved. Maintenance work is completed and no further action is available.",
        )
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)
    return None


@login_required
def complaint_create(request):
    """View for students to raise a new complaint."""
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
        # Students can ONLY view their own submitted complaints
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

    # Authorization check: Students can only view their own complaints
    if not (is_admin or is_staff):
        if complaint.user != user:
            raise PermissionDenied("You are not authorized to view this complaint.")
        # Students get a dedicated tracker with backend-filtered public data only.
        # Internal forms, history, resources and requests are never passed along.
        return render(
            request,
            "complaints/complaint_detail_student.html",
            _student_tracker_context(complaint),
        )

    usage_form = DirectInventoryUsageForm()
    request_form = MaintenanceRequestForm()
    assign_form = ComplaintAssignForm(instance=complaint)
    inspect_form = MaintenanceInspectionForm(instance=complaint)

    context = {
        "complaint": complaint,
        "is_admin": is_admin,
        "is_staff": is_staff,
        "is_administrator": user.is_admin_user,
        "is_assignee": complaint.assigned_to_id is not None and complaint.assigned_to_id == user.pk,
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
    if not (user.role == User.Role.MAINTENANCE):
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
    if not user.is_admin_user:
        raise PermissionDenied("Only Administrators can access complaint management.")

    unassigned_complaints = Complaint.objects.select_related("user", "asset").filter(assigned_to__isnull=True)
    pending_requests = MaintenanceRequest.objects.select_related("complaint", "requested_by", "inventory_item").filter(status="PENDING")
    all_complaints_queryset = Complaint.objects.select_related(
        "user", "asset", "assigned_to", "location_record"
    ).order_by("-created_at")
    all_complaints_paginator = Paginator(all_complaints_queryset, 25)
    all_complaints_page = all_complaints_paginator.get_page(request.GET.get("page"))

    context = {
        "unassigned_complaints": unassigned_complaints,
        "pending_requests": pending_requests,
        "all_complaints": all_complaints_page.object_list,
        "all_complaints_page": all_complaints_page,
        "all_complaints_count": all_complaints_paginator.count,
    }
    return render(request, "complaints/admin_complaint_manage.html", context)


@login_required
def staff_by_specialization(request):
    """JSON endpoint for specialization-first assignment: only staff of the given specialization."""
    user = request.user
    if not user.is_admin_user:
        raise PermissionDenied("Only Administrators can assign staff.")
    specialization = (request.GET.get("specialization") or "").strip()
    valid = {choice[0] for choice in User.Specialization.choices}
    if specialization not in valid:
        return JsonResponse({"staff": []})
    qs = (
        User.objects.filter(Q(role=User.Role.MAINTENANCE) | Q(is_staff=True))
        .filter(is_available=True, specialization=specialization)
        .order_by("name", "username")
        .values("id", "username", "name", "specialization")
    )
    return JsonResponse({"staff": list(qs)})


@login_required
def admin_assign_staff(request, complaint_id):
    """Administrator assigns or reassigns an available Maintenance Staff member (specialization-first)."""
    user = request.user
    if not user.is_admin_user:
        raise PermissionDenied("Only Administrators can assign staff.")

    complaint = get_object_or_404(
        Complaint.objects.select_related("assigned_to"), complaint_id=complaint_id
    )
    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response
    previous_staff = complaint.assigned_to
    previous_staff_id = complaint.assigned_to_id
    previous_name = (
        (previous_staff.name or previous_staff.username) if previous_staff else None
    )
    if request.method == "POST":
        form = ComplaintAssignForm(request.POST, instance=complaint)
        if form.is_valid():
            updated = form.save(commit=False)
            new_staff = updated.assigned_to
            is_reassignment = (
                previous_staff_id is not None
                and new_staff is not None
                and previous_staff_id != new_staff.pk
            )
            is_first_assignment = previous_staff_id is None and new_staff is not None
            updated.assigned_at = timezone.now()
            if is_first_assignment or is_reassignment:
                # (Re)assignment replaces the active assignment: status becomes Assigned.
                updated.status = Complaint.Status.ASSIGNED
            elif updated.status in (Complaint.Status.SUBMITTED, Complaint.Status.UNDER_REVIEW):
                updated.status = Complaint.Status.ASSIGNED
            # A fresh assignment starts a new cycle: clear any previous rejection
            # reason. The rejection event itself stays preserved in history.
            updated.rejection_reason = ""
            updated.save()

            staff_name = (new_staff.name or new_staff.username) if new_staff else "Staff"
            if is_reassignment:
                spec = (new_staff.specialization or "").strip() if new_staff else ""
                updated.log_history(
                    status=updated.status,
                    changed_by=request.user,
                    comment=(
                        f"Reassigned from {previous_name} to Maintenance Staff member "
                        f"{staff_name}" + (f" ({spec})." if spec else ".")
                    ),
                )
                messages.success(
                    request,
                    f"Reassigned complaint {complaint.complaint_id} from {previous_name} to {staff_name}.",
                )
            else:
                updated.log_history(
                    status=updated.status,
                    changed_by=request.user,
                    comment=f"Assigned to Maintenance Staff member {staff_name}.",
                )
                messages.success(request, f"Assigned Maintenance Staff member {staff_name} to complaint {complaint.complaint_id}.")
            if new_staff is not None and (is_first_assignment or is_reassignment):
                # Backend notification for the newly assigned staff member only.
                notify_type = (
                    Notification.NotificationType.REASSIGNMENT
                    if is_reassignment
                    else Notification.NotificationType.ASSIGNMENT
                )
                action_word = "Reassigned" if is_reassignment else "Assigned"
                Notification.notify(
                    recipient=new_staff,
                    notification_type=notify_type,
                    title=f"{action_word} maintenance request: {updated.complaint_id}",
                    message=(
                        f"You have been assigned to complaint {updated.complaint_id}: "
                        f"{updated.title} ({updated.get_category_display()}, "
                        f"{updated.display_location}, Priority: {updated.get_priority_display()})."
                    ),
                    link=reverse(
                        "complaints:detail", kwargs={"complaint_id": updated.complaint_id}
                    ),
                )
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}" if field != "__all__" else str(error))
    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_accept(request, complaint_id):
    """Currently assigned Maintenance Staff member accepts the assignment (Assigned -> Accepted)."""
    user = request.user
    if not (user.role == User.Role.MAINTENANCE):
        raise PermissionDenied("Only Maintenance Staff can accept assignments.")

    complaint = get_object_or_404(
        Complaint.objects.select_related("assigned_to"), complaint_id=complaint_id
    )
    if complaint.assigned_to_id != user.pk:
        raise PermissionDenied("Only the currently assigned Maintenance Staff member can accept this complaint.")

    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response

    if request.method != "POST":
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    if complaint.status == Complaint.Status.ACCEPTED:
        messages.info(request, "This assignment has already been accepted.")
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    if complaint.status != Complaint.Status.ASSIGNED:
        messages.error(request, "Only complaints with 'Assigned' status can be accepted.")
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    complaint.status = Complaint.Status.ACCEPTED
    complaint.save(update_fields=["status", "updated_at"])
    staff_name = user.name or user.username
    complaint.log_history(
        status=Complaint.Status.ACCEPTED,
        changed_by=user,
        comment=f"Assignment accepted by Maintenance Staff member {staff_name}.",
    )
    messages.success(request, f"Assignment for complaint {complaint.complaint_id} accepted.")
    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_reject(request, complaint_id):
    """Currently assigned Maintenance Staff member rejects the assignment with a reason."""
    user = request.user
    if not (user.role == User.Role.MAINTENANCE):
        raise PermissionDenied("Only Maintenance Staff can reject assignments.")

    complaint = get_object_or_404(
        Complaint.objects.select_related("assigned_to"), complaint_id=complaint_id
    )
    if complaint.assigned_to_id != user.pk:
        raise PermissionDenied("Only the currently assigned Maintenance Staff member can reject this complaint.")

    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response

    if request.method != "POST":
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    if complaint.status == Complaint.Status.REJECTED:
        messages.info(request, "This assignment has already been rejected.")
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    if complaint.status not in (Complaint.Status.ASSIGNED, Complaint.Status.ACCEPTED):
        messages.error(request, "Only complaints with 'Assigned' or 'Accepted' status can be rejected.")
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    form = MaintenanceRejectionForm(request.POST)
    if not form.is_valid():
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}" if field != "__all__" else str(error))
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    reason = form.cleaned_data["reason"]
    staff_name = user.name or user.username
    complaint.status = Complaint.Status.REJECTED
    complaint.rejection_reason = reason
    # Release the assignment so the Administrator can assign new staff
    # specialization-first; the rejection event stays preserved in history.
    complaint.assigned_to = None
    complaint.save(update_fields=["status", "rejection_reason", "assigned_to", "updated_at"])
    complaint.log_history(
        status=Complaint.Status.REJECTED,
        changed_by=user,
        comment=f"Assignment rejected by Maintenance Staff member {staff_name}. Reason: {reason}",
    )
    messages.success(request, f"Assignment for complaint {complaint.complaint_id} rejected.")
    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


@login_required
def maintenance_inspect(request, complaint_id):
    """Maintenance Staff records inspection findings and updates operational progress."""
    user = request.user
    if not (user.role == User.Role.MAINTENANCE):
        raise PermissionDenied("Only Maintenance Staff can update inspection progress.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response
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
    if not (user.role == User.Role.MAINTENANCE):
        raise PermissionDenied("Only Maintenance Staff can issue inventory for maintenance.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response
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
    if not (user.role == User.Role.MAINTENANCE):
        raise PermissionDenied("Only Maintenance Staff can submit resource/asset action requests.")

    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    resolved_response = _resolved_guard(request, complaint)
    if resolved_response is not None:
        return resolved_response
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
    if not user.is_admin_user:
        raise PermissionDenied("Only Administrators can decide on maintenance requests.")

    req = get_object_or_404(MaintenanceRequest.objects.select_related("complaint", "inventory_item", "requested_by"), pk=request_id)
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
            if req.requested_by is not None:
                # Backend notification for the staff member who raised the request.
                decision_word = decision.get_status_display()
                if decision.status == MaintenanceRequest.Status.APPROVED:
                    notify_type = Notification.NotificationType.REQUEST_APPROVED
                elif decision.status == MaintenanceRequest.Status.REJECTED:
                    notify_type = Notification.NotificationType.REQUEST_REJECTED
                else:
                    notify_type = Notification.NotificationType.REQUEST_MORE_INFO
                Notification.notify(
                    recipient=req.requested_by,
                    notification_type=notify_type,
                    title=f"Resource request {decision_word}: {complaint.complaint_id}",
                    message=(
                        f"Your {req.get_request_type_display()} request for complaint "
                        f"{complaint.complaint_id} was {decision_word}."
                        + (f" Admin notes: {decision.admin_notes}" if decision.admin_notes else "")
                    ),
                    link=reverse(
                        "complaints:detail", kwargs={"complaint_id": complaint.complaint_id}
                    ),
                )
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("complaints:detail", complaint_id=complaint.complaint_id)


# Backward compatibility aliases
complaint_status_update = maintenance_inspect
complaint_add_resource = maintenance_use_inventory



