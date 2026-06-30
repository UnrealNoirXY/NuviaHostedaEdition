from django import template
from ..models import IT_Ticket

register = template.Library()

@register.filter
def get_status_display_from_key(key):
    return dict(IT_Ticket.STATUS_CHOICES).get(key, key)

@register.filter
def get_priority_display_from_key(key):
    return dict(IT_Ticket.PRIORITY_CHOICES).get(key, key)

@register.filter
def get_device_display_from_key(key):
    return dict(IT_Ticket.DEVICE_CHOICES).get(key, key)
