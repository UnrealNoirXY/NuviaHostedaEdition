from django import forms
from django.utils import timezone
from accounts.models import User
from core.models import AdminLogEntry, NuviaMailAccount, NuviaMailSignature, NuviaMailTemplate, NuviaMailSendQueue, NuviaMailCompliancePolicy
from resort.models import Resort, Room
from clients.models import Company

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['resort', 'name', 'description']

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

        if requesting_user and not requesting_user.is_superuser:
            if 'resort' in self.fields and requesting_user.company:
                self.fields['resort'].queryset = Resort.objects.filter(company=requesting_user.company)

class ResortForm(forms.ModelForm):
    class Meta:
        model = Resort
        fields = ['name', 'location', 'company']

    def __init__(self, *args, **kwargs):
        requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'

        if requesting_user and not requesting_user.is_superuser:
            # Owners don't get to choose the company, it's set in the view
            if 'company' in self.fields:
                del self.fields['company']

class UserForm(forms.ModelForm):
    new_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Nuova Password", help_text="Lasciare vuoto per non modificare la password.")
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), required=False, label="Conferma Nuova Password")

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'fiscal_code', 'role', 'company', 'resort', 'is_active', 'skills', 'has_maintenance_access', 'has_reviews_access', 'can_manage_purchase_orders', 'has_inventory_access', 'can_export_review_reports']
        widgets = {
            'skills': forms.CheckboxSelectMultiple,
            'has_maintenance_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_reviews_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_purchase_orders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_inventory_access': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_export_review_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and new_password != confirm_password:
            self.add_error('confirm_password', "Le password non corrispondono.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        # Pop the 'user' kwarg before calling super
        requesting_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Apply default widget classes
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.CheckboxInput):
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs.setdefault('class', 'form-select')
                else:
                    field.widget.attrs.setdefault('class', 'form-control')

        # If there is a requesting user, apply permission logic
        if requesting_user:
            # Only Superadmins and Owners can manage tool permissions
            if requesting_user.role not in [User.SUPERADMIN, User.OWNER]:
                if 'can_manage_purchase_orders' in self.fields:
                    del self.fields['can_manage_purchase_orders']
                if 'has_inventory_access' in self.fields:
                    del self.fields['has_inventory_access']
                if 'fiscal_code' in self.fields:
                    del self.fields['fiscal_code']

            # If the user is an owner, not a superuser, restrict their choices
            if not requesting_user.is_superuser and requesting_user.role == User.OWNER:
                # An owner cannot change the company
                if 'company' in self.fields:
                    if requesting_user.company:
                        self.fields['company'].queryset = Company.objects.filter(pk=requesting_user.company.pk)
                        self.fields['company'].initial = requesting_user.company
                    self.fields['company'].disabled = True

                # An owner can only assign roles below their own
                self.fields['role'].choices = [
                    (role, label) for role, label in User.ROLE_CHOICES
                    if role not in [User.SUPERADMIN, User.OWNER]
                ]

                # An owner can only assign resorts belonging to their company
                if 'resort' in self.fields and requesting_user.company:
                    self.fields['resort'].queryset = Resort.objects.filter(company=requesting_user.company)

            elif not requesting_user.is_superuser and requesting_user.role == User.HEAD_MAINTAINER:
                # A Head Maintainer can only create/edit Maintainers.
                self.fields['role'].choices = [
                    (role, label) for role, label in User.ROLE_CHOICES
                    if role == User.MAINTAINER
                ]
                # They also cannot change the company
                if 'company' in self.fields:
                    if requesting_user.company:
                        self.fields['company'].queryset = Company.objects.filter(pk=requesting_user.company.pk)
                        self.fields['company'].initial = requesting_user.company
                    self.fields['company'].disabled = True
                # And can only assign resorts from their company
                if 'resort' in self.fields and requesting_user.company:
                    self.fields['resort'].queryset = Resort.objects.filter(company=requesting_user.company)

class ProfileAvatarForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['avatar']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class UserProfileThemeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['theme']
        widgets = {
            'theme': forms.Select(attrs={'class': 'form-select'}),
        }

class UserCreationForm(UserForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}), label="Password")

    class Meta(UserForm.Meta):
        fields = UserForm.Meta.fields + ['password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.must_change_password = True
        if commit:
            user.save()
        return user

class ReportFilterForm(forms.Form):
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    resort = forms.ModelChoiceField(queryset=Resort.objects.all(), required=False, empty_label="Tutti i Resort", widget=forms.Select(attrs={'class': 'form-select'}))
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False, empty_label="Tutti gli Utenti", widget=forms.Select(attrs={'class': 'form-select'}))


