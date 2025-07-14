import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from wagtail import hooks
from wagtail.admin import widgets as wagtailadmin_widgets
from wagtail.admin.menu import AdminOnlyMenuItem, MenuItem
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, TitleFieldPanel
from wagtail.admin.widgets.slug import SlugInput
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.models import Page
from wagtail.snippets.action_menu import ActionMenuItem
from wagtail.snippets.bulk_actions.snippet_bulk_action import SnippetBulkAction
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import (
    Assessment,
    ContentPage,
    OrderedContentSet,
    WhatsAppTemplate,
    WhatsAppTemplateFolder,
)

from .views import (  # isort:skip
    ContentPageReportView,
    CustomIndexView,
    CustomIndexViewAssessment,
    OrderedContentSetUploadView,
    PageViewReportView,
    ContentUploadView,
    AssessmentUploadView,
    CustomIndexViewWhatsAppTemplate,
    WhatsAppTemplateUploadView,
)

from django.utils.translation import gettext_lazy as _
from wagtail.admin.menu import Menu, SubmenuMenuItem

from .whatsapp import submit_to_meta_action

logger = logging.getLogger(__name__)


@hooks.register("before_delete_page")
def prevent_deletion_if_linked(request: Any, page: Page) -> Any:
    """
    Check if the page is a ContentPage and if it has any links to prevent
    the deletion of a page if it is linked to other content.
    """
    if page.content_type.name != ContentPage._meta.verbose_name:
        return
    page_links, orderedcontentset_links, wat_links = page.get_all_links()

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
def get_import_urls() -> list[Any]:
    """
    Create additional admin URLs for various content import views.
    """
    return [
        path("import/", ContentUploadView.as_view(), name="import"),
        path(
            "import_orderedcontentset/",
            OrderedContentSetUploadView.as_view(),
            name="import_orderedcontentset",
        ),
        path(
            "import_assessment/",
            AssessmentUploadView.as_view(),
            name="import_assessment",
        ),
        path(
            "import_whatsapptemplate/",
            WhatsAppTemplateUploadView.as_view(),
            name="import_whatsapptemplate",
        ),
    ]


@hooks.register("register_page_listing_buttons")
def get_import_content_button(
    page: Page, page_perms: Any, is_parent: bool = False, next_url: str | None = None
) -> Any:
    """
    Generate buttons to add to action list for importing content.
    """
    yield wagtailadmin_widgets.PageListingButton(
        "Import Content", reverse("import"), priority=10
    )


@hooks.register("register_reports_menu_item")
def get_stale_content_report_menu_item() -> Any:
    """
    Create a admin only sub menu item for the Stale Content report.
    """
    return AdminOnlyMenuItem(
        "Stale Content",
        reverse("stale_content_report"),
        classname="icon icon-" + ContentPageReportView.header_icon,
        order=700,
    )


@hooks.register("register_admin_urls")
def get_stale_content_report_url() -> list[Any]:
    """
    Create additional URL for the State Content Report.
    """
    return [
        path(
            "reports/stale-content/",
            ContentPageReportView.as_view(),
            name="stale_content_report",
        ),
    ]


@hooks.register("register_reports_menu_item")
def get_page_views_report_menu_item() -> Any:
    """
    Create an admin only sub menu item for the Page Views report.
    """
    return AdminOnlyMenuItem(
        "Page Views",
        reverse("page_view_report"),
        classname="icon icon-doc-empty",
        order=700,
    )


@hooks.register("register_admin_urls")
def get_page_views_report_url() -> list[Any]:
    """
    Create additional URL for the Page Views report.
    """
    return [
        path(
            "reports/page-views/",
            PageViewReportView.as_view(),
            name="page_view_report",
        ),
    ]


@hooks.register("register_admin_urls")
def register_template_explorer_url() -> list[Any]:
    return [
        path(
            "whatsapp-templates/explorer/",
            template_explorer_view,
            name="whatsapp_template_explorer",
        ),
    ]


def template_explorer_view(request: Any) -> Any:
    # Get all root folders (folders with no parent)
    root_folders = WhatsAppTemplateFolder.objects.filter(parent__isnull=True)
    # Get all templates without a folder
    root_templates = WhatsAppTemplate.objects.filter(folder__isnull=True)

    return render(
        request,
        "admin/whatsapp_templates/explorer.html",
        {
            "root_folders": root_folders,
            "root_templates": root_templates,
        },
    )


