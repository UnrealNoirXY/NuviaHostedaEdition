from django import forms
from django.forms import inlineformset_factory
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, PurchaseCategory
from resort.models import Resort
from accounts.models import User


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['resort', 'supplier', 'category', 'status']
        widgets = {
            'resort': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser and user.role not in [User.ADMINISTRATIVE]:
            if user.company:
                self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
                self.fields['supplier'].queryset = Supplier.objects.filter(company=user.company)
            else:
                # If user has no company, they can't select any resort or supplier
                self.fields['resort'].queryset = Resort.objects.none()
                self.fields['supplier'].queryset = Supplier.objects.none()

        if not self.instance.pk:
            # For new instances, status is not user-editable, it defaults to 'draft'
            del self.fields['status']


class PurchaseOrderFilterForm(forms.Form):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.all(),
        required=False,
        label="Fornitore",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    resort = forms.ModelChoiceField(
        queryset=Resort.objects.all(),
        required=False,
        label="Resort",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        label="Data Inizio",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        required=False,
        label="Data Fine",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser and user.role not in [User.ADMINISTRATIVE]:
            if user.company:
                self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
                self.fields['supplier'].queryset = Supplier.objects.filter(company=user.company)
            else:
                self.fields['resort'].queryset = Resort.objects.none()
                self.fields['supplier'].queryset = Supplier.objects.none()

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    fields=('product_name', 'product_code', 'quantity', 'unit_price'),
    extra=1,
    can_delete=True,
    widgets={
        'product_name': forms.TextInput(attrs={'class': 'form-control'}),
        'product_code': forms.TextInput(attrs={'class': 'form-control'}),
        'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        'unit_price': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)
