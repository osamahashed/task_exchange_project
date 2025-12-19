from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except Exception:
        return None
