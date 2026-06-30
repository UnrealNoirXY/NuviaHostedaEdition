from django import template
import os

register = template.Library()

@register.filter(name='get_file_type')
def get_file_type(file_field):
    if not file_field or not file_field.name:
        return 'none'

    name = file_field.name.lower()
    if name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
        return 'image'
    if name.endswith(('.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv')):
        return 'video'
    return 'file'
