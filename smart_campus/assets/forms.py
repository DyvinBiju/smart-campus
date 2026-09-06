from django import forms
from .models import Asset


class AssetForm(forms.ModelForm):
    """
    Form for adding and editing campus assets.
    Provides styled Bootstrap 5 widgets and placeholders.
    """

    asset_code = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. AST-0001 (Leave blank to auto-generate)",
            }
        ),
        help_text="Unique asset identifier. Auto-generated if left blank.",
    )

    class Meta:
        model = Asset
        fields = [
            "asset_code",
            "name",
            "category",
            "building",
            "room",
            "status",
            "purchase_date",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Dell OptiPlex Desktop PC",
                }
            ),
            "category": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "building": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Academic Block A, Library, Main Building",
                }
            ),
            "room": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Room 204, Computer Lab 3 (Optional)",
                }
            ),
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "purchase_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter any additional details, specifications, or serial numbers...",
                }
            ),
        }