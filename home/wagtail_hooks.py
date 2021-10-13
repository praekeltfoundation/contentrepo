from wagtail.core import hooks
from wagtail.admin import widgets as wagtailadmin_widgets


@hooks.register("register_page_listing_buttons")
def page_listing_buttons(page, page_perms, is_parent=False, next_url=None):
    yield wagtailadmin_widgets.PageListingButton(
        "Import Content", "/import/", priority=10
    )
