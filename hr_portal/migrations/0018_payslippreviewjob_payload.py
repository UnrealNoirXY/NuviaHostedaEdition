from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0017_payslippreviewjob"),
    ]

    operations = [
        migrations.AddField(
            model_name="payslippreviewjob",
            name="preview_payload",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
