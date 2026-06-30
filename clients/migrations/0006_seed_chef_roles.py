from django.db import migrations


def seed_chef_roles(apps, schema_editor):
    Company = apps.get_model('clients', 'Company')
    StructureRole = apps.get_model('clients', 'StructureRole')

    for company in Company.objects.all():
        StructureRole.objects.get_or_create(
            company=company,
            name='Chef',
            defaults={
                'can_edit_menus': True,
                'can_edit_dishes': True,
                'can_manage_allergens': True,
            },
        )
        StructureRole.objects.get_or_create(
            company=company,
            name='Executive Chef',
            defaults={
                'can_edit_menus': True,
                'can_edit_dishes': True,
                'can_manage_allergens': True,
                'can_publish_menu': True,
                'can_approve_menu': True,
            },
        )


def unseed_chef_roles(apps, schema_editor):
    StructureRole = apps.get_model('clients', 'StructureRole')
    StructureRole.objects.filter(name__in=['Chef', 'Executive Chef']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0005_structurerole_can_approve_menu_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_chef_roles, unseed_chef_roles),
    ]
