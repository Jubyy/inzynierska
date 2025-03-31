from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """Dodaje klasę CSS do pola formularza"""
    return field.as_widget(attrs={'class': css_class}) 