from django.db import migrations


DEFAULT_ROLES = (
    (
        "Chef",
        {
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_manage_allergens": True,
        },
    ),
    (
        "Executive Chef",
        {
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_manage_allergens": True,
            "can_publish_menu": True,
            "can_approve_menu": True,
        },
    ),
    (
        "Proprietario",
        {
            "can_edit_layouts": True,
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_publish_menu": True,
            "can_approve_menu": True,
            "can_manage_allergens": True,
            "can_manage_templates": True,
        },
    ),
)


def seed_default_roles(apps, schema_editor):
    Company = apps.get_model("clients", "Company")
    StructureRole = apps.get_model("clients", "StructureRole")

    for company in Company.objects.all():
        for name, defaults in DEFAULT_ROLES:
            StructureRole.objects.get_or_create(
                company=company,
                name=name,
                defaults=defaults,
            )


def unseed_default_roles(apps, schema_editor):
    StructureRole = apps.get_model("clients", "StructureRole")
    StructureRole.objects.filter(name__in=[role[0] for role in DEFAULT_ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("clients", "0006_seed_chef_roles"),
    ]

    operations = [
        migrations.RunPython(seed_default_roles, unseed_default_roles),
    ]