@hooks.register("register_admin_menu_item")
def register_whatsapp_menu_item() -> Any:
    submenu = Menu(
        items=[
            MenuItem(
                _("WhatsApp Templates"),
                reverse("wagtailsnippets_home_whatsapptemplate:list"),
                icon_name="doc-empty",
            ),
            MenuItem(
                _("WhatsApp Template Explorer"),
                reverse("whatsapp_template_explorer"),
                icon_name="list-ul",
            ),
            MenuItem(
                _("WhatsApp Template Folders"),
                reverse("wagtailsnippets_home_whatsapptemplatefolder:list"),
                icon_name="folder",
            ),
        ]
    )

    return SubmenuMenuItem(
        _("WhatsApp Templates"), submenu, icon_name="mail", order=300
    )


@csrf_exempt
@require_http_methods(["POST"])
def move_template(request: Any, template_id: int) -> Any:
    try:
        template = WhatsAppTemplate.objects.get(pk=template_id)
        folder_id = request.POST.get("folder")

        if folder_id:
            try:
                folder = WhatsAppTemplateFolder.objects.get(pk=folder_id)
                template.folder = folder
            except WhatsAppTemplateFolder.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Folder not found"}, status=400
                )
        else:
            template.folder = None

        template.save(update_fields=["folder"])
        return JsonResponse({"status": "success"})
    except WhatsAppTemplate.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Template not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error moving template {template_id}: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def move_folder(request: Any, folder_id: int) -> Any:
    try:
        folder = WhatsAppTemplateFolder.objects.get(pk=folder_id)
        parent_id = request.POST.get("folder")  # This is the new parent folder ID

        # Prevent moving a folder to be a child of itself
        if parent_id:
            if str(folder.id) == parent_id:
                return JsonResponse(
                    {"status": "error", "message": "Cannot move folder into itself"},
                    status=400,
                )

            # Check if the target folder is a descendant of the current folder
            def is_descendant(parent, child):
                if not parent or not child:
                    return False
                if parent.id == child.id:
                    return True
                if child.parent:
                    return is_descendant(parent, child.parent)
                return False

            target_folder = WhatsAppTemplateFolder.objects.get(pk=parent_id)
            if is_descendant(folder, target_folder):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Cannot move folder into its own descendant",
                    },
                    status=400,
                )

            folder.parent = target_folder
        else:
            folder.parent = None  # Move to root

        # Save the folder with the new parent
        folder.save(update_fields=["parent"])

        # Update the depth for this folder and all its descendants
        def update_folder_and_children(folder_to_update, new_depth):
            folder_to_update.depth = new_depth
            folder_to_update.save(update_fields=["depth"])

            # Update all child folders
            for child in folder_to_update.children.all():
                update_folder_and_children(child, new_depth + 1)

        update_folder_and_children(
            folder, (folder.parent.depth + 1) if folder.parent else 0
        )

        return JsonResponse({"status": "success"})

    except WhatsAppTemplateFolder.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Folder not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Error moving folder {folder_id}: {str(e)}")
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


# Add the URL pattern
@hooks.register("register_admin_urls")
def register_template_urls() -> list[Any]:
    return [
        path(
            "whatsapp-templates/explorer/",
            template_explorer_view,
            name="whatsapp_template_explorer",
        ),
        path(
            "whatsapp-templates/<int:template_id>/move/",
            move_template,
            name="move_whatsapp_template",
        ),
        path(
            "whatsapp-template-folders/<int:folder_id>/move/",
            move_folder,
            name="move_whatsapp_template_folder",
        ),
    ]


class SubmitToMetaMenuItem(ActionMenuItem):
    name = "action-submit-to-meta"
    label = "Submit to Meta"
    icon_name = "globe"

    def get_url(self, context: Any) -> str:
        instance = context["instance"]
        return reverse("submit_to_meta", args=[instance.pk])

    def is_shown(self, context: Any) -> bool:
        return context["view"] == "edit"


@hooks.register("register_snippet_action_menu_item")
def register_submit_to_meta_menu_item(model: Any) -> Any:
    if model == WhatsAppTemplate:
        return SubmitToMetaMenuItem(order=10)
    return None


