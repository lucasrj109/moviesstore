from django import forms
from .models import Petition

class PetitionCreateForm(forms.ModelForm):
    class Meta:
        model = Petition
        fields = ['title', 'director', 'year', 'description', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'year': forms.NumberInput(attrs={'min': 1800, 'max': 9999}),
        }
