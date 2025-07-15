import logging
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
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
from wagtail.models import Locale, Page
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


def group_templates(templates_queryset: list[WhatsAppTemplate]) -> list[dict[str, Any]]:
    """Helper function to group templates by slug and collect their locales."""
    templates_by_slug = {}
    for template in templates_queryset:
        if template.slug not in templates_by_slug:
            templates_by_slug[template.slug] = {
                "template": template,
                "locales": set(),
                "templates": [],
            }
        if template.locale:
            templates_by_slug[template.slug]["locales"].add(
                template.locale.get_display_name()
            )
        templates_by_slug[template.slug]["templates"].append(template)

    # Convert to list and sort by slug
    grouped = []
    for _slug, data in templates_by_slug.items():
        data["locales"] = sorted(data["locales"])
        grouped.append(data)

    grouped.sort(key=lambda x: x["template"].slug)
    return grouped


def get_folder_data(folder: WhatsAppTemplateFolder) -> dict[str, Any]:
    """Recursively get folder data with grouped templates."""
    # Get all templates in this folder
    templates = WhatsAppTemplate.objects.filter(folder=folder).select_related("locale")

    # Group templates by slug
    grouped_templates = group_templates(templates)

    # Get all subfolders
    subfolders = WhatsAppTemplateFolder.objects.filter(parent=folder)

    # Process subfolders recursively
    folder_data = {
        "folder": folder,
        "templates": grouped_templates,
        "subfolders": [get_folder_data(sf) for sf in subfolders],
    }

    return folder_data


