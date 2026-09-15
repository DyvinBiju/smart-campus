from django import forms
from .models import Asset, Location


def _strip_required(value, field_name):
    text = (value or "").strip()
    if not text:
        raise forms.ValidationError(f"{field_name} cannot be blank.")
    return text


class LocationForm(forms.ModelForm):
    """
    Form for adding and editing campus locations in the Admin panel.
    """

    class Meta:
        model = Location
        fields = [
            "name",
            "location_type",
            "parent",
            "description",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Computer Science Block, Computer Lab 1",
                }
            ),
            "location_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "parent": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional directions or location details...",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_name(self):
        name = _strip_required(self.cleaned_data.get("name"), "Location name")
        qs = Location.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A location with this name already exists.")
        return name

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        if self.instance and self.instance.pk and parent and parent.pk == self.instance.pk:
            raise forms.ValidationError("A location cannot be its own parent.")
        if self.instance and self.instance.pk and parent:
            current = parent
            while current is not None:
                if current.pk == self.instance.pk:
                    raise forms.ValidationError("This parent selection would create a circular location hierarchy.")
                current = current.parent
        return parent

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "-- Main Location / No Parent --"
        self.fields["parent"].queryset = Location.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(pk=self.instance.pk)


class AssetForm(forms.ModelForm):
    """
    Form for adding and editing campus assets.
    Provides styled Bootstrap 5 widgets and location binding.
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
            "location",
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
            "location": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "building": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Academic Block A, Library, Main Building (Auto-synced if Location selected)",
                }
            ),
            "room": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Room 204, Computer Lab 3 (Auto-synced if Location selected)",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].required = False
        self.fields["location"].empty_label = "-- Select Registered Campus Location --"
        self.fields["location"].queryset = Location.objects.filter(is_active=True)
        self.fields["building"].required = False