from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.admin.menu import AdminOnlyMenuItem
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.models import Page
from wagtail.models.sites import Site


from .models import ContentPage, OrderedContentSet, SiteSettings

from .views import (  # isort:skip
    ContentPageReportView,
    CustomIndexView,
    OrderedContentSetUploadView,
    PageViewReportView,
    ContentUploadView,
)


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
        classnames="icon icon-" + ContentPageReportView.header_icon,
        order=700,
    )


@hooks.register("construct_homepage_panels")
def create_site_settings(request, page):
    for site in Site.objects.all():
        try:
            SiteSettings.objects.get(site=site)
        except SiteSettings.DoesNotExist:
            SiteSettings.objects.create(site=site)


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
        "slug",
        "title",
        "web_body",
        "subtitle",
        "wa_body",
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
        "messenger_body",
        "viber_body",
        "slug",
    )
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

    def vib_body(self, obj):
        body = ""
        for message in obj.viber_body:
            body = body + message.value["message"]
        return body

    vib_body.short_description = "Viber Body"

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
    list_display = ("name", "profile_fields", "num_pages")
    list_export = ("name", "profile_field", "page")
    search_fields = ("name", "profile_fields")

    def profile_field(self, obj):
        return [f"{x.block_type}:{x.value}" for x in obj.profile_fields]

    profile_field.short_description = "Profile Fields"

    def page(self, obj):
        if obj.pages:
            return [p.value.slug if p.value else "" for p in obj.pages]
        return ["-"]

    page.short_description = "Page Slugs"

    def num_pages(self, obj):
        return len(obj.pages)

    num_pages.short_description = "Number of Pages"


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(ContentPageAdmin)
modeladmin_register(OrderedContentSetAdmin)


@hooks.register("before_edit_page")
def validate_slug_before_edit(request, page):
    if request.POST.get("slug") == page.slug:
        return

    slug = create_unique_slug(request.POST.get("slug"))
    if slug:
        post = request.POST.copy()
        post["slug"] = slug
        request.POST = post


@hooks.register("before_create_page")
def validate_slug_before_create(request, parent_page, page_class):
    slug = create_unique_slug(request.POST.get("slug"))
    if slug:
        post = request.POST.copy()
        post["slug"] = slug
        request.POST = post


def create_unique_slug(slug):
    """
    If the slug already exists in the database, appends a number to the slug to ensure
    that the slug is unique
    """
    if not slug:
        return

    suffix = 1
    candidate_slug = slug
    while Page.objects.filter(slug=candidate_slug).exists():
        suffix += 1
        candidate_slug = f"{slug}-{suffix}"

    return candidate_slug
