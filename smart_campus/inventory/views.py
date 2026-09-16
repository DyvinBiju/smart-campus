from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import models
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InventoryItemForm, StockTransactionForm, StorageLocationForm
from .models import InventoryCategory, InventoryItem, StockTransaction, StorageLocation


def admin_required(view_func):
    """
    Decorator enforcing that only Admin Users (or Django superusers/staff)
    can manage inventory items and process stock transactions.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in with administrator credentials.")
            return redirect("account_login")
        is_admin = getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
        if not is_admin:
            messages.error(request, "Access denied. Only administrators have permission to perform inventory management operations.")
            return redirect("inventory:list")
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def inventory_list(request):
    is_admin = request.user.is_authenticated and (
        getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
    )
    is_maint = request.user.is_authenticated and getattr(request.user, "is_maintenance_staff", False)

    if not is_admin and not is_maint:
        raise PermissionDenied("Access denied. Inventory records are restricted to Administrators and Maintenance Staff.")

    items = InventoryItem.objects.select_related("category", "location").all()

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    location_id = request.GET.get("location", "")
    status = request.GET.get("status", "")

    if search:
        items = items.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(storage_location__icontains=search)
            | Q(location__name__icontains=search)
            | Q(location__code__icontains=search)
        )

    if category:
        items = items.filter(category_id=category)

    if location_id and location_id.isdigit():
        items = items.filter(location_id=int(location_id))

    if status in ["available", "in_stock"]:
        items = [item for item in items if item.stock_status == "In Stock"]
    elif status == "low":
        items = [item for item in items if item.stock_status == "Low Stock"]
    elif status == "out":
        items = [item for item in items if item.stock_status == "Out of Stock"]

    categories = InventoryCategory.objects.all()
    storage_locations = StorageLocation.objects.filter(is_active=True)

    context = {
        "items": items,
        "categories": categories,
        "storage_locations": storage_locations,
        "search": search,
        "selected_category": category,
        "selected_location": location_id,
        "selected_status": status,
        "is_admin": is_admin,
        "is_maintenance_staff": is_maint,
    }

    return render(
        request,
        "inventory/inventory_list.html",
        context,
    )


@login_required
def inventory_detail(request, pk):
    is_admin = request.user.is_authenticated and (
        getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
    )
    is_maint = request.user.is_authenticated and getattr(request.user, "is_maintenance_staff", False)

    if not is_admin and not is_maint:
        raise PermissionDenied("Access denied. You are not authorized to view inventory item details.")

    item = get_object_or_404(
        InventoryItem.objects.select_related("category"),
        pk=pk,
    )
    transactions = item.transactions.select_related("asset", "created_by").all()[:20]

    # Active complaints assigned to maintenance staff for quick usage selection
    from smart_campus.complaints.models import Complaint
    assigned_complaints = []
    if is_maint or is_admin:
        assigned_complaints = Complaint.objects.filter(
            assigned_to=request.user
        ).exclude(status__in=["Resolved", "Closed"])

    return render(
        request,
        "inventory/inventory_detail.html",
        {
            "item": item,
            "transactions": transactions,
            "is_admin": is_admin,
            "is_maintenance_staff": is_maint,
            "assigned_complaints": assigned_complaints,
        },
    )



@admin_required
def inventory_create(request):
    if request.method == "POST":
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f"Inventory item '{item.name}' created successfully.")
            return redirect("inventory:detail", pk=item.pk)
    else:
        form = InventoryItemForm()

    return render(
        request,
        "inventory/inventory_form.html",
        {"form": form, "page_title": "Add Inventory Item"},
    )


@admin_required
def inventory_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Inventory item '{item.name}' updated successfully.")
            return redirect("inventory:detail", pk=item.pk)
    else:
        form = InventoryItemForm(instance=item)

    return render(
        request,
        "inventory/inventory_form.html",
        {
            "form": form,
            "item": item,
            "page_title": f"Edit Item: {item.name}",
        },
    )


@admin_required
def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        item_name = item.name
        item.delete()
        messages.success(request, f"Inventory item '{item_name}' deleted successfully.")
        return redirect("inventory:list")

    return render(
        request,
        "inventory/inventory_confirm_delete.html",
        {"item": item},
    )


@admin_required
def stock_transaction_create(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        form = StockTransactionForm(request.POST, item=item)
        if form.is_valid():
            try:
                transaction = form.save(commit=False)
                transaction.item = item
                if request.user.is_authenticated:
                    transaction.created_by = request.user
                transaction.save()

                messages.success(
                    request,
                    f"Successfully processed {transaction.get_transaction_type_display()} of {transaction.quantity} {item.unit}."
                )
                return redirect("inventory:detail", pk=item.pk)
            except ValidationError as e:
                form.add_error(None, e)
    else:
        form = StockTransactionForm(item=item)

    return render(
        request,
        "inventory/stock_transaction_form.html",
        {
            "form": form,
            "item": item,
        },
    )


@login_required
def category_list(request):
    is_admin = request.user.is_authenticated and (
        getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
    )
    is_maint = request.user.is_authenticated and getattr(request.user, "is_maintenance_staff", False)

    if not is_admin and not is_maint:
        raise PermissionDenied("Access denied. Inventory categories are restricted to Administrators and Maintenance Staff.")

    categories = InventoryCategory.objects.annotate(
        item_count=models.Count("items")
    ).order_by("name")

    return render(
        request,
        "inventory/category_list.html",
        {
            "categories": categories,
            "is_admin": is_admin,
            "is_maintenance_staff": is_maint,
        },
    )


@admin_required
def category_create(request):
    from .forms import InventoryCategoryForm
    if request.method == "POST":
        form = InventoryCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect("inventory:category_list")
    else:
        form = InventoryCategoryForm()

    return render(
        request,
        "inventory/category_form.html",
        {"form": form, "page_title": "Add Inventory Category"},
    )


@admin_required
def category_update(request, pk):
    from .forms import InventoryCategoryForm
    category = get_object_or_404(InventoryCategory, pk=pk)
    if request.method == "POST":
        form = InventoryCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect("inventory:category_list")
    else:
        form = InventoryCategoryForm(instance=category)

    return render(
        request,
        "inventory/category_form.html",
        {"form": form, "category": category, "page_title": f"Edit Category: {category.name}"},
    )


@admin_required
def category_delete(request, pk):
    category = get_object_or_404(InventoryCategory, pk=pk)
    if request.method == "POST":
        if category.items.exists():
            messages.error(
                request,
                f"Cannot delete category '{category.name}' because it contains active inventory items. Reassign or delete the items first."
            )
            return redirect("inventory:category_list")
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted successfully.")
        return redirect("inventory:category_list")

    return render(
        request,
        "inventory/category_confirm_delete.html",
        {"category": category},
    )


@login_required
def inventory_use_for_complaint(request, pk):
    """
    Allows Maintenance Staff to record inventory resource usage against an assigned complaint.
    Reduces stock auditably via StockTransaction and logs ComplaintResource.
    """
    is_maint = getattr(request.user, "is_maintenance_staff", False) or getattr(request.user, "is_admin_user", False)
    if not is_maint:
        raise PermissionDenied("Only Maintenance Staff can record resource usage.")

    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        from smart_campus.complaints.models import Complaint, ComplaintResource

        complaint_pk = request.POST.get("complaint_id")
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            messages.error(request, "Enter a valid quantity (a whole number of at least 1).")
            return redirect("inventory:detail", pk=item.pk)

        if quantity < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect("inventory:detail", pk=item.pk)

        complaint = get_object_or_404(Complaint, pk=complaint_pk)

        # Ensure complaint is assigned to staff or user is admin
        if complaint.assigned_to != request.user and not getattr(request.user, "is_admin_user", False) and not request.user.is_superuser:
            raise PermissionDenied("You can only use inventory for complaints assigned to you.")

        # Check stock availability
        if item.quantity < quantity or item.quantity == 0:
            messages.error(
                request,
                f"Insufficient stock for '{item.name}'. Requested: {quantity} {item.unit}, Available: {item.quantity} {item.unit}. Please report resource unavailable."
            )
            return redirect("inventory:detail", pk=item.pk)

        # 1. Create StockTransaction (automatically deducts item.quantity in save())
        transaction = StockTransaction(
            item=item,
            transaction_type="ISSUE",
            quantity=quantity,
            created_by=request.user,
            notes=f"Issued for complaint {complaint.complaint_id}",
        )
        transaction.save()

        # 2. Record ComplaintResource usage
        ComplaintResource.objects.create(
            complaint=complaint,
            inventory_item=item,
            quantity_used=quantity,
        )

        # 3. Log complaint lifecycle history
        complaint.log_history(
            status=complaint.status,
            changed_by=request.user,
            comment=f"Issued {quantity} {item.unit} of '{item.name}' from inventory.",
        )

        messages.success(
            request,
            f"Successfully recorded {quantity} {item.unit} of '{item.name}' used for complaint {complaint.complaint_id}."
        )
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("inventory:detail", pk=item.pk)


@login_required
def inventory_report_unavailable(request, pk):
    """
    Allows Maintenance Staff to submit an administrative MaintenanceRequest when required stock is out or low.
    """
    is_maint = getattr(request.user, "is_maintenance_staff", False) or getattr(request.user, "is_admin_user", False)
    if not is_maint:
        raise PermissionDenied("Only Maintenance Staff can report unavailable resources.")

    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        from smart_campus.complaints.models import Complaint, MaintenanceRequest

        complaint_pk = request.POST.get("complaint_id")
        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            messages.error(request, "Enter a valid quantity (a whole number of at least 1).")
            return redirect("inventory:detail", pk=item.pk)

        if quantity < 1:
            messages.error(request, "Quantity must be at least 1.")
            return redirect("inventory:detail", pk=item.pk)

        reason = request.POST.get("reason", "").strip()
        complaint = get_object_or_404(Complaint, pk=complaint_pk)

        # Create MaintenanceRequest for Admin attention
        m_req = MaintenanceRequest.objects.create(
            complaint=complaint,
            requested_by=request.user,
            request_type=MaintenanceRequest.RequestType.UNAVAILABLE_RESOURCE,
            inventory_item=item,
            quantity_requested=quantity,
            reason=reason or f"Resource '{item.name}' is unavailable/out of stock for complaint {complaint.complaint_id}.",
            status=MaintenanceRequest.Status.PENDING,
        )

        messages.success(
            request,
            f"Reported unavailable resource '{item.name}' to Administrator for complaint {complaint.complaint_id}."
        )
        return redirect("complaints:detail", complaint_id=complaint.complaint_id)

    return redirect("inventory:detail", pk=item.pk)


@login_required
def storage_location_list(request):
    is_admin = request.user.is_authenticated and (
        getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
    )
    is_maint = request.user.is_authenticated and getattr(request.user, "is_maintenance_staff", False)

    if not is_admin and not is_maint:
        raise PermissionDenied("Access denied. Storage locations are restricted to Administrators and Maintenance Staff.")

    locations = StorageLocation.objects.prefetch_related("items").all()

    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")

    if search:
        locations = locations.filter(
            Q(name__icontains=search)
            | Q(code__icontains=search)
            | Q(description__icontains=search)
        )

    if status == "active":
        locations = locations.filter(is_active=True)
    elif status == "inactive":
        locations = locations.filter(is_active=False)

    total_locations = StorageLocation.objects.count()
    active_locations = StorageLocation.objects.filter(is_active=True).count()
    inactive_locations = StorageLocation.objects.filter(is_active=False).count()

    context = {
        "locations": locations,
        "total_locations": total_locations,
        "active_locations": active_locations,
        "inactive_locations": inactive_locations,
        "search": search,
        "selected_status": status,
        "is_admin": is_admin,
        "is_maintenance_staff": is_maint,
    }

    return render(request, "inventory/storage_location_list.html", context)


@login_required
def storage_location_detail(request, pk):
    is_admin = request.user.is_authenticated and (
        getattr(request.user, "is_admin_user", False) or request.user.is_superuser or request.user.is_staff
    )
    is_maint = request.user.is_authenticated and getattr(request.user, "is_maintenance_staff", False)

    if not is_admin and not is_maint:
        raise PermissionDenied("Access denied. You are not authorized to view storage location details.")

    location = get_object_or_404(StorageLocation, pk=pk)
    stored_items = location.items.select_related("category").all()

    return render(
        request,
        "inventory/storage_location_detail.html",
        {
            "location": location,
            "stored_items": stored_items,
            "is_admin": is_admin,
            "is_maintenance_staff": is_maint,
        },
    )


@admin_required
def storage_location_create(request):
    if request.method == "POST":
        form = StorageLocationForm(request.POST)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Storage location '{loc.name}' created successfully.")
            return redirect("inventory:storage_location_list")
    else:
        form = StorageLocationForm()

    return render(
        request,
        "inventory/storage_location_form.html",
        {"form": form, "page_title": "Add Storage Location"},
    )


@admin_required
def storage_location_update(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)

    if request.method == "POST":
        form = StorageLocationForm(request.POST, instance=location)
        if form.is_valid():
            loc = form.save()
            messages.success(request, f"Storage location '{loc.name}' updated successfully.")
            return redirect("inventory:storage_location_list")
    else:
        form = StorageLocationForm(instance=location)

    return render(
        request,
        "inventory/storage_location_form.html",
        {
            "form": form,
            "location": location,
            "page_title": f"Edit Storage Location: {location.name}",
        },
    )


@admin_required
def storage_location_toggle_active(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)
    if request.method == "POST":
        location.is_active = not location.is_active
        location.save()
        status_str = "ACTIVATED" if location.is_active else "DEACTIVATED"
        messages.success(request, f"Storage location '{location.name}' has been {status_str}.")
    return redirect("inventory:storage_location_list")


@admin_required
def storage_location_delete(request, pk):
    location = get_object_or_404(StorageLocation, pk=pk)

    if request.method == "POST":
        if location.items.exists():
            messages.error(
                request,
                f"Cannot delete storage location '{location.name}' because it contains {location.item_count} active inventory item(s). Deactivate it instead to preserve audit records.",
            )
            return redirect("inventory:storage_location_list")

        loc_name = location.name
        location.delete()
        messages.success(request, f"Storage location '{loc_name}' deleted successfully.")
        return redirect("inventory:storage_location_list")

    return render(
        request,
        "inventory/storage_location_confirm_delete.html",
        {"location": location},
    )


