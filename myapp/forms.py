from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

from .models import FraudComplaint, Property, PropertyRating, ServiceFeedback


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class PropertyForm(forms.ModelForm):
    class Meta:
        model = Property
        fields = [
            "property_type",
            "title",
            "description",
            "location",
            "area_sqft",
            "price",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["property_type"].widget.attrs["class"] = "form-select"

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= 0:
            raise forms.ValidationError("Price must be greater than 0.")
        return price


class PropertySearchForm(forms.Form):
    location = forms.CharField(required=False, max_length=200)
    property_type = forms.ChoiceField(
        required=False,
        choices=[("", "All types")] + Property.PROPERTY_TYPE_CHOICES,
    )
    min_price = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=12)
    max_price = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].widget.attrs["class"] = "form-control"
        self.fields["location"].widget.attrs["placeholder"] = "Enter location"
        self.fields["property_type"].widget.attrs["class"] = "form-select"
        self.fields["min_price"].widget.attrs["class"] = "form-control"
        self.fields["max_price"].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")

        if min_price is not None and max_price is not None and min_price > max_price:
            raise forms.ValidationError("Min price cannot be greater than max price.")
        return cleaned_data


class RecommendationForm(forms.Form):
    budget = forms.DecimalField(required=False, min_value=0, decimal_places=2, max_digits=12)
    location = forms.CharField(required=False, max_length=200)
    property_type = forms.ChoiceField(
        required=False,
        choices=[("", "All types")] + Property.PROPERTY_TYPE_CHOICES,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["budget"].widget.attrs["class"] = "form-control"
        self.fields["location"].widget.attrs["class"] = "form-control"
        self.fields["location"].widget.attrs["placeholder"] = "Preferred location"
        self.fields["property_type"].widget.attrs["class"] = "form-select"


class FraudComplaintForm(forms.Form):
    property_id = forms.IntegerField(min_value=1)
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_id"].widget.attrs["class"] = "form-control"
        self.fields["property_id"].widget.attrs["placeholder"] = "Enter property ID"
        self.fields["reason"].widget.attrs["class"] = "form-control"
        self.fields["reason"].widget.attrs["placeholder"] = "Explain why this property seems fraudulent"

    def clean_property_id(self):
        property_id = self.cleaned_data["property_id"]
        property_item = Property.objects.filter(id=property_id).first()
        if not property_item:
            raise forms.ValidationError("Property with this ID does not exist.")
        return property_id

    def save(self, reporter):
        property_item = Property.objects.get(id=self.cleaned_data["property_id"])
        return FraudComplaint.objects.create(
            reporter=reporter,
            property=property_item,
            reason=self.cleaned_data["reason"],
        )


class ServiceFeedbackForm(forms.ModelForm):
    class Meta:
        model = ServiceFeedback
        fields = ["service_rating", "feedback_text"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_rating"].widget.attrs["class"] = "form-select"
        self.fields["service_rating"].widget.choices = [(i, i) for i in range(1, 6)]
        self.fields["feedback_text"].widget.attrs["class"] = "form-control"
        self.fields["feedback_text"].widget.attrs["rows"] = 4
        self.fields["feedback_text"].widget.attrs["placeholder"] = "Share feedback about platform services"


class PropertyRatingForm(forms.Form):
    property_id = forms.IntegerField(min_value=1)
    rating = forms.ChoiceField(choices=[(i, i) for i in range(1, 6)])
    feedback_text = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property_id"].widget.attrs["class"] = "form-control"
        self.fields["property_id"].widget.attrs["placeholder"] = "Enter property ID"
        self.fields["rating"].widget.attrs["class"] = "form-select"
        self.fields["feedback_text"].widget.attrs["class"] = "form-control"
        self.fields["feedback_text"].widget.attrs["placeholder"] = "Optional comment for this property"

    def clean_property_id(self):
        property_id = self.cleaned_data["property_id"]
        if not Property.objects.filter(id=property_id).exists():
            raise forms.ValidationError("Property with this ID does not exist.")
        return property_id

    def save(self, user):
        property_item = Property.objects.get(id=self.cleaned_data["property_id"])
        rating_value = int(self.cleaned_data["rating"])
        feedback_text = self.cleaned_data.get("feedback_text", "")
        rating_obj, _ = PropertyRating.objects.update_or_create(
            user=user,
            property=property_item,
            defaults={"rating": rating_value, "feedback_text": feedback_text},
        )
        return rating_obj
