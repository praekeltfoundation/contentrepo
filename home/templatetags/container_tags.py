from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def container_image_hash() -> str:
    container_image = settings.CONTAINER_IMAGE
    # Extract "main-6e26067" from "ghcr.io/praekeltfoundation/contentrepo:main-6e26067"
    if ":" in container_image:
        return container_image.split(":")[-1]
    return container_image
