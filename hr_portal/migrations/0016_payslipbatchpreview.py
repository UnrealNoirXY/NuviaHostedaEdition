from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0015_payslipbatch_manual_assignments"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayslipBatchPreview",
            fields=[
                ("id", models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ("source_filename", models.CharField(blank=True, default="", max_length=255)),
                ("manual_assignments", models.JSONField(blank=True, default=dict)),
                ("locked_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payslip_batch_previews",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
