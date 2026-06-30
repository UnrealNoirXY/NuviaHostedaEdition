from decimal import Decimal

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0014_ticket_completion_photo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='actual_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Costo effettivo sostenuto per risolvere il ticket.',
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0'))],
            ),
        ),
        migrations.AddField(
            model_name='ticket',
            name='estimated_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Costo stimato per completare il ticket.',
                max_digits=12,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal('0'))],
            ),
        ),
    ]
