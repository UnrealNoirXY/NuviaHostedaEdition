from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0014_alter_payslipbatch_enable_ocr"),
    ]

    operations = [
        migrations.AddField(
            model_name="payslipbatch",
            name="manual_assignments",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
