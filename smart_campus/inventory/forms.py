from django import forms
from django.db.models import Q
from .models import InventoryCategory, InventoryItem, StockTransaction, StorageLocation


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. IT Consumables"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Category name cannot be blank.")
        qs = InventoryCategory.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A category named '{name}' already exists.")
        return name


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. IT Equipment Store"}),
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. STORE-001"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Description or scope of store..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Storage location name cannot be blank.")
        qs = StorageLocation.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A storage location named '{name}' already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data.get("code", "").strip() if self.cleaned_data.get("code") else None
        if code:
            qs = StorageLocation.objects.filter(code__iexact=code)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"A storage location with code '{code}' already exists.")
        return code


class InventoryItemForm(forms.ModelForm):
    location = forms.ModelChoiceField(
        queryset=StorageLocation.objects.filter(is_active=True),
        required=False,
        empty_label="[ Select Storage Location ]",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Storage Location",
        help_text="Select an active inventory storage location",
    )

    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "category",
            "quantity",
            "minimum_quantity",
            "unit",
            "location",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. A4 Paper Reams, HP Toner #05A"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "minimum_quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. reams, pieces, cartridges, boxes"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Item specifications, part numbers, etc."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.location:
            self.fields["location"].queryset = StorageLocation.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.location.pk)
            )

    def clean_name(self):
        name = (self.cleaned_data.get("name") or "").strip()
        if not name:
            raise forms.ValidationError("Item name cannot be blank.")
        return name

    def clean_unit(self):
        unit = (self.cleaned_data.get("unit") or "").strip()
        if not unit:
            raise forms.ValidationError("Unit cannot be blank.")
        return unit

    def clean_location(self):
        loc = self.cleaned_data.get("location")
        if loc and not loc.is_active:
            if not (self.instance and self.instance.pk and self.instance.location == loc):
                raise forms.ValidationError(f"Storage location '{loc.name}' is inactive and cannot be selected for new inventory items.")
        return loc

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative.")
        return quantity

    def clean_minimum_quantity(self):
        minimum_quantity = self.cleaned_data.get("minimum_quantity")
        if minimum_quantity is not None and minimum_quantity < 0:
            raise forms.ValidationError("Minimum quantity cannot be negative.")
        return minimum_quantity


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = [
            "transaction_type",
            "quantity",
            "asset",
            "notes",
        ]
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "asset": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Reason for issue, maintenance activity notes, or PO number..."}),
        }

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop("item", None)
        super().__init__(*args, **kwargs)
        if self.item:
            self.fields["asset"].help_text = "Select campus asset if issuing stock for maintenance (optional)."

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get("transaction_type")
        quantity = cleaned_data.get("quantity")

        if transaction_type == "ISSUE" and self.item and quantity:
            if self.item.quantity < quantity:
                raise forms.ValidationError(
                    f"Cannot issue {quantity} {self.item.unit}. Only {self.item.quantity} {self.item.unit} available in stock!"
                )
        return cleaned_data
