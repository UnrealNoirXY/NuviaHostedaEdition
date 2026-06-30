from django import forms
from .models import Guest, Consent

class GuestForm(forms.ModelForm):
    # Aggiungiamo un campo per l'upload del documento, non legato direttamente al modello Guest
    document_image = forms.ImageField(
        label="Foto del Documento d'Identità",
        required=True,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Guest
        fields = [
            'first_name',
            'last_name',
            'date_of_birth',
            'document_number',
            'document_expiry_date',
            'document_image',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cognome'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'document_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numero documento (es. AA1234567)'}),
            'document_expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        labels = {
            'first_name': 'Nome',
            'last_name': 'Cognome',
            'date_of_birth': 'Data di Nascita',
            'document_number': 'Numero Documento',
            'document_expiry_date': 'Data di Scadenza Documento',
        }

# Usiamo un formset per gestire un numero variabile di ospiti per prenotazione
GuestFormSet = forms.formset_factory(
    GuestForm,
    extra=1,
    can_delete=True,
)

class ConsentForm(forms.Form):
    terms_and_conditions = forms.BooleanField(
        required=True,
        label="Dichiaro di aver letto e di accettare i Termini e le Condizioni del soggiorno."
    )
    privacy_policy = forms.BooleanField(
        required=True,
        label="Dichiaro di aver letto e di accettare l'Informativa sulla Privacy."
    )
    newsletter_subscription = forms.BooleanField(
        required=False,
        label="Desidero iscrivermi alla newsletter per ricevere offerte e promozioni."
    )

class OtpForm(forms.Form):
    otp_code = forms.CharField(
        label="Codice OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg text-center', 'placeholder': '------', 'autocomplete': 'one-time-code'}),
    )