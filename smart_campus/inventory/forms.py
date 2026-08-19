from django import forms

from .models import InventoryCategory, InventoryItem


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "description"]


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "category",
            "quantity",
            "minimum_quantity",
            "unit",
            "description",
        ]

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")

        if quantity is not None and quantity < 0:
            raise forms.ValidationError(
                "Quantity cannot be negative."
            )

        return quantity

    def clean_minimum_quantity(self):
        minimum_quantity = self.cleaned_data.get("minimum_quantity")

        if minimum_quantity is not None and minimum_quantity < 0:
            raise forms.ValidationError(
                "Minimum quantity cannot be negative."
            )

        return minimum_quantity