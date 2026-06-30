from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone

from accounts.models import User
from clients.models import Company
from resort.models import Resort
from purchase_orders.models import Budget

from .models import (
    FinancialCategory,
    FinancialPeriod,
    FinancialSnapshot,
    FinancialLineItem,
    FinancialDataSource,
    FinancialImportBatch,
)


def _apply_bootstrap(field):
    widget = field.widget
    if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
        css_class = 'form-check-input'
    elif isinstance(widget, (forms.Select, forms.DateInput, forms.DateTimeInput)):
        css_class = 'form-select'
    else:
        css_class = 'form-control'
    existing = widget.attrs.get('class', '')
    if css_class not in existing:
        widget.attrs['class'] = f"{existing} {css_class}".strip()


class FinancialDashboardFilterForm(forms.Form):
    company = forms.ModelChoiceField(queryset=Company.objects.none(), required=False, label='Società')
    resort = forms.ModelChoiceField(queryset=Resort.objects.none(), required=False, label='Struttura')
    year = forms.ChoiceField(choices=[], required=False, label='Anno')
    period_type = forms.ChoiceField(choices=FinancialPeriod.PERIOD_CHOICES, required=False, label='Periodicità')

    def __init__(self, *args, user: User, companies=None, resorts=None, years=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        companies = companies or Company.objects.none()
        resorts = resorts or Resort.objects.none()
        years = years or []

        self.fields['company'].queryset = companies
        self.fields['resort'].queryset = resorts

        year_choices = [(year, year) for year in years]
        if not year_choices:
            year_choices = [(timezone.now().year, timezone.now().year)]
        self.fields['year'].choices = year_choices
        self.fields['year'].initial = year_choices[0][0]
        self.fields['period_type'].initial = FinancialPeriod.PERIOD_MONTHLY

        for field in self.fields.values():
            _apply_bootstrap(field)


class FinancialSnapshotFilterForm(FinancialDashboardFilterForm):
    snapshot_type = forms.ChoiceField(
        choices=[('', 'Tutti')] + list(FinancialSnapshot.SNAPSHOT_TYPE_CHOICES),
        required=False,
        label='Tipologia',
    )


class FinancialPeriodForm(forms.ModelForm):
    class Meta:
        model = FinancialPeriod
        fields = ['company', 'resort', 'period_type', 'year', 'month', 'start_date', 'end_date', 'is_locked']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, user: User, companies=None, **kwargs):
        super().__init__(*args, **kwargs)
        companies = companies or Company.objects.none()
        self.fields['company'].queryset = companies
        if user.is_superuser or getattr(user, 'role', None) == User.SUPERADMIN:
            resort_qs = Resort.objects.all()
        elif user.company_id:
            resort_qs = Resort.objects.filter(company=user.company)
        else:
            resort_qs = Resort.objects.none()
        self.fields['resort'].queryset = resort_qs

        for field in self.fields.values():
            _apply_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        period_type = cleaned_data.get('period_type')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')

        if period_type == FinancialPeriod.PERIOD_MONTHLY and not month:
            raise forms.ValidationError('Seleziona il mese per un periodo mensile.')
        if period_type == FinancialPeriod.PERIOD_QUARTERLY:
            if not month:
                raise forms.ValidationError('Specifica il mese di riferimento (primo mese del trimestre).')
            cleaned_data['month'] = ((int(month) - 1) // 3) * 3 + 1
        if period_type == FinancialPeriod.PERIOD_YEARLY:
            cleaned_data['month'] = None

        if year and year < 2000:
            raise forms.ValidationError('Indica un anno valido (>=2000).')

        return cleaned_data


class FinancialSnapshotForm(forms.ModelForm):
    recalculate_totals = forms.BooleanField(
        required=False,
        initial=True,
        label='Ricalcola automaticamente i totali dai dettagli',
    )

    class Meta:
        model = FinancialSnapshot
        fields = [
            'period',
            'snapshot_type',
            'total_revenue',
            'total_costs',
            'currency',
            'notes',
            'data_source',
            'import_batch',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user: User, companies=None, **kwargs):
        super().__init__(*args, **kwargs)
        companies = companies or Company.objects.none()
        period_qs = FinancialPeriod.objects.filter(company__in=companies)
        if user.role == User.DIRECTOR and user.company_id:
            period_qs = period_qs.filter(company=user.company)
        if user.role == User.DIRECTOR and user.resort_id:
            period_qs = period_qs.filter(Q(resort=user.resort) | Q(resort__isnull=True))
        self.fields['period'].queryset = period_qs.order_by('-year', '-month')

        data_source_qs = FinancialDataSource.objects.filter(Q(company__in=companies) | Q(company__isnull=True))
        self.fields['data_source'].queryset = data_source_qs

        batch_qs = FinancialImportBatch.objects.filter(
            Q(data_source__in=data_source_qs) | Q(data_source__isnull=True)
        )
        self.fields['import_batch'].queryset = batch_qs

        for field in self.fields.values():
            _apply_bootstrap(field)

    def clean_period(self):
        period = self.cleaned_data['period']
        if period.is_locked and not self.instance.pk:
            raise forms.ValidationError('Il periodo è bloccato e non può essere modificato.')
        return period


class FinancialLineItemForm(forms.ModelForm):
    class Meta:
        model = FinancialLineItem
        fields = ['category', 'line_type', 'description', 'amount', 'cost_center', 'budget']
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Voce di dettaglio'}),
        }

    def __init__(self, *args, user: User, companies=None, **kwargs):
        super().__init__(*args, **kwargs)
        companies = companies or Company.objects.none()
        company_filter = Q(company__in=companies) | Q(company__isnull=True)
        self.fields['category'].queryset = FinancialCategory.objects.filter(company_filter, is_active=True).order_by('name')
        self.fields['cost_center'].queryset = self.fields['cost_center'].queryset.filter(company__in=companies).order_by('code')
        budget_filter = Q(resort__company__in=companies)
        self.fields['budget'].queryset = Budget.objects.filter(budget_filter).order_by('-year', '-month')

        if not self.instance.pk and self.initial.get('category') and not self.initial.get('line_type'):
            try:
                category = FinancialCategory.objects.get(pk=self.initial['category'])
                self.fields['line_type'].initial = category.category_type
            except FinancialCategory.DoesNotExist:
                pass

        for field in self.fields.values():
            if field.widget.input_type == 'checkbox':
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                _apply_bootstrap(field)

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        line_type = cleaned_data.get('line_type')
        if category and category.category_type != line_type:
            self.add_error('line_type', 'Il tipo di voce deve corrispondere alla categoria selezionata.')
        return cleaned_data


class BaseFinancialLineItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, user: User, companies=None, **kwargs):
        self.user = user
        self.companies = companies or Company.objects.none()
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['user'] = self.user
        kwargs['companies'] = self.companies
        return super()._construct_form(i, **kwargs)


FinancialLineItemFormSet = inlineformset_factory(
    FinancialSnapshot,
    FinancialLineItem,
    form=FinancialLineItemForm,
    formset=BaseFinancialLineItemFormSet,
    extra=2,
    can_delete=True,
)
