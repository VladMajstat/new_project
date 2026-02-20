# main_app/templatetags/dict_extras.py
from django import template

register = template.Library()

@register.filter
def getitem(d, key):
    """dict lookup in templates: {{ mydict|getitem:key }}"""
    if d is None:
        return None
    return d.get(key)

@register.filter
def grade_class(value):
    """
    Map Outstanding -> CSS class.
    0–20: purple, 21–50: red, 51–75: amber, 76+: green
    """
    try:
        v = int(value)
    except Exception:
        return ""
    if 0 <= v <= 20:
        return "purple"
    if 21 <= v <= 50:
        return "red"
    if 51 <= v <= 75:
        return "amber"
    return "green"