def template_explorer_view(request: Any) -> Any:
    # Sort the grouped templates
    def get_sort_key(item: dict[str, Any]) -> str:
        template = item["template"]
        if sort_by == "name":
            return template.slug.lower()
        elif sort_by == "type":
            return template.template_type or ""
        elif sort_by == "category":
            return template.get_category_display() or ""
        elif sort_by == "locale":
            return template.locale.get_display_name() if template.locale else ""
        elif sort_by == "status":
            return template.get_status_display() or ""
        elif sort_by == "modified":
            return (
                template.latest_revision.created_at if template.latest_revision else ""
            )
        return ""

    # Process all root folders with their hierarchy
    def sort_folder_templates(folder_data: dict[str, Any]) -> dict[str, Any]:
        folder_data["templates"].sort(key=get_sort_key, reverse=sort_order == "desc")
        for subfolder in folder_data["subfolders"]:
            sort_folder_templates(subfolder)
        return folder_data

    # Get search parameters
    search_query = request.GET.get("q", "").strip()

    # Get sort parameters from request
    sort_by = request.GET.get("sort", "name")
    sort_order = request.GET.get("order", "asc")
    locale_filter = request.GET.get("locale", -1) or -1
    category_filter = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")

    # Define valid sort fields
    valid_sort_fields = {
        "name": "slug",
        "type": "type",
        "category": "category",
        "locale": "locale__language_code",
        "status": "status",
        "modified": "latest_revision__created_at",
    }

    # Default sort field and order
    sort_field = valid_sort_fields.get(sort_by, "slug")
    sort_prefix = "" if sort_order == "asc" else "-"

    # Get all templates and filter by search query
    all_templates = WhatsAppTemplate.objects.all()
    if search_query:
        all_templates = all_templates.filter(Q(slug__icontains=search_query))

    # Get all templates and folders
    all_templates = WhatsAppTemplate.objects.all()
    root_folders = WhatsAppTemplateFolder.objects.filter(parent__isnull=True)

    # Apply filters to templates
    filtered_templates = all_templates
    if locale_filter:
        filtered_templates = filtered_templates.filter(locale__id=locale_filter)
    if category_filter:
        filtered_templates = filtered_templates.filter(category=category_filter)
    if status_filter:
        filtered_templates = filtered_templates.filter(submission_status=status_filter)

    # Search
    if search_query:
        # Filter folders that contain matching templates or match the search query
        folder_ids_with_templates = filtered_templates.values_list(
            "folder_id", flat=True
        )
        root_folders = root_folders.filter(
            Q(name__icontains=search_query) | Q(id__in=folder_ids_with_templates)
        ).distinct()

    # Filter root templates by search and filters
    root_templates = filtered_templates.filter(folder__isnull=True)
    if search_query:
        root_templates = root_templates.filter(Q(slug__icontains=search_query))

    # Group templates by slug
    grouped_templates = []
    for template in root_templates:
        # Get all locales for this template's slug that match the filters
        matching_templates = filtered_templates.filter(slug=template.slug)
        locales = matching_templates.values_list("locale__language_code", flat=True)
        grouped_templates.append({"template": template, "locales": list(locales)})

    # Process folders with filtered templates
    processed_folders = []

    def process_folder(folder_data: dict[str, Any]) -> dict[str, Any] | None:
        """Recursively process a folder and its subfolders."""
        # Filter this folder's templates
        folder_data["templates"] = [
            t
            for t in folder_data["templates"]
            if (
                int(locale_filter) in [inner_t.locale_id for inner_t in t["templates"]]
                or locale_filter == -1
            )
            and (t["template"].category == category_filter or not category_filter)
            and (t["template"].submission_status == status_filter or not status_filter)
        ]

        # Recursively process subfolders
        folder_data["subfolders"] = [
            process_folder(subfolder) for subfolder in folder_data["subfolders"]
        ]
        folder_data["subfolders"] = [
            sf for sf in folder_data["subfolders"] if sf is not None
        ]

        # Only include folders that have templates or non-empty subfolders
        has_content = folder_data["templates"] or any(
            subfolder["templates"] or subfolder["subfolders"]
            for subfolder in folder_data["subfolders"]
        )

        if has_content:
            return sort_folder_templates(folder_data)
        return None

    for folder in root_folders.order_by("name"):
        folder_data = get_folder_data(folder)
        result = process_folder(folder_data)
        if result:
            processed_folders.append(result)

    # Apply sorting to both folders and templates
    if sort_by in valid_sort_fields:
        sort_field = valid_sort_fields[sort_by]
        if sort_order == "desc":
            sort_field = f"-{sort_field}"

        # Sort folders
        for folder_data in processed_folders:
            sort_folder_templates(folder_data)

        # Sort templates
        grouped_templates.sort(key=lambda x: getattr(x["template"], sort_field))
    root_folders = root_folders.order_by(f"{sort_prefix}name")
    root_templates = root_templates.order_by(f"{sort_prefix}{sort_field}")
    root_templates = (
        WhatsAppTemplate.objects.filter(folder__isnull=True)
        .select_related("locale", "latest_revision")
        .order_by(f"{sort_prefix}{sort_field}")
    )

    # Group root templates by slug
    grouped_root_templates = group_templates(root_templates)

    grouped_root_templates.sort(key=get_sort_key, reverse=sort_order == "desc")

    # Get all available locales, categories, and statuses
    # Get all unique locale IDs from templates
    locale_ids = WhatsAppTemplate.objects.values_list("locale", flat=True).distinct()
    # Get the actual Locale objects and their display names
    locales = Locale.objects.filter(id__in=locale_ids)

    categories = WhatsAppTemplate.objects.values_list("category", flat=True).distinct()
    statuses = WhatsAppTemplate.objects.values_list(
        "submission_status", flat=True
    ).distinct()

    # Pass sort parameters to template
    sort_context = {
        "current_sort": sort_by,
        "current_order": sort_order,
        "next_order": "desc" if sort_order == "asc" else "asc",
    }

    context = {
        "root_folders_data": processed_folders,
        "grouped_templates": grouped_root_templates,
        "search_query": search_query,
        "locales": locales,
        "categories": categories,
        "statuses": statuses,
        "locale_filter": locale_filter,
        "category_filter": category_filter,
        "status_filter": status_filter,
    }
    context.update(sort_context)

    return render(
        request,
        "admin/whatsapp_templates/explorer.html",
        context,
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
        # Get the template being moved
        template = WhatsAppTemplate.objects.get(pk=template_id)
        folder_id = request.POST.get("folder")

        # Get all templates with the same slug (across all locales)
        templates_to_move = WhatsAppTemplate.objects.filter(slug=template.slug)

        # Update folder for all templates with the same slug
        if folder_id:
            try:
                folder = WhatsAppTemplateFolder.objects.get(pk=folder_id)
                updated_count = templates_to_move.update(folder=folder)
            except WhatsAppTemplateFolder.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "Folder not found"}, status=400
                )
        else:
            updated_count = templates_to_move.update(folder=None)

        return JsonResponse(
            {
                "status": "success",
                "message": f"Moved {updated_count} template(s) to {'folder' if folder_id else 'root'}",
            }
        )
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
            def is_descendant(
                parent: WhatsAppTemplateFolder, child: WhatsAppTemplateFolder
            ) -> bool:
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
        def update_folder_and_children(
            folder_to_update: WhatsAppTemplateFolder, new_depth: int
        ) -> None:
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
