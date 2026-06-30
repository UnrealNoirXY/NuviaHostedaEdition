from django import forms
from django import forms
from django.utils import timezone
from .models import Ticket, TicketComment
from resort.models import Resort

from accounts.models import User  # importa il modello utente personalizzato
from resort.models import Room


PRIVILEGED_DEADLINE_ROLES = {
    User.OWNER,
    User.HEAD_MAINTAINER,
    User.MAINTENANCE_MANAGER,
    User.SUPERADMIN,
}


class TicketUpdateForm(forms.ModelForm):
    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Scadenza",
    )
    completion_photo = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label="Foto lavoro completato",
    )
    deadline_justification = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Motiva la proroga'}),
        label="Motivazione proroga",
    )
    acknowledged_due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Scadenza confermata",
        help_text="Conferma la scadenza concordata prima di chiudere o avanzare il ticket.",
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['status'].widget.attrs.update({'class': 'form-select'})
        self.fields['notes'].widget.attrs.update({'class': 'form-control', 'rows': 3})

        if self.instance and self.instance.due_date:
            self.fields['due_date'].initial = timezone.localtime(self.instance.due_date).strftime('%Y-%m-%dT%H:%M')

        if self.instance and self.instance.acknowledged_due_date:
            self.fields['acknowledged_due_date'].initial = (
                timezone.localtime(self.instance.acknowledged_due_date).strftime('%Y-%m-%dT%H:%M')
            )
        elif self.instance and self.instance.due_date:
            self.fields['acknowledged_due_date'].initial = timezone.localtime(self.instance.due_date).strftime('%Y-%m-%dT%H:%M')

        if self.user and not self._user_can_freely_edit_deadline(self.user):
            self.fields['deadline_justification'].required = False
        else:
            # Privileged users don't need justification unless they add it voluntarily
            self.fields['deadline_justification'].widget.attrs['placeholder'] = 'Opzionale'

    class Meta:
        model = Ticket
        fields = ['status', 'notes', 'due_date', 'completion_photo', 'acknowledged_due_date']

    @staticmethod
    def _user_can_freely_edit_deadline(user):
        return bool(user and (user.is_superuser or user.role in PRIVILEGED_DEADLINE_ROLES))

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now():
            raise forms.ValidationError("La scadenza non può essere nel passato.")
        return due_date

    def clean(self):
        cleaned_data = super().clean()
        new_status = cleaned_data.get('status')
        completion_photo = cleaned_data.get('completion_photo')
        due_date = cleaned_data.get('due_date')
        if due_date is None and self.instance:
            due_date = self.instance.due_date
            cleaned_data['due_date'] = due_date
        justification = cleaned_data.get('deadline_justification')
        acknowledged_due = cleaned_data.get('acknowledged_due_date') or (
            self.instance.acknowledged_due_date if self.instance else None
        )

        if new_status == 'closed' and not (completion_photo or (self.instance and self.instance.completion_photo)):
            self.add_error('completion_photo', "Per chiudere il ticket è obbligatorio caricare una foto del lavoro finito.")

        original_due = self.instance.due_date if self.instance else None

        if due_date != original_due:
            if not self._user_can_freely_edit_deadline(self.user):
                if original_due is None and due_date:
                    self.add_error('due_date', "Non puoi impostare una scadenza per questo ticket.")
                elif original_due and due_date and due_date <= original_due:
                    self.add_error('due_date', "Puoi solo prorogare la scadenza esistente.")
                if not justification:
                    self.add_error('deadline_justification', "Devi motivare la proroga della scadenza.")

            # reset acknowledged deadline when due date changes
            cleaned_data['acknowledged_due_date'] = None
            acknowledged_due = None

        effective_due = due_date or original_due

        if new_status in ['in_progress', 'resolved', 'closed']:
            if effective_due is None:
                self.add_error('due_date', "Definisci prima una scadenza per il ticket.")
            if acknowledged_due is None:
                self.add_error('acknowledged_due_date', "Devi confermare la scadenza prima di procedere.")

        if acknowledged_due and effective_due:
            normalized_ack = self._normalize_to_minute(acknowledged_due)
            normalized_effective = self._normalize_to_minute(effective_due)

            if normalized_ack == normalized_effective:
                # Persist the canonical value so the acknowledgement always matches the ticket deadline
                cleaned_data['acknowledged_due_date'] = effective_due
            else:
                self.add_error(
                    'acknowledged_due_date',
                    "La scadenza confermata deve coincidere con la scadenza del ticket.",
                )

        return cleaned_data

    def save(self, commit=True):
        ticket = super().save(commit=False)
        acknowledged_due = self.cleaned_data.get('acknowledged_due_date')
        previous_ack = None
        if self.instance and self.instance.pk:
            previous_ack = Ticket.objects.get(pk=self.instance.pk).acknowledged_due_date

        if acknowledged_due:
            if not previous_ack or acknowledged_due != previous_ack:
                ticket.acknowledged_by = self.user
                ticket.acknowledged_at = timezone.now()
        else:
            ticket.acknowledged_by = None
            ticket.acknowledged_at = None

        if commit:
            ticket.save()
        return ticket

    @staticmethod
    def _normalize_to_minute(value):
        if not value:
            return None
        return value.replace(second=0, microsecond=0)

