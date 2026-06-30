from django.conf import settings
from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0016_payslipbatchpreview"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayslipPreviewJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_file", models.FileField(max_length=255, upload_to="hr/payslip_previews/")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "In coda"),
                            ("running", "In esecuzione"),
                            ("completed", "Completata"),
                            ("failed", "Fallita"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("progress_percent", models.PositiveIntegerField(default=0)),
                ("total_items", models.PositiveIntegerField(default=0)),
                ("processed_items", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="payslip_preview_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
