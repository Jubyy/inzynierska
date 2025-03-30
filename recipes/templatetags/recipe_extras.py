from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Filter do pobierania elementu słownika przez klucz w szablonach Django.
    
    Przykład użycia:
    {{ my_dict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    
    return dictionary.get(key) 