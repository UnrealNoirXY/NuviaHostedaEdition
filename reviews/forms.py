from django import forms
from .models import ScrapingURL, ReviewSource, ReportTemplate, ReviewAnalysis
from resort.models import Resort
from clients.models import Company

class ScrapingURLForm(forms.ModelForm):
    class Meta:
        model = ScrapingURL
        fields = ['source', 'url']
        widgets = {
            'source': forms.Select(attrs={'class': 'form-select'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.tripadvisor.com/...'}),
        }

class ScrapingTaskForm(forms.Form):
    resorts = forms.ModelMultipleChoiceField(
        queryset=Resort.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Seleziona Resorts",
        help_text="Seleziona uno o più resort per cui avviare lo scraping."
    )
    sources = forms.ModelMultipleChoiceField(
        queryset=ReviewSource.objects.filter(scraper_identifier__isnull=False).exclude(scraper_identifier__exact=''),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Seleziona Fonti",
        help_text="Scegli da quali piattaforme vuoi scaricare le recensioni."
    )
    max_reviews_booking = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'}),
        label="Numero massimo recensioni (Booking.com)",
        help_text="Lascia vuoto per scaricare tutte le recensioni."
    )
    max_reviews_google = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'}),
        label="Numero massimo recensioni (Google)",
        help_text="Lascia vuoto per scaricare tutte le recensioni."
    )
    max_reviews_tripadvisor = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'}),
        label="Numero massimo recensioni (Tripadvisor)",
        help_text="Lascia vuoto per scaricare tutte le recensioni."
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label="Data di inizio scraping (opzionale)",
        help_text="Verranno scaricate solo le recensioni più recenti di questa data. Funziona per Booking.com e Tripadvisor."
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            if user.is_superuser:
                self.fields['resorts'].queryset = Resort.objects.all().order_by('name')
            elif user.company:
                self.fields['resorts'].queryset = Resort.objects.filter(company=user.company).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        sources = cleaned_data.get('sources')
        if not sources:
            return cleaned_data

        is_booking_selected = sources.filter(name='Booking.com').exists()
        is_google_selected = sources.filter(name='Google Maps').exists()
        is_tripadvisor_selected = sources.filter(name='Tripadvisor').exists()

        if cleaned_data.get('max_reviews_booking') and not is_booking_selected:
            self.add_error('max_reviews_booking', "Questo campo è valido solo se 'Booking.com' è selezionato.")
        if cleaned_data.get('max_reviews_google') and not is_google_selected:
            self.add_error('max_reviews_google', "Questo campo è valido solo se 'Google Maps' è selezionato.")
        if cleaned_data.get('max_reviews_tripadvisor') and not is_tripadvisor_selected:
            self.add_error('max_reviews_tripadvisor', "Questo campo è valido solo se 'Tripadvisor' è selezionato.")

        if cleaned_data.get('start_date') and not (is_tripadvisor_selected or is_booking_selected):
            self.add_error('start_date', "Questo campo è valido solo se 'Tripadvisor' o 'Booking.com' è selezionato come fonte.")

        return cleaned_data

class RatingReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), label="Data Inizio")
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), label="Data Fine")
    company = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        required=False,
        label="Società",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    resort = forms.ModelChoiceField(
        queryset=Resort.objects.all(),
        required=False,
        label="Resort",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    sources = forms.ModelMultipleChoiceField(
        queryset=ReviewSource.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Piattaforme"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.is_superuser:
                pass
            elif user.role == 'owner':
                self.fields['company'].queryset = Company.objects.filter(pk=user.company.pk)
                self.fields['company'].initial = user.company
                self.fields['company'].disabled = True
                self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
            elif user.role == 'director':
                self.fields['company'].queryset = Company.objects.filter(pk=user.company.pk)
                self.fields['company'].initial = user.company
                self.fields['company'].disabled = True
                self.fields['resort'].queryset = Resort.objects.filter(pk=user.resort.pk)
                self.fields['resort'].initial = user.resort
                self.fields['resort'].disabled = True
            else:
                self.fields['company'].queryset = Company.objects.none()
                self.fields['resort'].queryset = Resort.objects.none()

class KeywordAnalysisForm(RatingReportFilterForm):
    pass

class SentimentReportFilterForm(KeywordAnalysisForm):
    pass

class PlatformPerformanceFilterForm(RatingReportFilterForm):
    pass

WIDGET_CHOICES = [
    ('full_review_list', 'Lista Completa Recensioni'),
]

class ReportTemplateForm(forms.Form):
    name = forms.CharField(label="Nome del Template", widget=forms.TextInput(attrs={'class': 'form-control'}))
    report_type = forms.ChoiceField(
        choices=ReportTemplate.REPORT_TYPE_CHOICES,
        label="Tipo di Report",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    resorts = forms.ModelMultipleChoiceField(
        queryset=Resort.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Resort Specifici"
    )
    sources = forms.ModelMultipleChoiceField(
        queryset=ReviewSource.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Piattaforme Specifiche"
    )
    sentiments = forms.MultipleChoiceField(
        choices=ReviewAnalysis.SENTIMENT_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tipi di Sentiment"
    )
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), label="Data Inizio")
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}), label="Data Fine")
    widgets = forms.MultipleChoiceField(
        choices=WIDGET_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        initial=['full_review_list'],
        label="Contenuti del Report"
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_superuser:
            self.fields['resorts'].queryset = Resort.objects.filter(company=user.company)


from django_celery_beat.models import CrontabSchedule, PeriodicTask
from .models import ScheduledScraping
import json

class ScheduledScrapingForm(forms.ModelForm):
    class Meta:
        model = ScheduledScraping
        fields = [
            'name', 'is_active', 'frequency', 'day_of_week', 'hour', 'minute',
            'resorts', 'sources', 'scrape_period_days',
            'max_reviews_booking', 'max_reviews_google', 'max_reviews_tripadvisor'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'hour': forms.Select(choices=[(i, f"{i:02d}") for i in range(24)], attrs={'class': 'form-select'}),
            'minute': forms.Select(choices=[(i, f"{i:02d}") for i in range(0, 60, 15)], attrs={'class': 'form-select'}),
            'resorts': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
            'sources': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '3'}),
            'scrape_period_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_reviews_booking': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_reviews_google': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_reviews_tripadvisor': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['hour'].initial = self.instance.hour
            self.fields['minute'].initial = self.instance.minute

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Create the CrontabSchedule
        hour = self.cleaned_data.get('hour')
        minute = self.cleaned_data.get('minute')
        frequency = self.cleaned_data.get('frequency')
        day_of_week = self.cleaned_data.get('day_of_week', '*')

        crontab, _ = CrontabSchedule.objects.get_or_create(
            minute=minute,
            hour=hour,
            day_of_month='*',
            month_of_year='*',
            day_of_week=day_of_week if frequency == ScheduledScraping.FREQUENCY_WEEKLY else '*',
        )

        if commit:
            instance.save()
            self.save_m2m()

            task_name = f"Scheduled Scraping: {instance.name} (ID: {instance.id})"
            task_args = json.dumps([instance.id])

            if instance.periodic_task:
                task = instance.periodic_task
                task.crontab = crontab
                task.name = task_name
                task.args = task_args
                task.enabled = instance.is_active
                task.save()
            else:
                new_task = PeriodicTask.objects.create(
                    crontab=crontab,
                    name=task_name,
                    task='reviews.tasks.run_scheduled_scraping',
                    args=task_args,
                    enabled=instance.is_active,
                )
                instance.periodic_task = new_task
                instance.save(update_fields=['periodic_task'])

        return instance
