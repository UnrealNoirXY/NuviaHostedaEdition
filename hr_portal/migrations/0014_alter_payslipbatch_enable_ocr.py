from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("hr_portal", "0013_alter_hrnotification_cta_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payslipbatch",
            name="enable_ocr",
            field=models.BooleanField(
                default=True,
                help_text="Abilita OCR sui PDF singoli se il testo incorporato non contiene identificativi chiari",
            ),
        ),
    ]
