from django import forms
from .models import Competitor, ScrapingLink, ResortCompetitorAssociation

class CompetitorForm(forms.ModelForm):
    class Meta:
        model = Competitor
        fields = ['company', 'name', 'website']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        }

class ResortCompetitorAssociationForm(forms.ModelForm):
    class Meta:
        model = ResortCompetitorAssociation
        fields = ['competitor']
        widgets = {
            'competitor': forms.Select(attrs={'class': 'form-select'}),
        }

class ScrapingLinkForm(forms.ModelForm):
    # Mimicking the fields from the reviews app's ScrapingTaskForm
    max_reviews_booking = forms.IntegerField(
        required=False, label="Max Recensioni (Booking)",
        help_text="Solo per fonti Booking.com",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'})
    )
    max_reviews_google = forms.IntegerField(
        required=False, label="Max Recensioni (Google)",
        help_text="Solo per fonti Google Maps",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'})
    )
    max_reviews_tripadvisor = forms.IntegerField(
        required=False, label="Max Recensioni (Tripadvisor)",
        help_text="Solo per fonti Tripadvisor",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Es. 50'})
    )

    class Meta:
        model = ScrapingLink
        fields = ['source', 'url', 'is_active']
        widgets = {
            'source': forms.Select(attrs={'class': 'form-select'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://www.example.com/hotel/...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CompetitorScrapingTaskForm(forms.Form):
    competitors = forms.ModelMultipleChoiceField(
        queryset=Competitor.objects.all().order_by('name'),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Seleziona Competitors",
        help_text="Seleziona uno o più competitor per cui avviare lo scraping di tutti i link attivi."
    )
