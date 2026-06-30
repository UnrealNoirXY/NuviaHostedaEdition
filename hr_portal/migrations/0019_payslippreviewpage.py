from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0018_payslippreviewjob_payload"),
    ]

    operations = [
        migrations.CreateModel(
            name="PayslipPreviewPage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_index", models.PositiveIntegerField()),
                ("image", models.FileField(max_length=255, upload_to="hr/payslip_previews/pages/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "preview_job",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="pages",
                        to="hr_portal.payslippreviewjob",
                    ),
                ),
            ],
            options={
                "ordering": ["page_index"],
                "unique_together": {("preview_job", "page_index")},
            },
        ),
    ]
