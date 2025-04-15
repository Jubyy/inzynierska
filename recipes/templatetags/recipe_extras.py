from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Zwraca wartość ze słownika dla podanego klucza"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter(name='format_notification_count')
def format_notification_count(count):
    """Formatuje liczbę powiadomień dla wyświetlenia w interfejsie"""
    if count is None or count == 0:
        return ""
    elif count > 99:
        return "99+"
    else:
        return str(count)

@register.filter(name='is_helpful_to')
def is_helpful_to(rating, user):
    """Sprawdza, czy ocena jest przydatna dla danego użytkownika"""
    if hasattr(rating, 'is_helpful_for'):
        return rating.is_helpful_for(user)
    return False 