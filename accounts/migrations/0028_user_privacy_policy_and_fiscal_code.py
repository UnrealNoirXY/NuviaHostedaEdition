from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0027_user_menu_creation_studio_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="fiscal_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Codice fiscale dell'utente (16 caratteri).",
                max_length=16,
                null=True,
                verbose_name="Codice Fiscale",
            ),
        ),
        migrations.CreateModel(
            name="PrivacyPolicyVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=50, unique=True)),
                ("content", models.TextField(help_text="Contenuto HTML/testo della policy.")),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Versione Policy Privacy",
                "verbose_name_plural": "Versioni Policy Privacy",
                "ordering": ("-published_at", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="UserPrivacyConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accepted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("payslip_email_opt_in", models.BooleanField(default=False)),
                ("payslip_email_opt_in_at", models.DateTimeField(blank=True, null=True)),
                ("email_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "policy_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="user_consents",
                        to="accounts.privacypolicyversion",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="privacy_consents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Consenso Privacy Utente",
                "verbose_name_plural": "Consensi Privacy Utenti",
                "ordering": ("-accepted_at", "-created_at"),
                "unique_together": {("user", "policy_version")},
            },
        ),
        migrations.AddIndex(
            model_name="userprivacyconsent",
            index=models.Index(fields=["user", "policy_version"], name="accounts_us_user_id_7e1b4b_idx"),
        ),
        migrations.AddIndex(
            model_name="userprivacyconsent",
            index=models.Index(fields=["payslip_email_opt_in"], name="accounts_us_payslip_3f5b2b_idx"),
        ),
    ]
