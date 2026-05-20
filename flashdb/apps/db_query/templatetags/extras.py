'''Custom Django template for extras'''
from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    """Custom Django template filter to access list elements by index"""
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return None
