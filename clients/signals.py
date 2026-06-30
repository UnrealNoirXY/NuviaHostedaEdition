from django.db import IntegrityError
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Company, StructureRole


DEFAULT_ROLES = (
    {
        "name": "Chef",
        "defaults": {
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_manage_allergens": True,
        },
    },
    {
        "name": "Executive Chef",
        "defaults": {
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_manage_allergens": True,
            "can_publish_menu": True,
            "can_approve_menu": True,
        },
    },
    {
        "name": "Proprietario",
        "defaults": {
            "can_edit_layouts": True,
            "can_edit_menus": True,
            "can_edit_dishes": True,
            "can_publish_menu": True,
            "can_approve_menu": True,
            "can_manage_allergens": True,
            "can_manage_templates": True,
        },
    },
)


def ensure_default_roles(company):
    for role in DEFAULT_ROLES:
        try:
            StructureRole.objects.get_or_create(
                company=company,
                name=role["name"],
                defaults=role["defaults"],
            )
        except IntegrityError:
            StructureRole.objects.filter(
                company=company,
                name=role["name"],
            ).first()


@receiver(post_save, sender=Company)
def create_default_roles(sender, instance, created, **kwargs):
    if created:
        ensure_default_roles(instance)
