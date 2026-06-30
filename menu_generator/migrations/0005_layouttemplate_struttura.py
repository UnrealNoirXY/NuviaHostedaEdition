from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0005_structurerole_can_approve_menu_and_more'),
        ('menu_generator', '0004_menudocumentjob_expires_at_menuauditevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='layouttemplate',
            name='struttura',
            field=models.ForeignKey(
                blank=True,
                help_text='Struttura associata al layout (selezione opzionale).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='layout_templates',
                to='clients.structure',
            ),
        ),
    ]
