from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hr_portal", "0002_payslipunmatched_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="payslipunmatched",
            name="status",
            field=models.CharField(
                choices=[("to_assign", "DA ASSEGNARE"), ("resolved", "ASSEGNATO")],
                db_index=True,
                default="to_assign",
                max_length=32,
            ),
        ),
    ]
