from django import forms
from .models import Complaint


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["title", "category", "location", "priority", "description"]
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


class ComplaintStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ["status"]
        widgets = {
            "status": forms.Select(
                attrs={
                    "class": "form-select",
                    "required": True,
                }
            ),
        }
