from django.urls import path, reverse

from wagtail.admin.menu import MenuItem
from wagtail import hooks

from .views import page_views


@hooks.register("register_admin_urls")
def register_page_view_url():
    return [
        path("page_view/", page_views, name="page_view"),
    ]


@hooks.register("register_admin_menu_item")
def register_page_view_menu_item():
    return MenuItem("Page views", reverse("page_view"), icon_name="doc-empty")
