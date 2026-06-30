from django import forms
from .models import Document
from accounts.models import User

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['user', 'title', 'file', 'document_type']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'document_type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('requesting_user', None)
        super().__init__(*args, **kwargs)

        if requesting_user and not requesting_user.is_superuser:
            if requesting_user.company:
                self.fields['user'].queryset = User.objects.filter(company=requesting_user.company).order_by('username')
            else:
                self.fields['user'].queryset = User.objects.none()

from resort.models import Resort

class DocumentFilterForm(forms.Form):
    name = forms.CharField(label="Nome Dipendente", required=False, widget=forms.TextInput(attrs={'placeholder': 'Cerca per nome...'}))
    resort = forms.ModelChoiceField(queryset=Resort.objects.all(), label="Struttura", required=False)
    role = forms.ChoiceField(label="Ruolo", required=False, choices=[('', 'Tutti i ruoli')] + User.ROLE_CHOICES)
