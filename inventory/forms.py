from django import forms
from .models import InventoryItem, StockRecord
from resort.models import Resort
from accounts.models import User

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['resort', 'name', 'product_code', 'description', 'current_stock']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if user.role in [User.OWNER, User.CAPO_ECONOMO]:
                if user.company:
                    self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
                else:
                    self.fields['resort'].queryset = Resort.objects.none()
            elif user.role in [User.DIRECTOR, User.ECONOMO, User.MAINTAINER]:
                if user.resort:
                    self.fields['resort'].queryset = Resort.objects.filter(pk=user.resort.pk)
                else:
                    self.fields['resort'].queryset = Resort.objects.none()
            else:
                # Default to no resorts if the role doesn't have a clear scope
                self.fields['resort'].queryset = Resort.objects.none()

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockRecord
        fields = ['change', 'reason', 'notes']
        widgets = {
            'change': forms.NumberInput(attrs={'class': 'form-control'}),
            'reason': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # We only want to show manual adjustment reasons in this form
        self.fields['reason'].choices = [
            ('withdrawal', 'Prelievo/Utilizzo'),
            ('adjustment', 'Rettifica Manuale'),
            ('return', 'Reso'),
            ('initial', 'Giacenza Iniziale'),
        ]
