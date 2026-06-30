from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0008_alter_hreventlog_event_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payslip",
            name="file",
            field=models.FileField(max_length=255, upload_to="hr/payslips/"),
        ),
        migrations.AlterField(
            model_name="payslipunmatched",
            name="file",
            field=models.FileField(max_length=255, upload_to="hr/payslips/unmatched/"),
        ),
    ]
