from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0003_payslipunmatched_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="payslipbatch",
            name="enable_ocr",
            field=models.BooleanField(
                default=False,
                help_text="Abilita OCR sui PDF singoli se il testo incorporato non contiene identificativi chiari",
            ),
        ),
        migrations.AddField(
            model_name="payslipbatch",
            name="ocr_languages",
            field=models.CharField(
                blank=True,
                default="ita+eng",
                help_text="Lingue da passare a Tesseract (es. ita+eng)",
                max_length=50,
            ),
        ),
    ]
