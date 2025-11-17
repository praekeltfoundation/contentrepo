from importlib.metadata import version

from django import template

register = template.Library()


@register.simple_tag
def contentrepo_version() -> str:
    return version("contentrepo")