class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['comment', 'attachment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Aggiungi una nota...'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        comment = cleaned_data.get("comment")
        attachment = cleaned_data.get("attachment")

        if not comment and not attachment:
            raise forms.ValidationError("Devi inserire una nota o caricare un allegato.", code='required')

        return cleaned_data

class TicketAssignForm(forms.ModelForm):
    resort = forms.ModelChoiceField(
        queryset=Resort.objects.none(),
        label="Seleziona Resort",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    room = forms.ModelChoiceField(
        queryset=Room.objects.none(),
        required=False,
        label="Seleziona Camera (opzionale)",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        label='Assegna a manutentore (opzionale)',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    due_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label="Scadenza",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # --- Determine the resort from all possible sources (POST data, instance, or initial GET data) ---
        resort = None
        if 'resort' in self.data:
            try:
                resort_id = int(self.data.get('resort'))
                resort = Resort.objects.get(id=resort_id)
            except (ValueError, TypeError, Resort.DoesNotExist):
                pass
        elif self.instance.pk and self.instance.resort:
            resort = self.instance.resort
        elif 'resort' in self.initial:
            resort = self.initial.get('resort')

        # --- Set querysets based on the determined resort ---
        if resort:
            self.fields['room'].queryset = Room.objects.filter(resort=resort).order_by('name')
            self.fields['assigned_to'].queryset = User.objects.filter(
                role=User.MAINTAINER,
                resort=resort
            ).order_by('username')
        else:
            # Initially, maintainers are empty, to be populated by AJAX
            self.fields['assigned_to'].queryset = User.objects.none()

        # --- Set resort queryset based on user permissions ---
        if user:
            if user.is_superuser:
                self.fields['resort'].queryset = Resort.objects.all()
            elif user.role in [User.OWNER, User.CAPO_ECONOMO, User.RISORSE_UMANE, User.HEAD_MAINTAINER, User.MAINTENANCE_MANAGER]:
                if user.company:
                    self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
                else:
                    self.fields['resort'].queryset = Resort.objects.none()
            elif user.role in [User.DIRECTOR, User.RECEPTIONIST, User.ECONOMO, User.HOUSEKEEPING, User.MAINTAINER]:
                if user.resort:
                    self.fields['resort'].queryset = Resort.objects.filter(pk=user.resort.pk)
                else:
                    self.fields['resort'].queryset = Resort.objects.none()

            if TicketUpdateForm._user_can_freely_edit_deadline(user):
                self.fields['due_date'].required = True
                self.fields['due_date'].help_text = "Imposta la scadenza iniziale concordata con il manutentore."
            else:
                self.fields['due_date'].help_text = "Non hai i permessi per impostare la scadenza."
                self.fields['due_date'].widget.attrs['readonly'] = True
                self.fields['due_date'].widget.attrs['tabindex'] = -1
                self.fields['due_date'].widget.attrs['class'] += ' disabled'

        # --- Disable fields if coming from QR code (check initial data) ---
        if 'resort' in self.initial and 'room' in self.initial:
            self.fields['resort'].disabled = True
            self.fields['room'].disabled = True


    class Meta:
        model = Ticket
        fields = ['title', 'resort', 'room', 'priority', 'required_skill', 'description', 'attachment', 'assigned_to', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'required_skill': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'style': 'max-width: 100%;'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }
