from django import forms
from .models import IT_Ticket, IT_TicketComment
from accounts.models import User
from django.db.models import Q

from assets.models import Asset

class IT_TicketForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.resort:
            # Show assets assigned to the user's resort OR assets with no resort
            self.fields['asset'].queryset = Asset.objects.filter(
                Q(resort=user.resort) | Q(resort__isnull=True)
            )
        elif user:
            # If user has no resort, show only unassigned assets
            self.fields['asset'].queryset = Asset.objects.filter(resort__isnull=True)
        else:
            # No user, show no assets
            self.fields['asset'].queryset = Asset.objects.none()

    class Meta:
        model = IT_Ticket
        fields = ['title', 'description', 'device_type', 'priority', 'asset', 'anydesk_id', 'attachment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'anydesk_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. 123 456 789'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'anydesk_id': "Se pertinente, inserire l'ID AnyDesk per l'assistenza remota.",
            'attachment': "Allega uno screenshot o un file di log che possa aiutare a capire il problema."
        }
        labels = {
            'title': 'Oggetto del Problema',
            'description': 'Descrizione Dettagliata',
            'device_type': 'Tipo di Dispositivo',
            'priority': 'Priorità',
            'anydesk_id': 'ID AnyDesk',
            'attachment': 'Allegato',
        }

class IT_TicketUpdateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit choices for 'assigned_to' to relevant roles
        self.fields['assigned_to'].queryset = User.objects.filter(
            Q(role=User.IT_TECHNICIAN) | Q(is_superuser=True)
        ).distinct()
        self.fields['assigned_to'].required = False

    class Meta:
        model = IT_Ticket
        fields = ['status', 'priority', 'assigned_to', 'intervention_cost']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'status': 'Stato del Ticket',
            'priority': 'Nuova Priorità',
            'assigned_to': 'Assegna a',
        }

class IT_TicketCommentForm(forms.ModelForm):
    class Meta:
        model = IT_TicketComment
        fields = ['comment', 'attachment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Aggiungi un commento...'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'comment': 'Nuovo Commento',
            'attachment': 'Allega un file (opzionale)',
        }
