from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_user_privacy_policy_and_fiscal_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(
                default=False,
                help_text="Se attivo, l'utente deve cambiare la password al primo accesso.",
                verbose_name="Cambio password obbligatorio",
            ),
        ),
    ]
