from django import forms
from .models import Announcement
from accounts.models import User
from resort.models import Resort

from .models import RecipientGroup

class AnnouncementForm(forms.ModelForm):
    load_group = forms.ModelChoiceField(
        queryset=RecipientGroup.objects.none(), # Will be populated in the view
        required=False,
        label="Carica un Gruppo Salvato",
        empty_label="-- Nessuno --",
        widget=forms.Select(attrs={'class': 'form-select mb-3', 'id': 'load-group-select'})
    )
    target_resorts = forms.ModelMultipleChoiceField(
        queryset=Resort.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        required=False,
        label="Invia a tutti gli utenti di questi Resort"
    )
    target_roles = forms.MultipleChoiceField(
        choices=User.ROLE_CHOICES,
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        required=False,
        label="Filtra per questi Ruoli (opzionale, si applica ai resort scelti)"
    )
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
        required=False,
        label="Oppure, invia a questi Utenti Specifici"
    )
    save_group = forms.BooleanField(
        required=False,
        label="Salva questa selezione di destinatari come un nuovo gruppo",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    new_group_name = forms.CharField(
        max_length=100,
        required=False,
        label="Nome del nuovo gruppo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Announcement
        fields = ['load_group', 'title', 'body', 'priority', 'target_resorts', 'target_roles', 'recipients', 'save_group', 'new_group_name']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Titolo',
            'body': 'Messaggio',
            'priority': 'Priorità',
        }

    def clean(self):
        cleaned_data = super().clean()
        target_resorts = cleaned_data.get('target_resorts')
        recipients = cleaned_data.get('recipients')
        target_roles = cleaned_data.get('target_roles')

        # We need at least one resort, one role, or one user.
        if not target_resorts and not recipients and not target_roles:
            raise forms.ValidationError(
                "Devi selezionare almeno un resort, un ruolo o un utente specifico a cui inviare la comunicazione."
            )
        return cleaned_data


from django_celery_beat.models import CrontabSchedule, PeriodicTask
from .models import ScheduledEmailReport

class ScheduledEmailReportForm(forms.ModelForm):
    class Meta:
        model = ScheduledEmailReport
        fields = [
            'name', 'recipients', 'resorts', 'is_active',
            'frequency', 'day_of_week', 'hour', 'minute', 'review_period_days'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'recipients': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '8'}),
            'resorts': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '8'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'hour': forms.Select(choices=[(i, f"{i:02d}") for i in range(24)], attrs={'class': 'form-select'}),
            'minute': forms.Select(choices=[(i, f"{i:02d}") for i in range(0, 60, 15)], attrs={'class': 'form-select'}),
            'review_period_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
        labels = {
            'name': "Nome del Report",
            'recipients': "Destinatari",
            'resorts': "Resort da Includere",
            'is_active': "Attiva/Disattiva Invio Programmato",
            'frequency': "Frequenza",
            'day_of_week': "Giorno della settimana",
            'hour': "Ora di invio",
            'minute': "Minuto di invio",
            'review_period_days': "Includi recensioni degli ultimi (giorni)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recipients'].queryset = User.objects.filter(
            is_active=True
        ).exclude(email="").distinct().order_by('username')
        self.fields['resorts'].queryset = Resort.objects.all().order_by('name')

        # Imposta i valori iniziali per i campi di tempo/frequenza se l'istanza esiste
        if self.instance and self.instance.pk:
            self.fields['hour'].initial = self.instance.hour
            self.fields['minute'].initial = self.instance.minute
            self.fields['day_of_week'].initial = self.instance.day_of_week
            self.fields['frequency'].initial = self.instance.frequency

    def save(self, commit=True):
        import json
        instance = super().save(commit=False)

        # Logica per creare il CrontabSchedule
        hour = self.cleaned_data.get('hour')
        minute = self.cleaned_data.get('minute')
        frequency = self.cleaned_data.get('frequency')
        day_of_week = self.cleaned_data.get('day_of_week', '*')

        cron_params = {
            'minute': minute,
            'hour': hour,
            'day_of_month': '*',
            'month_of_year': '*',
            'day_of_week': '*' if frequency == ScheduledEmailReport.FREQUENCY_DAILY else day_of_week,
        }
        crontab, _ = CrontabSchedule.objects.get_or_create(**cron_params)

        if commit:
            # Salva l'istanza principale prima di gestire il task periodico
            instance.save()
            self.save_m2m()

            task_name = f"Scheduled Report: {instance.name} (ID: {instance.id})"
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
                    task='communications.tasks.send_review_report',
                    args=task_args,
                    enabled=instance.is_active,
                )
                instance.periodic_task = new_task
                instance.save(update_fields=['periodic_task'])

        return instance
