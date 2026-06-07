from django import forms

from .models import WatchSource


class WatchSourceForm(forms.ModelForm):
    class Meta:
        model = WatchSource
        fields = ["name", "url", "source_type", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://example.com/rss"}),
            "source_type": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
