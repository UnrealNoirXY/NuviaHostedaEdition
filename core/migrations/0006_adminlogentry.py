from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_platformsettings_marketing_policy_version_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminLogEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("access", "Accessi"),
                            ("password_change", "Cambio password"),
                            ("payslip", "Buste paga"),
                            ("communication", "Comunicazioni"),
                            ("intellectual_property", "Proprietà intellettuale"),
                            ("data", "Dati"),
                            ("other", "Altro"),
                        ],
                        db_index=True,
                        max_length=50,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("description", models.TextField(blank=True)),
                ("extra", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="admin_logs",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Log amministratore",
                "verbose_name_plural": "Log amministratore",
                "ordering": ("-timestamp",),
            },
        ),
    ]
