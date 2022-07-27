from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.admin.menu import AdminOnlyMenuItem

from .views import StaleContentReportView


@hooks.register("register_page_listing_buttons")
def page_listing_buttons(page, page_perms, is_parent=False, next_url=None):
    yield wagtailadmin_widgets.PageListingButton(
        "Import Content", "/import/", priority=10
    )


@hooks.register("register_reports_menu_item")
def register_stale_content_report_menu_item():
    return AdminOnlyMenuItem(
        "Stale Content",
        reverse("stale_content_report"),
        classnames="icon icon-" + StaleContentReportView.header_icon,
        order=700,
    )


@hooks.register("register_admin_urls")
def register_stale_content_report_url():
    return [
        path(
            "reports/stale-content/",
            StaleContentReportView.as_view(),
            name="stale_content_report",
        ),
    ]
