from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """Dodaje klasę CSS do pola formularza"""
    # Sprawdzenie, czy field to faktycznie pole formularza, a nie np. string
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    else:
        # Jeśli to nie jest pole formularza, zwróć oryginalną wartość
        return field 