class AdminLogFilterForm(forms.Form):
    start_date = forms.DateField(
        label="Dal",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    end_date = forms.DateField(
        label="Al",
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    action_type = forms.ChoiceField(
        label="Funzione/Modulo",
        required=False,
        choices=[("", "Tutte le funzioni")] + list(AdminLogEntry.ACTION_CHOICES),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    user = forms.ModelChoiceField(
        label="Utente/Profilo",
        queryset=User.objects.all(),
        required=False,
        empty_label="Tutti gli utenti",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    ip_address = forms.CharField(
        label="IP",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cerca IP..."}),
    )

class TwoFactorAuthForm(forms.Form):
    enable_2fa = forms.BooleanField(
        required=False,
        label="Abilita Autenticazione a Due Fattori via Email",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class TwoFactorVerifyForm(forms.Form):
    code = forms.CharField(
        label="Codice di Verifica",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '******', 'autocomplete': 'off'})
    )
    remember_device = forms.BooleanField(
        required=False,
        label="Ricorda questo dispositivo per 30 giorni",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class PasswordChangeOTPForm(forms.Form):
    code = forms.CharField(
        label="Codice OTP",
        max_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '******', 'autocomplete': 'off'})
    )

class UserFilterForm(forms.Form):
    name = forms.CharField(label="Nome", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cerca per nome o username...'}))
    resort = forms.ModelChoiceField(label="Struttura", queryset=Resort.objects.all(), required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    role = forms.ChoiceField(label="Ruolo/Settore", required=False, choices=[('', 'Tutti i ruoli')] + User.ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and not user.is_superuser:
            if user.role == User.OWNER and user.company:
                # Owner can filter by any resort in their company
                self.fields['resort'].queryset = Resort.objects.filter(company=user.company)
            elif user.role == User.DIRECTOR and user.resort:
                # Director can only see their own resort
                self.fields['resort'].queryset = Resort.objects.filter(pk=user.resort.pk)
                self.fields['resort'].disabled = True
                self.fields['resort'].initial = user.resort
            else:
                # For other roles, or if no company/resort is set, hide the field
                del self.fields['resort']



class NuviaMailAccountForm(forms.ModelForm):
    class Meta:
        model = NuviaMailAccount
        fields = [
            'provider',
            'auth_mode',
            'email_address',
            'username',
            'imap_host',
            'imap_port',
            'smtp_host',
            'smtp_port',
            'use_ssl',
            'use_starttls',
            'is_active',
        ]
        widgets = {
            'provider': forms.Select(attrs={'class': 'form-select'}),
            'auth_mode': forms.Select(attrs={'class': 'form-select'}),
            'email_address': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nome.cognome@azienda.it'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Se vuoto usa email aziendale'}),
            'imap_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'imap.tuodominio.com'}),
            'imap_port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
            'smtp_host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'smtp.tuodominio.com'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
            'use_ssl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'use_starttls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        provider = cleaned_data.get('provider')
        imap_host = cleaned_data.get('imap_host')
        smtp_host = cleaned_data.get('smtp_host')

        if provider == NuviaMailAccount.PROVIDER_IMAP:
            if not imap_host:
                self.add_error('imap_host', 'Inserisci il server IMAP per la configurazione generica.')
            if not smtp_host:
                self.add_error('smtp_host', 'Inserisci il server SMTP per la configurazione generica.')

        return cleaned_data


class NuviaMailSignatureForm(forms.ModelForm):
    class Meta:
        model = NuviaMailSignature
        fields = ['name', 'body', 'is_default']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Firma standard'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Cordiali saluti,\n{{nome}} {{cognome}}'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }



class NuviaMailTemplateForm(forms.ModelForm):
    class Meta:
        model = NuviaMailTemplate
        fields = ['name', 'subject', 'body', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Risposta rapida reception'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Oggetto template'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Contenuto template...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class NuviaMailSendQueueForm(forms.ModelForm):
    class Meta:
        model = NuviaMailSendQueue
        fields = ['to_email', 'cc', 'bcc', 'subject', 'body', 'scheduled_for']
        widgets = {
            'to_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'destinatario@azienda.it'}),
            'cc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'opzionale'}),
            'bcc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'opzionale'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Oggetto email'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Scrivi qui il messaggio...'}),
            'scheduled_for': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_scheduled_for(self):
        value = self.cleaned_data.get('scheduled_for')
        if value and value <= timezone.now():
            raise forms.ValidationError('La pianificazione deve essere nel futuro.')
        return value



class NuviaMailCompliancePolicyForm(forms.ModelForm):
    class Meta:
        model = NuviaMailCompliancePolicy
        fields = [
            'enforce_external_domain_block',
            'allowed_domains',
            'blocked_domains',
            'blocked_recipients',
            'sensitive_keywords',
            'sensitive_regex_patterns',
            'flagged_action',
        ]
        widgets = {
            'enforce_external_domain_block': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allowed_domains': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'azienda.it, partner.com'}),
            'blocked_domains': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'mailinator.com,tempmail.com'}),
            'blocked_recipients': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'blocked@dominio.it, spam@foo.com'}),
            'sensitive_keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'iban, password, carta credito'}),
            'sensitive_regex_patterns': forms.TextInput(attrs={'class': 'form-control', 'placeholder': r'([A-Z]{2}\d{2}[A-Z0-9]{11,30}),(?:\d[ -]*?){13,16}'}),
            'flagged_action': forms.Select(attrs={'class': 'form-select'}),
        }
