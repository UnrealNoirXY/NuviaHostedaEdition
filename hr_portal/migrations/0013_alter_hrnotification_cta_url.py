from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0012_payslipbatch_default_match_strategy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="hrnotification",
            name="cta_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
