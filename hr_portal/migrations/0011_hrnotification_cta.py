from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0010_payslipemailrecipient"),
    ]

    operations = [
        migrations.AddField(
            model_name="hrnotification",
            name="cta_label",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="hrnotification",
            name="cta_type",
            field=models.CharField(
                choices=[("primary", "Primaria"), ("secondary", "Secondaria")],
                default="primary",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="hrnotification",
            name="cta_url",
            field=models.URLField(blank=True, default=""),
        ),
    ]
