from django import forms
from django.contrib.auth import get_user_model
from smart_campus.assets.models import Asset
from smart_campus.inventory.models import InventoryItem
from .models import Complaint, ComplaintResource

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


class ComplaintStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["status", "assigned_to", "resolution_notes"]
        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
            "assigned_to": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "resolution_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Describe actions taken or resolution notes...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].empty_label = "-- Unassigned --"
        self.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[User.Role.MAINTENANCE, User.Role.ADMIN]
        )


class ComplaintResourceForm(forms.ModelForm):
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
        self.fields["inventory_item"].queryset = InventoryItem.objects.filter(quantity__gt=0)
        self.fields["inventory_item"].empty_label = "-- Select Inventory Resource --"

    def clean(self):
        cleaned_data = super().clean()
        item = cleaned_data.get("inventory_item")
        qty = cleaned_data.get("quantity_used")
        if item and qty:
            if qty > item.quantity:
                raise forms.ValidationError(
                    f"Requested quantity ({qty}) exceeds available stock ({item.quantity}) for {item.name}."
                )
        return cleaned_data

