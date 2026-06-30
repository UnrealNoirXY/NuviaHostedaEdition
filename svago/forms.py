from django import forms
from accounts.models import User

class GamerTagForm(forms.Form):
    gamertag = forms.CharField(
        max_length=20,
        required=True,
        label="Scegli il tuo GamerTag",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. SuperMario'})
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label="Entrando in questo spazio il vostro gamertag sarà visibile da altri utenti online."
    )

    def clean_gamertag(self):
        gamertag = self.cleaned_data.get('gamertag')
        # Check for uniqueness, case-insensitive
        if User.objects.filter(gamertag__iexact=gamertag).exists():
            raise forms.ValidationError("Questo GamerTag è già stato scelto. Provane un altro.")
        return gamertag
