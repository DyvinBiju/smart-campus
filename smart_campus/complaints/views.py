from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import ComplaintForm
from .forms import ComplaintStatusUpdateForm
from .models import Complaint


def complaint_create(request):
    """View to raise a new complaint."""
    if request.method == "POST":
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            if request.user.is_authenticated:
                complaint.user = request.user
            complaint.save()
            messages.success(
                request,
                f"Complaint submitted successfully! Complaint ID: {complaint.complaint_id}",
            )
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)
    else:
        form = ComplaintForm()

    return render(request, "complaints/complaint_form.html", {"form": form})


def complaint_list(request):
    """View to list all complaints with search and filtering."""
    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "").strip()
    priority_filter = request.GET.get("priority", "").strip()
    status_filter = request.GET.get("status", "").strip()

    complaints = Complaint.objects.all()

    if search_query:
        complaints = complaints.filter(
            Q(complaint_id__icontains=search_query)
            | Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
        )

    if category_filter:
        complaints = complaints.filter(category=category_filter)

    if priority_filter:
        complaints = complaints.filter(priority=priority_filter)

    if status_filter:
        complaints = complaints.filter(status=status_filter)

    has_active_filters = bool(
        search_query or category_filter or priority_filter or status_filter
    )

    context = {
        "complaints": complaints,
        "search_query": search_query,
        "category_filter": category_filter,
        "priority_filter": priority_filter,
        "status_filter": status_filter,
        "categories": Complaint.Category.choices,
        "priorities": Complaint.Priority.choices,
        "statuses": Complaint.Status.choices,
        "has_active_filters": has_active_filters,
    }
    return render(request, "complaints/complaint_list.html", context)


def complaint_detail(request, complaint_id):
    """View to display details of a single complaint."""
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    return render(request, "complaints/complaint_detail.html", {"complaint": complaint})


def complaint_status_update(request, complaint_id):
    """View to update complaint status."""
    complaint = get_object_or_404(Complaint, complaint_id=complaint_id)
    if request.method == "POST":
        form = ComplaintStatusUpdateForm(request.POST, instance=complaint)
        if form.is_valid():
            complaint = form.save()
            messages.success(
                request,
                f"Complaint status updated successfully to '{complaint.get_status_display()}'.",
            )
            return redirect("complaints:detail", complaint_id=complaint.complaint_id)
    else:
        form = ComplaintStatusUpdateForm(instance=complaint)

    return render(
        request,
        "complaints/complaint_status_form.html",
        {"form": form, "complaint": complaint},
    )
