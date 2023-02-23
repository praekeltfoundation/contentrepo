from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import ContentPage, OrderedContentSet
from .views import ContentPageReportView, CustomIndexView, PageViewReportView OrderedContentSetUploadView


@hooks.register('register_admin_urls')
def register_ordered_set_import_url():
    return [
        path('import_orderedcontentset/', OrderedContentSetUploadView.as_view(), name='import_orderedcontentset'),
    ]


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
        classnames="icon icon-" + ContentPageReportView.header_icon,
        order=700,
    )


@hooks.register("register_admin_urls")
def register_stale_content_report_url():
    return [
        path(
            "reports/stale-content/",
            ContentPageReportView.as_view(),
            name="stale_content_report",
        ),
    ]


@hooks.register("register_reports_menu_item")
def register_page_views_report_menu_item():
    return AdminOnlyMenuItem(
        "Page Views",
        reverse("page_view_report"),
        classnames="icon icon-doc-empty",
        order=700,
    )


@hooks.register("register_admin_urls")
def register_page_views_report_url():
    return [
        path(
            "reports/page-views/",
            PageViewReportView.as_view(),
            name="page_view_report",
        ),
    ]


class ContentPageAdmin(ModelAdmin):
    model = ContentPage
    menu_label = "ContentPages"
    menu_icon = "pilcrow"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    index_view_class = CustomIndexView
    list_display = (
        "title",
        "web_body",
        "subtitle",
        "wa_body",
        "mess_body",
        "replies",
        "trigger",
        "tag",
        "related_pages",
        "parental",
    )
    list_filter = ("locale",)
    search_fields = ("title", "body")
    list_export = ("locale", "title")

    def replies(self, obj):
        return [x for x in obj.quick_replies.all()]

    replies.short_description = "Quick Replies"

    def trigger(self, obj):
        return [x for x in obj.triggers.all()]

    trigger.short_description = "Triggers"

    def tag(self, obj):
        return [x for x in obj.tags.all()]

    tag.short_description = "Tags"

    def wa_body(self, obj):
        return [m.value["message"] for m in obj.whatsapp_body]

    wa_body.short_description = "Whatsapp Body"

    def mess_body(self, obj):
        body = ""
        for message in obj.messenger_body:
            body = body + message.value["message"]
        return body

    mess_body.short_description = "Messenger Body"

    def web_body(self, obj):
        return obj.body

    web_body.short_description = "Web Body"

    def parental(self, obj):
        return obj.get_parent()

    parental.short_description = "Parent"


class OrderedContentSetAdmin(ModelAdmin):
    model = OrderedContentSet
    menu_icon = "order"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("name", "profile_fields", "pages")
    list_export = ("name", "profile_field", "page")
    search_fields = ("name", "profile_fields")

    def profile_field(self, obj):
        return [f"{x.block_type}:{x.value}" for x in obj.profile_fields]

    profile_field.short_description = "Profile Fields"

    def page(self, obj):
        return [p.value.slug for p in obj.pages]

    page.short_description = "Page Slugs"


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(ContentPageAdmin)
modeladmin_register(OrderedContentSetAdmin)
