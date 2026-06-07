from django import forms

from .models import TrackedProduct, WatchSource


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


class TrackedProductForm(forms.ModelForm):
    class Meta:
        model = TrackedProduct
        fields = ["name", "aliases", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "aliases": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": '["商品名の別表記", "略称"]',
                }
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
