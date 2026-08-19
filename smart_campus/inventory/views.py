from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import InventoryItemForm
from .models import InventoryCategory, InventoryItem


def inventory_list(request):
    items = InventoryItem.objects.select_related("category")

    search = request.GET.get("search", "").strip()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")

    if search:
        items = items.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
        )

    if category:
        items = items.filter(category_id=category)

    if status == "available":
        items = [
            item for item in items
            if item.stock_status == "Available"
        ]
    elif status == "low":
        items = [
            item for item in items
            if item.stock_status == "Low Stock"
        ]
    elif status == "out":
        items = [
            item for item in items
            if item.stock_status == "Out of Stock"
        ]

    categories = InventoryCategory.objects.all()

    context = {
        "items": items,
        "categories": categories,
        "search": search,
        "selected_category": category,
        "selected_status": status,
    }

    return render(
        request,
        "inventory/inventory_list.html",
        context,
    )


def inventory_create(request):
    if request.method == "POST":
        form = InventoryItemForm(request.POST)

        if form.is_valid():
            item = form.save()
            return redirect("inventory:detail", pk=item.pk)
    else:
        form = InventoryItemForm()

    return render(
        request,
        "inventory/inventory_form.html",
        {"form": form},
    )


def inventory_detail(request, pk):
    item = get_object_or_404(
        InventoryItem.objects.select_related("category"),
        pk=pk,
    )

    return render(
        request,
        "inventory/inventory_detail.html",
        {"item": item},
    )


def inventory_update(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        form = InventoryItemForm(request.POST, instance=item)

        if form.is_valid():
            form.save()
            return redirect("inventory:detail", pk=item.pk)
    else:
        form = InventoryItemForm(instance=item)

    return render(
        request,
        "inventory/inventory_form.html",
        {
            "form": form,
            "item": item,
        },
    )


def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)

    if request.method == "POST":
        item.delete()
        return redirect("inventory:list")

    return render(
        request,
        "inventory/inventory_confirm_delete.html",
        {"item": item},
    )