@hooks.register("register_bulk_action")
class SubmitToMetaBulkAction(SnippetBulkAction):
    display_name = "Submit to Meta"
    aria_label = "Submit selected objects to Meta"
    action_type = "submit_to_meta"
    template_name = (
        "wagtailsnippets/snippets/home/whatsapptemplate/confirm_bulk_submit.html"
    )
    models = [WhatsAppTemplate]

    @classmethod
    def execute_action(cls, objects: Any, **kwargs: Any) -> tuple[int, int]:
        num_parent_objects, num_child_objects = 0, 0
        for obj in objects:
            num_parent_objects += 1
            submit_to_meta_action(obj)
        return num_parent_objects, num_child_objects

    def get_success_message(
        self, num_parent_objects: int, num_child_objects: int
    ) -> str:
        return f"{num_parent_objects} objects have been submitted to Meta"


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
        "slug",
        "language_code",
    )

    export_headings = {"language_code": "Locale"}

    list_filter = ("locale",)
    search_fields = ("name", "profile_fields")


class WhatsAppTemplateAdmin(SnippetViewSet):
    model = WhatsAppTemplate
    body_truncate_size = 200
    icon = "draft"
    menu_order = 200
    add_to_admin_menu = False
    add_to_settings_menu = False
    exclude_from_explorer = False
    list_export = "slug"
    list_display = (
        "slug",
        "get_category_display",
        "locale",
        "status",
        "get_submission_status_display",
    )
    list_filter = ["locale", "tags__name", "category"]
    search_fields = (
        "slug",
        "message",
    )

    index_view_class = CustomIndexViewWhatsAppTemplate

    # class Meta:
    #     filter_overrides = {
    #         ManyToManyField: {
    #             'filter_class': DjangoFilterBackend,
    #             'extra': lambda f: {
    #                 'lookup_expr': 'icontains',
    #             }
    #         },
    #     }

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("slug"),
                FieldPanel("folder"),
                FieldPanel("category"),
                FieldPanel("image"),
                FieldPanel("message"),
                FieldPanel("buttons"),
                FieldPanel("tags"),
                FieldPanel("locale"),
                FieldPanel("example_values"),
                FieldPanel("submission_name", read_only=True),
                FieldPanel("submission_status", read_only=True),
                FieldPanel("submission_result", read_only=True),
            ],
            heading="Whatsapp Template",
        ),
    ]


class AssessmentAdmin(SnippetViewSet):
    menu_label = "CMS Forms"
    model = Assessment
    add_to_admin_menu = True
    list_display = ("title", "slug", "version", "locale")
    search_fields = ("title", "slug", "version")
    list_filter = ("locale",)
    icon = "circle-check"
    menu_order = 300
    list_export = "title"
    index_view_class = CustomIndexViewAssessment

    panels = [
        MultiFieldPanel(
            [
                TitleFieldPanel("title"),
                FieldPanel("slug", widget=SlugInput()),
                FieldPanel("version"),
                FieldPanel("locale"),
                FieldPanel("tags"),
            ],
            heading="Identifiers",
        ),
        MultiFieldPanel(
            [
                FieldPanel("high_result_page"),
                FieldPanel("high_inflection"),
                FieldPanel("medium_result_page"),
                FieldPanel("medium_inflection"),
                FieldPanel("low_result_page"),
                FieldPanel("skip_threshold"),
                FieldPanel("skip_high_result_page"),
            ],
            heading="Results",
        ),
        MultiFieldPanel(
            [
                FieldPanel("generic_error"),
                FieldPanel("questions"),
            ],
            heading="Questions",
        ),
    ]


class WhatsAppTemplateFolderAdmin(SnippetViewSet):
    model = WhatsAppTemplateFolder
    menu_label = "Template Folders"
    icon = "folder"
    menu_order = 300
    add_to_admin_menu = False
    list_display = ["name", "parent", "templates_count"]
    list_filter = ["parent"]
    search_fields = ["name"]


# Now you just need to register your customised ModelAdmin class with Wagtail
modeladmin_register(ContentPageAdmin)
register_snippet(AssessmentAdmin)
register_snippet(OrderedContentSetViewSet)
# Flag for turning on Standalone Whatsapp Templates, still in development
if settings.ENABLE_STANDALONE_WHATSAPP_TEMPLATES:
    register_snippet(WhatsAppTemplateAdmin)
    register_snippet(WhatsAppTemplateFolderAdmin)
