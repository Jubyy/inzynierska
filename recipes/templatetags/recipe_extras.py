from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Filter do pobierania elementu słownika przez klucz w szablonach Django.
    
    Przykład użycia:
    {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    
    return dictionary.get(key) 