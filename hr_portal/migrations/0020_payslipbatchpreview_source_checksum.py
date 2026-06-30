from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0019_payslippreviewpage"),
    ]

    operations = [
        migrations.AddField(
            model_name="payslipbatchpreview",
            name="source_checksum",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
    ]
