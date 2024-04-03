from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.defaultfilters import truncatechars
from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet
from wagtail_modeladmin.options import ModelAdmin, modeladmin_register

from wagtail.admin.panels import FieldPanel, MultiFieldPanel  # isort:skip

from .models import ContentPage, OrderedContentSet, WhatsAppTemplate

from .views import (  # isort:skip
    ContentPageReportView,
    CustomIndexView,
    OrderedContentSetUploadView,
    PageViewReportView,
    ContentUploadView,
)

@hooks.register("before_delete_page")
def before_delete_page(request, page):
    if page.content_type.name != ContentPage._meta.verbose_name:
        return

    page_links, orderedcontentset_links = page.get_all_links()

    if page_links or orderedcontentset_links:
        msg_parts = ["You can't delete this page while it is linked."]

        if page_links:
            msg_parts.append("<br>Content Pages:")
            for link in page_links:
                msg_parts.append(f'<a href="{link[0]}">{link[1]}</a>')

        if orderedcontentset_links:
            msg_parts.append("<br>Ordered Content Sets:")
            for link in orderedcontentset_links:
                msg_parts.append(f'<a href="{link[0]}">{link[1]}</a>')

        messages.warning(request, "<br>".join(msg_parts))
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))


@hooks.register("register_admin_urls")
def register_import_urls():
    return [
        path("import/", ContentUploadView.as_view(), name="import"),
        path(
            "import_orderedcontentset/",
            OrderedContentSetUploadView.as_view(),
            name="import_orderedcontentset",
        ),
    ]


@hooks.register("register_page_listing_buttons")
def page_listing_buttons(page, page_perms, is_parent=False, next_url=None):
    yield wagtailadmin_widgets.PageListingButton(
        "Import Content", reverse("import"), priority=10
    )


@hooks.register("register_reports_menu_item")
def register_stale_content_report_menu_item():
    return AdminOnlyMenuItem(
        "Stale Content",
        reverse("stale_content_report"),
        classname="icon icon-" + ContentPageReportView.header_icon,
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
        classname="icon icon-doc-empty",
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
    body_truncate_size = 200
    model = ContentPage
    menu_label = "ContentPages"
    menu_icon = "pilcrow"
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    index_view_class = CustomIndexView
    list_display = (
        "slug",
        "title",
        "web_body",
        "subtitle",
        "wa_body",
        "sms_body",
        "ussd_body",
        "mess_body",
        "vib_body",
        "replies",
        "trigger",
        "tag",
        "related_pages",
        "parental",
    )
    list_filter = ("locale",)

    search_fields = (
        "title",
        "body",
        "whatsapp_body",
        "sms_body",
        "ussd_body",
        "messenger_body",
        "viber_body",
        "slug",
    )
    list_export = ("locale", "title")

    def replies(self, obj):
        return list(obj.quick_replies.all())

    replies.short_description = "Quick Replies"

    def trigger(self, obj):
        return list(obj.triggers.all())

    trigger.short_description = "Triggers"

    def tag(self, obj):
        return list(obj.tags.all())

    tag.short_description = "Tags"

    def wa_body(self, obj):
        body = "\n".join(m.value["message"] for m in obj.whatsapp_body)
        return truncatechars(str(body), self.body_truncate_size)

    wa_body.short_description = "Whatsapp Body"

    def sms_body(self, obj):
        body = "\n".join(m.value["message"] for m in obj.sms_body)
        return truncatechars(str(body), self.body_truncate_size)

    sms_body.short_description = "SMS Body"

    def ussd_body(self, obj):
        body = "\n".join(m.value["message"] for m in obj.ussd_body)
        return truncatechars(str(body), self.body_truncate_size)

    ussd_body.short_description = "USSD Body"

    def mess_body(self, obj):
        body = "\n".join(m.value["message"] for m in obj.messenger_body)
        return truncatechars(str(body), self.body_truncate_size)

    mess_body.short_description = "Messenger Body"

    def vib_body(self, obj):
        body = "\n".join(m.value["message"] for m in obj.viber_body)
        return truncatechars(str(body), self.body_truncate_size)

    vib_body.short_description = "Viber Body"

    def web_body(self, obj):
        return truncatechars(str(obj.body), self.body_truncate_size)

    web_body.short_description = "Web Body"

    def parental(self, obj):
        return obj.get_parent()

    parental.short_description = "Parent"


class OrderedContentSetViewSet(SnippetViewSet):
    model = OrderedContentSet
    icon = "order"
    menu_order = 200
    add_to_admin_menu = True
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = ("name", "latest_draft_profile_fields", "num_pages", "status")
    list_export = (
        "name",
        "profile_field",
        "page",
        "time",
        "unit",
        "before_or_after",
        "contact_field",
    )
    search_fields = ("name", "profile_fields")


class WhatsAppTemplateViewSet(SnippetViewSet):
    model = WhatsAppTemplate
    body_truncate_size = 200
    icon = "order"
    menu_order = 200
    add_to_admin_menu = True
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_display = (
        "name",
        "category",
        "locale",
        "status",
        "quick_replies",
        "example_values",
        "submission_status",
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("category"),
                FieldPanel("image"),
                FieldPanel("message"),
                FieldPanel("quick_replies", heading="Quick Replies"),
                FieldPanel("locale"),
                FieldPanel("example_values"),
                FieldPanel("submission_status", read_only=True),
                FieldPanel("submission_result", read_only=True),

            ],
            heading="Whatsapp Template",
        ),
    ]

    search_fields = (
        "name",
        "category",
        "message",
        "locale",
    )



register_snippet(OrderedContentSetViewSet)
modeladmin_register(ContentPageAdmin)
# Flag for turning on Standalone Whatsapp Templates, still in development
if settings.ENABLE_STANDALONE_WHATSAPP_TEMPLATES:
    register_snippet(WhatsAppTemplateViewSet)
