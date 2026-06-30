from django import forms
from .models import Procedure, Sector

class ProcedureForm(forms.ModelForm):
    """
    Form for creating and updating Procedure objects.
    The logic for versioning and assigning the user is handled in the view.
    """
    class Meta:
        model = Procedure
        fields = ['title', 'file', 'sectors']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'sectors': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order sectors alphabetically in the form for consistency
        self.fields['sectors'].queryset = Sector.objects.order_by('name')
