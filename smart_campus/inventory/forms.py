from django import forms
from .models import InventoryCategory, InventoryItem, StockTransaction


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. IT Consumables"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "category",
            "quantity",
            "minimum_quantity",
            "unit",
            "storage_location",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. A4 Paper Reams, HP Toner #05A"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "minimum_quantity": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "unit": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. reams, pieces, cartridges, boxes"}),
            "storage_location": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Central Store Room 102"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Item specifications, part numbers, etc."}),
        }

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