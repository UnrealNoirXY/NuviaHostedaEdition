from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0011_hrnotification_cta"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payslipbatch",
            name="auto_match_strategy",
            field=models.CharField(
                default="fiscal_code",
                help_text="Strategia di auto-match: fiscal_code, username, email o regex su fiscal_code",
                max_length=50,
            ),
        ),
    ]
