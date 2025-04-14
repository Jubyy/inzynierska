from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Zwraca wartość ze słownika dla podanego klucza"""
    if dictionary is None:
        return None
    return dictionary.get(key) 