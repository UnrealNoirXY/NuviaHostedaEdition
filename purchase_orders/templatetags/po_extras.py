from django import template

register = template.Library()

@register.filter(name='status_badge')
def status_badge(status):
    """
    Returns a Bootstrap badge color class based on the status string.
    """
    # Purchase Order Statuses
    if status == 'draft':
        return 'bg-secondary'
    elif status == 'submitted':
        return 'bg-info text-dark'
    elif status == 'approved':
        return 'bg-primary'
    elif status == 'completed':
        return 'bg-success'
    elif status == 'cancelled':
        return 'bg-danger'
    # Ticket Statuses (for good measure, though not used in this app)
    elif status == 'Aperto':
        return 'bg-danger'
    elif status == 'In Lavorazione':
        return 'bg-warning text-dark'
    elif status == 'Chiuso':
        return 'bg-success'
    # Default
    return 'bg-dark'
