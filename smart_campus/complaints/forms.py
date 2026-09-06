from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from smart_campus.assets.models import Asset
from smart_campus.inventory.models import InventoryItem
from .models import Complaint, ComplaintResource, MaintenanceRequest

User = get_user_model()


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["title", "category", "asset", "location", "priority", "description"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Projector not working in Room 204",
                    "required": True,
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "asset": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Science Block, 2nd Floor, Lab 3",
                    "required": True,
                }
            ),
            "priority": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Provide details about the issue...",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["asset"].required = False
        self.fields["asset"].empty_label = "-- Select Affected Asset (Optional) --"
        self.fields["asset"].queryset = Asset.objects.all()


class ComplaintAssignForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["assigned_to"]
        widgets = {
            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].empty_label = "-- Select Available Staff Member --"
        # Prefer Maintenance Staff members marked as available
        staff_qs = User.objects.filter(
            Q(role=User.Role.MAINTENANCE) | Q(is_staff=True)
        ).filter(is_available=True)
        self.fields["assigned_to"].queryset = staff_qs


class MaintenanceInspectionForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["status", "inspection_notes", "resolution_notes"]
        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "inspection_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Record inspection findings, problem diagnosis, or component check...",
                }
            ),
            "resolution_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe repair actions completed or resolution details...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit staff status choices to operational choices
        allowed_statuses = [
            Complaint.Status.UNDER_INSPECTION,
            Complaint.Status.IN_PROGRESS,
            Complaint.Status.RESOLVED,
        ]
        self.fields["status"].choices = [
            (choice[0], choice[1]) for choice in Complaint.Status.choices if choice[0] in allowed_statuses
        ]


class DirectInventoryUsageForm(forms.ModelForm):
    class Meta:
        model = ComplaintResource
        fields = ["inventory_item", "quantity_used"]
        widgets = {
            "inventory_item": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "quantity_used": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "value": 1,
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only permit selecting items that are currently in stock (>0)
        self.fields["inventory_item"].queryset = InventoryItem.objects.filter(quantity__gt=0)
        self.fields["inventory_item"].empty_label = "-- Select Available Inventory Item --"

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("inventory_item")
        qty = cleaned_data.get("quantity_used")
        if item and qty:
            if qty > item.quantity:
                raise forms.ValidationError(
                    f"Requested quantity ({qty}) exceeds available stock ({item.quantity} {item.unit}) for {item.name}."
                )
        return cleaned_data


class MaintenanceRequestForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["request_type", "inventory_item", "quantity_requested", "reason"]
        widgets = {
            "request_type": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "inventory_item": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "quantity_requested": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "value": 1,
                }
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Explain why this resource or administrative action (repair/replace/retire) is required...",
                    "required": True,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["inventory_item"].required = False
        self.fields["inventory_item"].empty_label = "-- Select Inventory Item (if applicable) --"
        self.fields["inventory_item"].queryset = InventoryItem.objects.all()


class AdminDecisionForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequest
        fields = ["status", "admin_notes"]
        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "admin_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter decision rationale, purchase instructions, or notes for maintenance staff...",
                }
            ),
        }


# Backward compatibility aliases
ComplaintStatusUpdateForm = MaintenanceInspectionForm
ComplaintResourceForm = DirectInventoryUsageForm


