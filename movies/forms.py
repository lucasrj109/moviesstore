from django import forms
from .models import CheckoutExperienceReview

class CheckoutExperienceReviewForm(forms.ModelForm):
    class Meta:
        model = CheckoutExperienceReview
        fields = ['name', 'is_anonymous', 'review_text']
        widgets = {
            'review_text': forms.Textarea(attrs={'rows': 4}),
        }
