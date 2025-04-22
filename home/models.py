import logging
import re
from typing import Any

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.forms import CheckboxSelectMultiple
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from taggit.models import ItemBase, TagBase, TaggedItemBase
from wagtail import blocks
from wagtail.admin.panels import (
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
    TitleFieldPanel,
)
from wagtail.api import APIField
from wagtail.blocks import (
    StreamValue,
    StructBlockValidationError,
)
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import (
    DraftStateMixin,
    Locale,
    LockableMixin,
    Page,
    ReferenceIndex,
    Revision,
    RevisionMixin,
    WorkflowMixin,
)
from wagtail.models.sites import Site
from wagtail.search import index
from wagtail.snippets.blocks import SnippetChooserBlock
from wagtail_content_import.models import ContentImportMixin
from wagtailmedia.blocks import AbstractMediaChooserBlock

from .panels import PageRatingPanel
from .whatsapp import (
    TemplateSubmissionClientException,
    TemplateSubmissionServerException,
    TemplateVariableError,
    create_standalone_whatsapp_template,
    create_whatsapp_template,
)

from .constants import (  # isort:skip
    AGE_CHOICES,
    GENDER_CHOICES,
    RELATIONSHIP_STATUS_CHOICES,
)


logger = logging.getLogger(__name__)


class UniqueSlugMixin:
    """
    Ensures that slugs are unique per locale
    """

    def is_slug_available(self, slug: str, PO: type[Page] = Page) -> bool:
        pages = PO.objects.filter(
            locale=self.locale_id or self.get_default_locale(), slug=slug
        )
        if self.pk is not None:
            pages = pages.exclude(pk=self.pk)
        return not pages.exists()

    def get_unique_slug(self, slug: str, PO: type[Page] = Page) -> str:
        suffix = 1
        candidate_slug = slug
        while not self.is_slug_available(candidate_slug, PO):
            suffix += 1
            candidate_slug = f"{slug}-{suffix}"
        return candidate_slug

    def clean(self, PO: type[Page] = Page) -> None:
        super().clean()

        if not self.is_slug_available(self.slug, PO):
            page = PO.objects.get(locale=self.locale, slug=self.slug)
            page_url = page.url if isinstance(page, Page) else page.name
            raise ValidationError(
                {
                    "slug": ValidationError(
                        _(
                            "The slug '%(page_slug)s' is already in use at '%(page_url)s'"
                        ),
                        params={"page_slug": self.slug, "page_url": page_url},
                        code="slug-in-use",
                    )
                }
            )


@register_setting
class SiteSettings(BaseSiteSetting):
    title = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="The branding title shown in the CMS",
    )
    login_message = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="The login message shown on the login page",
    )
    welcome_message = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="The welcome message shown after logging in",
    )
    logo = models.ImageField(blank=True, null=True, upload_to="images")
    favicon = models.ImageField(blank=True, null=True, upload_to="images")
    profile_field_options = StreamField(
        [
            (
                "gender",
                blocks.MultipleChoiceBlock(
                    choices=GENDER_CHOICES, widget=CheckboxSelectMultiple
                ),
            ),
            (
                "age",
                blocks.MultipleChoiceBlock(
                    choices=AGE_CHOICES, widget=CheckboxSelectMultiple
                ),
            ),
            (
                "relationship",
                blocks.MultipleChoiceBlock(
                    choices=RELATIONSHIP_STATUS_CHOICES, widget=CheckboxSelectMultiple
                ),
            ),
        ],
        blank=True,
        null=True,
        help_text="Fields that may be used to restrict content to certain user segments",
        use_json_field=True,
        block_counts={
            "gender": {"max_num": 1},
            "age": {"max_num": 1},
            "relationship": {"max_num": 1},
        },
    )

    first_tab_panels = [
        FieldPanel("title"),
        FieldPanel("login_message"),
        FieldPanel("welcome_message"),
        FieldPanel("logo"),
        FieldPanel("favicon"),
    ]
    second_tab_panels = [
        FieldPanel("profile_field_options"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(first_tab_panels, heading="Branding"),
            ObjectList(second_tab_panels, heading="Profiling"),
        ]
    )


class MediaBlock(AbstractMediaChooserBlock):
    def render_basic(
        self, value: dict[str, Any], context: dict[str, Any] | None = None
    ) -> None:
        pass


def get_valid_profile_values(field: str) -> list[str]:
    site = Site.objects.get(is_default_site=True)
    site_settings = SiteSettings.for_site(site)

    profile_values = {}

    for profile_block in site_settings.profile_field_options:
        profile_values[profile_block.block_type] = list(profile_block.value)
    try:
        return profile_values[field]
    except KeyError:
        return []


def get_gender_choices() -> list[tuple[str, str]]:
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = dict(GENDER_CHOICES)
    return [(g, choices[g]) for g in get_valid_profile_values("gender")]


def get_age_choices() -> list[tuple[str, str]]:
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = dict(AGE_CHOICES)
    return [(a, choices[a]) for a in get_valid_profile_values("age")]


def get_relationship_choices() -> list[tuple[str, str]]:
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = dict(RELATIONSHIP_STATUS_CHOICES)
    return [(r, choices[r]) for r in get_valid_profile_values("relationship")]


class VariationBlock(blocks.StructBlock):
    variation_restrictions = blocks.StreamBlock(
        [
            ("gender", blocks.ChoiceBlock(choices=get_gender_choices)),
            ("age", blocks.ChoiceBlock(choices=get_age_choices)),
            ("relationship", blocks.ChoiceBlock(choices=get_relationship_choices)),
        ],
        required=False,
        min_num=1,
        max_num=1,
        help_text="Restrict this variation to users with this profile value. Valid values must be added to the Site Settings",
        use_json_field=True,
    )
    message = blocks.TextBlock(
        help_text="each message cannot exceed 4096 characters.",
        validators=(MaxLengthValidator(4096),),
    )


class NextMessageButton(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the button, up to 20 characters.",
        validators=(MaxLengthValidator(20),),
    )


class GoToPageButton(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the button, up to 20 characters.",
        validators=(MaxLengthValidator(20),),
    )
    page = blocks.PageChooserBlock(help_text="Page the button should go to")


class GoToFormButton(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the button, up to 20 characters.",
        validators=(MaxLengthValidator(20),),
    )
    form = SnippetChooserBlock(
        "home.Assessment", help_text="Form the button should start"
    )


class NextMessageListItem(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the list item, up to 24 characters.",
        validators=(MaxLengthValidator(24),),
    )


class GoToPageListItem(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the list item, up to 24 characters.",
        validators=(MaxLengthValidator(24),),
    )
    page = blocks.PageChooserBlock(help_text="Page the list item should go to")


class GoToFormListItem(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="Text for the list item, up to 24 characters.",
        validators=(MaxLengthValidator(24),),
    )
    form = SnippetChooserBlock(
        "home.Assessment", help_text="Form the list item should start"
    )


class WhatsappBlock(blocks.StructBlock):
    WHATSAPP_MESSAGE_MAX_LENGTH = 1024
    image = ImageChooserBlock(required=False)
    document = DocumentChooserBlock(icon="document", required=False)
    media = MediaBlock(icon="media", required=False)
    message = blocks.TextBlock(
        help_text="each text message cannot exceed 4096 characters, messages with "
        "media cannot exceed 1024 characters.",
        validators=(MaxLengthValidator(4096),),
    )
    example_values = blocks.ListBlock(
        blocks.CharBlock(
            label="Example Value",
        ),
        default=[],
        label="Variable Example Values",
        help_text="Please add example values for all variables used in a WhatsApp template",
    )
    variation_messages = blocks.ListBlock(VariationBlock(), default=[])
    # TODO: next_prompt is deprecated, and should be removed in the next major version
    next_prompt = blocks.CharBlock(
        help_text="prompt text for next message",
        required=False,
        validators=(MaxLengthValidator(20),),
    )
    buttons = blocks.StreamBlock(
        [
            ("next_message", NextMessageButton()),
            ("go_to_page", GoToPageButton()),
            ("go_to_form", GoToFormButton()),
        ],
        required=False,
        max_num=3,
    )
    list_title = blocks.CharBlock(
        required=False,
        help_text="List title, up to 24 characters.",
        max_length=24,
    )
    list_items = blocks.StreamBlock(
        [
            ("next_message", NextMessageListItem()),
            ("go_to_page", GoToPageListItem()),
            ("go_to_form", GoToFormListItem()),
        ],
        help_text="Items to appear in the list message",
        required=False,
        max_num=10,
    )
    footer = blocks.CharBlock(
        help_text="Footer cannot exceed 60 characters.",
        required=False,
        validators=(MaxLengthValidator(60),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"

    def clean(self, value: dict[str, Any]) -> dict[str, Any]:
        result = super().clean(value)
        errors = {}

        if (result["image"] or result["document"] or result["media"]) and len(
            result["message"]
        ) > self.WHATSAPP_MESSAGE_MAX_LENGTH:
            errors["message"] = ValidationError(
                "A WhatsApp message with media cannot be longer than "
                f"{self.WHATSAPP_MESSAGE_MAX_LENGTH} characters, your message is "
                f"{len(result['message'])} characters long"
            )
        if (result["buttons"] or result["list_items"]) and len(
            result["message"]
        ) > self.WHATSAPP_MESSAGE_MAX_LENGTH:
            errors["message"] = ValidationError(
                "A WhatsApp message with interactive items cannot be longer than "
                f"{self.WHATSAPP_MESSAGE_MAX_LENGTH} characters, your message is "
                f"{len(result['message'])} characters long"
            )

        variation_messages = result["variation_messages"]
        for message in variation_messages:
            if len(message) > 4096:
                errors["variation_messages"] = ValidationError(
                    f"Ensure this variation message has at most 4096 characters, it has {len(message)} characters"
                )
        if errors:
            raise StructBlockValidationError(errors)
        return result


class SMSBlock(blocks.StructBlock):
    message = blocks.TextBlock(
        help_text="each message cannot exceed 459 characters (3 messages).",
        validators=(MaxLengthValidator(459),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class USSDBlock(blocks.StructBlock):
    message = blocks.TextBlock(
        help_text="each message cannot exceed 160 characters.",
        validators=(MaxLengthValidator(160),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"

    def clean(self, value: dict[str, Any]) -> dict[str, Any]:
        result = super().clean(value)
        errors: dict[str, Any] = {}

        if errors:
            raise StructBlockValidationError(errors)
        return result


class ViberBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    message = blocks.TextBlock(
        help_text="each message cannot exceed 7000 characters.",
        validators=(MaxLengthValidator(7000),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class MessengerBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    message = blocks.TextBlock(
        help_text="each message cannot exceed 2000 characters.",
        validators=(MaxLengthValidator(2000),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class HomePage(UniqueSlugMixin, Page):
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "home.ContentPageIndex",
    ]


class ContentPageIndex(UniqueSlugMixin, Page):
    parent_page_types = ["home.HomePage"]
    subpage_types = [
        "home.ContentPage",
    ]

    include_in_homepage = models.BooleanField(default=False)

    @property
    def has_children(self) -> bool:
        return self.get_children_count() > 0

    api_fields = [
        APIField("title"),
        APIField("include_in_homepage"),
        APIField("has_children"),
    ]


class ContentPageTag(TaggedItemBase):
    content_object = ParentalKey(
        "ContentPage", on_delete=models.CASCADE, related_name="tagged_items"
    )


class ContentTrigger(TagBase):
    class Meta:
        verbose_name = "content trigger"
        verbose_name_plural = "content triggers"


class TriggeredContent(ItemBase):
    tag = models.ForeignKey(
        ContentTrigger, related_name="triggered_content", on_delete=models.CASCADE
    )
    content_object = ParentalKey(
        to="home.ContentPage", on_delete=models.CASCADE, related_name="triggered_items"
    )


class ContentQuickReply(TagBase):
    class Meta:
        verbose_name = "quick reply"
        verbose_name_plural = "quick replies"


class QuickReplyContent(ItemBase):
    tag = models.ForeignKey(
        ContentQuickReply, related_name="quick_reply_content", on_delete=models.CASCADE
    )
    content_object = ParentalKey(
        to="home.ContentPage",
        on_delete=models.CASCADE,
        related_name="quick_reply_items",
    )


class ContentPage(UniqueSlugMixin, Page, ContentImportMixin):
    body_truncate_size = 200

    class WhatsAppTemplateCategory(models.TextChoices):
        MARKETING = "MARKETING", _("Marketing")
        UTILITY = "UTILITY", _("Utility")

    parent_page_types = ["home.ContentPageIndex", "home.ContentPage"]

    # general page attributes
    tags = ClusterTaggableManager(through=ContentPageTag, blank=True)
    triggers = ClusterTaggableManager(through="home.TriggeredContent", blank=True)
    quick_replies = ClusterTaggableManager(through="home.QuickReplyContent", blank=True)
    related_pages = StreamField(
        [
            ("related_page", blocks.PageChooserBlock()),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )
    enable_web = models.BooleanField(
        default=False, help_text="When enabled, the API will include the web content"
    )
    enable_whatsapp = models.BooleanField(
        default=False,
        help_text="When enabled, the API will include the whatsapp content",
    )
    enable_sms = models.BooleanField(
        default=False,
        help_text="When enabled, the API will include the SMS content",
    )
    enable_ussd = models.BooleanField(
        default=False,
        help_text="When enabled, the API will include the USSD content",
    )
    enable_messenger = models.BooleanField(
        default=False,
        help_text="When enabled, the API will include the messenger content",
    )
    enable_viber = models.BooleanField(
        default=False, help_text="When enabled, the API will include the viber content"
    )

    # Web page setup
    subtitle = models.CharField(max_length=200, blank=True, default="")
    body = StreamField(
        [
            ("paragraph", blocks.RichTextBlock()),
            ("image", ImageChooserBlock()),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )
    include_in_footer = models.BooleanField(default=False)

    # Web panels
    web_panels = [
        MultiFieldPanel(
            [
                TitleFieldPanel("title"),
                FieldPanel("subtitle"),
                FieldPanel("body"),
                FieldPanel("include_in_footer"),
            ],
            heading="Web",
        ),
    ]

    # whatsapp page setup
    is_whatsapp_template = models.BooleanField("Is Template", default=False)
    whatsapp_template_name = models.CharField(max_length=512, blank=True, default="")
    whatsapp_template_category = models.CharField(
        max_length=14,
        choices=WhatsAppTemplateCategory.choices,
        default=WhatsAppTemplateCategory.UTILITY,
    )
    whatsapp_title = models.CharField(max_length=200, blank=True, default="")
    whatsapp_body = StreamField(
        [
            (
                "Whatsapp_Message",
                WhatsappBlock(
                    help_text="Each message will be sent with the text and media"
                ),
            ),
            (
                "Whatsapp_Template",
                SnippetChooserBlock(
                    "home.WhatsAppTemplate", help_text="WhatsAppTemplate to use"
                ),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )

    # whatsapp panels
    whatsapp_panels = [
        MultiFieldPanel(
            [
                FieldPanel("whatsapp_title"),
                FieldPanel("is_whatsapp_template"),
                FieldPanel("whatsapp_template_category"),
                FieldPanel("whatsapp_body"),
            ],
            heading="Whatsapp",
        ),
    ]

    sms_title = models.CharField(max_length=200, blank=True)
    sms_body = StreamField(
        [
            (
                "SMS_Message",
                SMSBlock(help_text="Each message will be sent with the text"),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )
    # sms panels
    sms_panels = [
        MultiFieldPanel(
            [
                FieldPanel("sms_title"),
                FieldPanel("sms_body"),
            ],
            heading="SMS",
        ),
    ]

    ussd_title = models.CharField(max_length=200, blank=True)
    ussd_body = StreamField(
        [
            (
                "USSD_Message",
                USSDBlock(help_text="Each message will be sent with the text"),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )
    # USSD panels
    ussd_panels = [
        MultiFieldPanel(
            [
                FieldPanel("ussd_title"),
                FieldPanel("ussd_body"),
            ],
            heading="USSD",
        ),
    ]

    # messenger page setup
    messenger_title = models.CharField(max_length=200, blank=True, default="")
    messenger_body = StreamField(
        [
            (
                "messenger_block",
                MessengerBlock(
                    help_text="Each paragraph cannot extend "
                    "over the messenger message "
                    "limit of 2000 characters"
                ),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )

    # messenger panels
    messenger_panels = [
        MultiFieldPanel(
            [
                FieldPanel("messenger_title"),
                FieldPanel("messenger_body"),
            ],
            heading="Messenger",
        ),
    ]

    # viber page setup
    viber_title = models.CharField(max_length=200, blank=True, default="")
    viber_body = StreamField(
        [
            (
                "viber_message",
                ViberBlock(
                    help_text="Each paragraph cannot extend "
                    "over the viber message limit "
                    "of 7000 characters"
                ),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )

    # viber panels
    viber_panels = [
        MultiFieldPanel(
            [
                FieldPanel("viber_title"),
                FieldPanel("viber_body"),
            ],
            heading="Viber",
        ),
    ]

    promote_panels = Page.promote_panels + [
        FieldPanel("tags"),
        FieldPanel("triggers", heading="Triggers"),
        FieldPanel("quick_replies", heading="Quick Replies"),
        PageRatingPanel("Rating"),
        FieldPanel("related_pages"),
    ]
    settings_panels = Page.settings_panels + [
        MultiFieldPanel(
            [
                FieldPanel("enable_web"),
                FieldPanel("enable_whatsapp"),
                FieldPanel("enable_sms"),
                FieldPanel("enable_ussd"),
                FieldPanel("enable_messenger"),
                FieldPanel("enable_viber"),
            ],
            heading="API settings",
        ),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(web_panels, heading="Web"),
            ObjectList(whatsapp_panels, heading="Whatsapp"),
            ObjectList(sms_panels, heading="SMS"),
            ObjectList(ussd_panels, heading="USSD"),
            ObjectList(messenger_panels, heading="Messenger"),
            ObjectList(viber_panels, heading="Viber"),
            ObjectList(promote_panels, heading="Promotional"),
            ObjectList(settings_panels, heading="Settings"),
        ]
    )

    api_fields = [
        APIField("title"),
        APIField("subtitle"),
        APIField("body"),
        APIField("tags"),
        APIField("triggers"),
        APIField("quick_replies"),
        APIField("related_pages"),
        APIField("has_children"),
    ]

    @property
    def has_children(self):
        return self.get_children_count() > 0

    @property
    def page_rating(self):
        return self._calc_avg_rating(self.ratings.all())

    @property
    def view_count(self):
        return self.views.count()

    @property
    def latest_revision_rating(self):
        return self._calc_avg_rating(
            self.ratings.filter(revision=self.get_latest_revision())
        )

    @property
    def whatsapp_template_prefix(self):
        return self.whatsapp_title.lower().replace(" ", "_")

    @property
    def whatsapp_template_body(self):
        return self.whatsapp_body.raw_data[0]["value"]["message"]

    @property
    def whatsapp_template_image(self):
        return self.whatsapp_body.raw_data[0]["value"]["image"]

    def create_whatsapp_template_name(self) -> str:
        return f"{self.whatsapp_template_prefix}_{self.get_latest_revision().pk}"

    def get_descendants(self, inclusive=False):
        return ContentPage.objects.descendant_of(self, inclusive)

    def _calc_avg_rating(self, ratings):
        if ratings:
            helpful = 0
            for rating in ratings:
                if rating.helpful:
                    helpful += 1

            percentage = int(helpful / ratings.count() * 100)
            return f"{helpful}/{ratings.count()} ({percentage}%)"
        return "(no ratings yet)"

    def save_page_view(self, query_params, platform=None):
        if not platform and query_params:
            if "whatsapp" in query_params:
                platform = "whatsapp"
            elif "sms" in query_params:
                platform = "sms"
            elif "ussd" in query_params:
                platform = "ussd"
            elif "messenger" in query_params:
                platform = "messenger"
            elif "viber" in query_params:
                platform = "viber"
            else:
                platform = "web"

        data = {}
        for param, value in query_params.items():
            if param.startswith("data__"):
                key = param.replace("data__", "")
                data[key] = value

        page_view = {
            "revision": self.get_latest_revision(),
            "data": data,
            "platform": f"{platform}",
        }

        if "message" in query_params and query_params["message"].isdigit():
            page_view["message"] = query_params["message"]

        self.views.create(**page_view)

    @property
    def quick_reply_buttons(self) -> list[str]:
        return self.quick_reply_items.all().values_list("tag__name", flat=True)

    @property
    def whatsapp_template_buttons(self) -> list[str]:
        # If Buttons and quick replies are present then Buttons are used
        first_msg = self.whatsapp_body.raw_data[0]["value"]
        if "buttons" in first_msg and first_msg["buttons"]:
            buttons = [b["value"]["title"] for b in first_msg["buttons"]]
            return buttons
        return []

    @property
    def whatsapp_template_fields(self):
        """
        Returns a tuple of fields that can be used to determine template equality
        """
        return (
            self.whatsapp_template_body,
            self.whatsapp_template_buttons,
            self.is_whatsapp_template,
            self.whatsapp_template_image,
            self.whatsapp_template_category,
        )

    def submit_whatsapp_template(self, previous_revision):
        """
        Submits a request to the WhatsApp API to create a template for this content

        Only submits if the create templates is enabled, if the page is a whatsapp
        template, and if the template fields are different to the previous revision
        """
        if not settings.WHATSAPP_CREATE_TEMPLATES:
            return
        if not self.is_whatsapp_template:
            return
        # If there are any missing fields in the previous revision, then carry on
        try:
            previous_revision = previous_revision.as_object()
            previous_revision_fields = previous_revision.whatsapp_template_fields
        except (IndexError, AttributeError):
            previous_revision_fields = ()
        # If there are any missing fields in this revision, then don't submit template
        try:
            if self.whatsapp_template_fields == previous_revision_fields:
                return
        except (IndexError, AttributeError):
            return

        self.whatsapp_template_name = self.create_whatsapp_template_name()

        create_whatsapp_template(
            self.whatsapp_template_name,
            self.whatsapp_template_body,
            str(self.whatsapp_template_category),
            self.locale,
            self.whatsapp_template_buttons,
            self.whatsapp_template_image,
        )

        return self.whatsapp_template_name

    def get_all_links(self):
        page_links = []
        orderedcontentset_links = []
        whatsapp_template_links = []

        usage = ReferenceIndex.get_references_to(self).group_by_source_object()
        for ref in usage:
            for link in ref[1]:
                if link.model_name == "content page":
                    link_type = "Related Page"
                    tab = "#tab-promotional"
                    if link.related_field.name == "whatsapp_body":
                        link_type = "WhatsApp: Go to button"
                        tab = "#tab-whatsapp"

                    page = ContentPage.objects.get(id=link.object_id)
                    url = reverse("wagtailadmin_pages:edit", args=(link.object_id,))
                    page_links.append((url + tab, f"{page} - {link_type}"))

                elif link.model_name == "Ordered Content Set":
                    orderedcontentset = OrderedContentSet.objects.get(id=link.object_id)
                    url = reverse(
                        "wagtailsnippets_home_orderedcontentset:edit",
                        args=(link.object_id,),
                    )
                    orderedcontentset_links.append((url, orderedcontentset.name))
                elif link.model_name == "WhatsApp Template":
                    whatsapp_template = WhatsAppTemplate.objects.get(id=link.object_id)
                    url = reverse(
                        "wagtailsnippets_home_whatsapptemplate:edit",
                        args=(link.object_id,),
                    )
                    whatsapp_template_links.append((url, whatsapp_template.name))
                else:
                    raise Exception("Unknown model link")

        return page_links, orderedcontentset_links, whatsapp_template_links

    def save_revision(
        self,
        user=None,
        submitted_for_moderation=False,
        approved_go_live_at=None,
        changed=True,
        log_action=False,
        previous_revision=None,
        clean=True,
    ):
        previous_revision = self.get_latest_revision()
        revision = super().save_revision(
            user,
            submitted_for_moderation,
            approved_go_live_at,
            changed,
            log_action,
            previous_revision,
            clean,
        )

        try:
            template_name = self.submit_whatsapp_template(previous_revision)
        except Exception:
            # Log the error to sentry and send error message to the user
            logger.exception(
                f"Failed to submit template name:  {self.whatsapp_template_name}"
            )
            raise ValidationError("Failed to submit template")

        if template_name:
            revision.content["whatsapp_template_name"] = template_name
            revision.save(update_fields=["content"])
        return revision

    def short_description(description):
        def set_short_description(func):
            func.short_description = description
            return func

        return set_short_description

    @short_description("Quick Replies")
    def replies(self):
        return list(self.quick_replies.all())

    @short_description("Triggers")
    def trigger(self):
        return list(self.triggers.all())

    @short_description("Tags")
    def tag(self):
        return list(self.tags.all())

    @short_description("Whatsapp Body")
    def wa_body(self) -> str:
        body = (
            "\n".join(
                (
                    m.value["message"]
                    if m.block_type == "Whatsapp_Message"
                    else m.value.message
                )
                for m in self.whatsapp_body
            )
            if self.whatsapp_body
            else ""
        )
        return truncatechars(str(body), self.body_truncate_size)

    @short_description("SMS Body")
    def sms_body_message(self):
        body = (
            "\n".join(m.value["message"] for m in self.sms_body)
            if self.sms_body
            else ""
        )
        return truncatechars(str(body), self.body_truncate_size)

    @short_description("USSD Body")
    def ussd_body_message(self):
        body = (
            "\n".join(m.value["message"] for m in self.ussd_body)
            if self.ussd_body
            else ""
        )
        return truncatechars(str(body), self.body_truncate_size)

    @short_description("Messenger Body")
    def mess_body(self):
        body = "\n".join(m.value["message"] for m in self.messenger_body)
        return truncatechars(str(body), self.body_truncate_size)

    @short_description("Viber Body")
    def vib_body(self):
        body = "\n".join(m.value["message"] for m in self.viber_body)
        return truncatechars(str(body), self.body_truncate_size)

    @short_description("Web Body")
    def web_body(self):
        return truncatechars(str(self.body), self.body_truncate_size)

    @short_description("Parent")
    def parental(self):
        return self.get_parent()

    def clean(self):
        result = super().clean(Page)
        errors = {}

        # Clean the whatsapp body to remove hidden characters
        if self.whatsapp_body and isinstance(self.whatsapp_body, StreamValue):
            for block in self.whatsapp_body:
                if block.block_type == "Whatsapp_Message":
                    message = block.value["message"]
                    cleaned_message = "".join(
                        char
                        for char in message
                        if char.isprintable() or char in "\n\r\t"
                    ).strip()

                    block.value["message"] = cleaned_message

        if errors:
            raise ValidationError(errors)

        return result


def _get_default_locale():
    site = Site.objects.get(is_default_site=True)
    return site.root_page.locale.id


class OrderedContentSet(
    UniqueSlugMixin,
    WorkflowMixin,
    DraftStateMixin,
    LockableMixin,
    RevisionMixin,
    index.Indexed,
    models.Model,
):
    slug = models.SlugField(
        max_length=255,
        help_text="A unique identifier for this ordered content set",
        default="",
    )
    locale = models.ForeignKey(
        to=Locale, on_delete=models.CASCADE, default=_get_default_locale
    )
    revisions = GenericRelation(
        "wagtailcore.Revision", related_query_name="orderedcontentset"
    )
    workflow_states = GenericRelation(
        "wagtailcore.WorkflowState",
        content_type_field="base_content_type",
        object_id_field="object_id",
        related_query_name="orderedcontentset",
        for_concrete_model=False,
    )
    name = models.CharField(
        max_length=255, help_text="The name of the ordered content set."
    )

    def get_gender(self):
        for item in self.get_latest_revision_as_object().profile_fields.raw_data:
            if item["type"] == "gender":
                return item["value"]

    def get_age(self):
        for item in self.get_latest_revision_as_object().profile_fields.raw_data:
            if item["type"] == "age":
                return item["value"]

    def get_relationship(self):
        for item in self.get_latest_revision_as_object().profile_fields.raw_data:
            if item["type"] == "relationship":
                return item["value"]

    def profile_field(self):
        return [
            f"{x.block_type}:{x.value}"
            for x in self.get_latest_revision_as_object().profile_fields
        ]

    profile_field.short_description = "Profile Fields"

    def page(self):
        if self.pages:
            return [
                (self._get_field_value(p, "contentpage", raw=True).slug)
                for p in self.pages
            ]
        return ["-"]

    page.short_description = "Page Slugs"

    def time(self):
        if self.pages:
            return [(self._get_field_value(p, "time")) for p in self.pages]
        return ["-"]

    time.short_description = "Time"

    def unit(self):
        if self.pages:
            return [(self._get_field_value(p, "unit")) for p in self.pages]
        return ["-"]

    unit.short_description = "Unit"

    def before_or_after(self):
        if self.pages:
            return [(self._get_field_value(p, "before_or_after")) for p in self.pages]
        return ["-"]

    before_or_after.short_description = "Before Or After"

    def contact_field(self):
        if self.pages:
            return [(self._get_field_value(p, "contact_field")) for p in self.pages]
        return ["-"]

    contact_field.short_description = "Contact Field"

    def num_pages(self):
        return len(self.pages)

    num_pages.short_description = "Number of Pages"

    def _get_field_value(self, page: Page, field: str, raw: bool = False) -> any:
        try:
            if value := page.value[field]:
                return value if raw else f"{value}"
            else:
                return ""
        except (AttributeError, TypeError):
            return ""

    def latest_draft_profile_fields(self):
        return self.get_latest_revision_as_object().profile_fields

    latest_draft_profile_fields.short_description = "Profile Fields"

    profile_fields = StreamField(
        [
            ("gender", blocks.ChoiceBlock(choices=get_gender_choices)),
            ("age", blocks.ChoiceBlock(choices=get_age_choices)),
            ("relationship", blocks.ChoiceBlock(choices=get_relationship_choices)),
        ],
        help_text="Restrict this ordered set to users with these profile values. Valid values must be added to the Site Settings",
        use_json_field=True,
        block_counts={
            "gender": {"max_num": 1},
            "age": {"max_num": 1},
            "relationship": {"max_num": 1},
        },
        default=[],
        blank=True,
    )
    search_fields = [
        index.SearchField("name"),
        index.SearchField("get_gender"),
        index.SearchField("get_age"),
        index.SearchField("get_relationship"),
    ]
    pages = StreamField(
        [
            (
                "pages",
                blocks.StructBlock(
                    [
                        ("contentpage", blocks.PageChooserBlock()),
                        (
                            "time",
                            blocks.IntegerBlock(
                                min_value=0,
                                required=False,
                                help_text="When should this message be sent? Set the number of  hours, days, months or year.",
                            ),
                        ),
                        (
                            "unit",
                            blocks.ChoiceBlock(
                                choices=[
                                    ("minutes", "Minutes"),
                                    ("hours", "Hours"),
                                    ("days", "Days"),
                                    ("months", "Months"),
                                ],
                                help_text="Choose the unit of time to use.",
                                required=False,
                            ),
                        ),
                        (
                            "before_or_after",
                            blocks.ChoiceBlock(
                                choices=[
                                    ("after", "After"),
                                    ("before", "Before"),
                                ],
                                help_text="Is it ‘before’ or ‘after’ the reference point for your timings, which is set in the contact field below.",
                                required=False,
                            ),
                        ),
                        (
                            "contact_field",
                            blocks.CharBlock(
                                help_text="This is the reference point used to base the timing of message on. For example, edd (estimated date of birth) or dob (date of birth).",
                                required=False,
                            ),
                        ),
                    ]
                ),
            ),
        ],
        use_json_field=True,
        blank=True,
        null=True,
    )

    def num_pages(self):
        return len(self.pages)

    num_pages.short_description = "Number of Pages"

    def status(self) -> str:
        workflow_state = self.workflow_states.last()
        workflow_state_status = workflow_state.status if workflow_state else None

        if self.live:
            if workflow_state_status == "in_progress":
                status = "Live + In Moderation"
            elif self.has_unpublished_changes:
                status = "Live + Draft"
            else:
                status = "Live"
        else:
            if workflow_state_status == "in_progress":
                status = "In Moderation"
            else:
                status = "Draft"

        return status

    panels = [
        FieldPanel("slug"),
        FieldPanel("locale"),
        FieldPanel("name"),
        FieldPanel("profile_fields"),
        FieldPanel("pages"),
    ]

    api_fields = [
        APIField("slug"),
        APIField("locale"),
        APIField("name"),
        APIField("profile_fields"),
        APIField("pages"),
    ]

    def __str__(self):
        """String repr of this snippet."""
        return self.name

    class Meta:  # noqa
        verbose_name = "Ordered Content Set"
        verbose_name_plural = "Ordered Content Sets"

    def clean(self):
        return super().clean(OrderedContentSet)

    def language_code(self):
        return self.locale.language_code


class ContentPageRating(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    page = models.ForeignKey(
        ContentPage, related_name="ratings", null=False, on_delete=models.CASCADE
    )
    revision = models.ForeignKey(
        Revision, related_name="ratings", null=False, on_delete=models.CASCADE
    )
    helpful = models.BooleanField()
    comment = models.TextField(blank=True, default="")
    data = models.JSONField(default=dict, blank=True, null=True)


class PageView(models.Model):
    platform = models.CharField(
        choices=[
            ("WHATSAPP", "whatsapp"),
            ("SMS", "sms"),
            ("USSD", "ussd"),
            ("VIBER", "viber"),
            ("MESSENGER", "messenger"),
            ("WEB", "web"),
        ],
        blank=True,
        default="web",
        max_length=20,
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    page = models.ForeignKey(
        ContentPage, related_name="views", null=False, on_delete=models.CASCADE
    )
    revision = models.ForeignKey(
        Revision, related_name="views", null=False, on_delete=models.CASCADE
    )
    message = models.IntegerField(blank=True, default=None, null=True)
    data = models.JSONField(default=dict, blank=True, null=True)


class AnswerBlock(blocks.StructBlock):
    answer = blocks.TextBlock(help_text="The choice shown to the user for this option")
    score = blocks.FloatBlock(
        help_text="How much to add to the total score if this answer is chosen"
    )
    semantic_id = blocks.TextBlock(help_text="Semantic ID for this answer")
    response = blocks.TextBlock(
        required=False, help_text="The text to show the user if they choose this answer"
    )


class BaseQuestionBlock(blocks.StructBlock):
    question = blocks.TextBlock(help_text="The question to ask the user")
    explainer = blocks.TextBlock(
        required=False,
        help_text="Explainer message which tells the user why we need this question",
    )
    error = blocks.TextBlock(
        required=False,
        help_text="Error message for this question if we don't understand the input",
    )
    semantic_id = blocks.TextBlock(help_text="Semantic ID for this question")


class CategoricalQuestionBlock(BaseQuestionBlock):
    answers = blocks.ListBlock(AnswerBlock())


class AgeQuestionBlock(BaseQuestionBlock):
    answers = None


class MultiselectQuestionBlock(BaseQuestionBlock):
    answers = blocks.ListBlock(AnswerBlock())


class FreeTextQuestionBlock(BaseQuestionBlock):
    answers = None
    error = None


class IntegerQuestionBlock(BaseQuestionBlock):
    min = blocks.IntegerBlock(
        help_text="The minimum value that can be entered",
        default=None,
    )
    max = blocks.IntegerBlock(
        help_text="The maximum value that can be entered",
        default=None,
    )
    answers = None

    def clean(self, value):
        result = super().clean(value)
        min = result["min"]
        max = result["max"]
        if min < 0 or max < 0:
            raise ValidationError("min and max cannot be less than zero")
        if min == max:
            raise ValidationError("min and max values need to be different")
        if min > max:
            raise ValidationError("min cannot be greater than max")

        return result


class YearofBirthQuestionBlock(BaseQuestionBlock):
    answers = None


class AssessmentTag(TaggedItemBase):
    content_object = ParentalKey(
        "Assessment", on_delete=models.CASCADE, related_name="tagged_items"
    )


class Assessment(DraftStateMixin, RevisionMixin, index.Indexed, ClusterableModel):
    class Meta:
        verbose_name = "CMS Form"
        verbose_name_plural = "CMS Forms"

    title = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255, help_text="A unique identifier for this CMS Form"
    )
    version = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="A version number for the question set",
    )
    locale = models.ForeignKey(to=Locale, on_delete=models.CASCADE)
    tags = ClusterTaggableManager(through=AssessmentTag, blank=True)
    high_result_page = models.ForeignKey(
        ContentPage,
        related_name="assessment_high",
        on_delete=models.CASCADE,
        help_text="The page to show the user if they score high",
        blank=True,
        null=True,
    )
    high_inflection = models.FloatField(
        help_text="Any score equal to or above this amount is considered high. Note that this is a percentage-based number.",
        blank=True,
        null=True,
    )
    medium_result_page = models.ForeignKey(
        ContentPage,
        related_name="assessment_medium",
        on_delete=models.CASCADE,
        help_text="The page to show the user if they score medium",
        blank=True,
        null=True,
    )
    medium_inflection = models.FloatField(
        help_text="Any score equal to or above this amount, but lower than the high "
        "inflection, is considered medium. Any score below this amount is considered "
        "low. Note that this is a percentage-based number.",
        blank=True,
        null=True,
    )
    low_result_page = models.ForeignKey(
        ContentPage,
        related_name="assessment_low",
        on_delete=models.CASCADE,
        help_text="The page to show the user if they score low",
        blank=True,
        null=True,
    )
    skip_threshold = models.FloatField(
        help_text="If a user skips equal to or greater than this many questions they will be presented with the skip page",
        default=0,
    )
    skip_high_result_page = models.ForeignKey(
        ContentPage,
        related_name="assessment_high_skip",
        on_delete=models.CASCADE,
        help_text="The page to show a user if they skip a question",
        blank=True,
        null=True,
    )
    generic_error = models.TextField(
        help_text="If no error is specified for a question, then this is used as the "
        "fallback"
    )

    questions = StreamField(
        [
            ("categorical_question", CategoricalQuestionBlock()),
            ("age_question", AgeQuestionBlock()),
            ("multiselect_question", MultiselectQuestionBlock()),
            ("freetext_question", FreeTextQuestionBlock()),
            ("integer_question", IntegerQuestionBlock()),
            ("year_of_birth_question", YearofBirthQuestionBlock()),
        ],
        use_json_field=True,
    )
    _revisions = GenericRelation(
        "wagtailcore.Revision", related_query_name="assessment"
    )

    search_fields = [
        index.SearchField("title"),
        index.AutocompleteField("title"),
        index.SearchField("slug"),
        index.AutocompleteField("slug"),
        index.SearchField("version"),
        index.AutocompleteField("version"),
        index.FilterField("locale"),
    ]

    api_fields = [
        APIField("title"),
        APIField("slug"),
        APIField("version"),
        APIField("high_result_page"),  # noqa: F821
        APIField("high_inflection"),
        APIField("medium_result_page"),
        APIField("medium_inflection"),
        APIField("low_result_page"),
        APIField("skip_threshold"),
        APIField("skip_high_result_page"),
        APIField("generic_error"),
        APIField("questions"),
    ]

    def __str__(self):
        return self.title


class TemplateContentQuickReply(TagBase):
    class Meta:
        verbose_name = "quick reply"
        verbose_name_plural = "quick replies"


class TemplateQuickReplyContent(ItemBase):
    tag = models.ForeignKey(
        TemplateContentQuickReply,
        related_name="template_quick_reply_content",
        on_delete=models.CASCADE,
    )
    content_object = ParentalKey(
        to="home.WhatsAppTemplate",
        on_delete=models.CASCADE,
        related_name="template_quick_reply_items",
    )


class WhatsAppTemplate(
    DraftStateMixin,
    ClusterableModel,
    RevisionMixin,
    index.Indexed,
    models.Model,
):
    class Meta:  # noqa
        verbose_name = "WhatsApp Template"
        verbose_name_plural = "WhatsApp Templates"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "locale"], name="unique_name_locale"
            )
        ]

    class Category(models.TextChoices):
        UTILITY = "UTILITY", _("Utility")
        MARKETING = "MARKETING", _("Marketing")

    class SubmissionStatus(models.TextChoices):
        NOT_SUBMITTED_YET = "NOT_SUBMITTED_YET", _("Not Submitted Yet")
        SUBMITTED = "SUBMITTED", _("Submitted")
        FAILED = "FAILED", _("Failed")

    def get_submission_status_display(self) -> str:
        return self.SubmissionStatus(self.submission_status).label

    get_submission_status_display.admin_order_field = "submission status"
    get_submission_status_display.short_description = "Submission status"

    name = models.CharField(max_length=512, blank=True, default="")
    category = models.CharField(
        max_length=14,
        choices=Category.choices,
        default=Category.MARKETING,
    )

    def get_category_display(self) -> str:
        return self.Category(self.category).label

    get_category_display.admin_order_field = "category"
    get_category_display.short_description = "Category"

    buttons = StreamField(
        [
            ("next_message", NextMessageButton()),
            ("go_to_page", GoToPageButton()),
            ("go_to_form", GoToFormButton()),
        ],
        use_json_field=True,
        null=True,
        max_num=3,
    )

    locale = models.ForeignKey(Locale, on_delete=models.CASCADE, default="")

    image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="image",
    )
    message = models.TextField(
        help_text="Each template message cannot exceed 1024 characters",
        max_length=1024,
    )

    example_values = StreamField(
        [("example_values", blocks.CharBlock(label="Example Value"))],
        blank=True,
        null=True,
        use_json_field=True,
    )

    submission_status = models.CharField(
        max_length=30,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.NOT_SUBMITTED_YET,
    )

    submission_result = models.TextField(
        help_text="The result of submitting the template",
        blank=True,
        max_length=4096,
        default="",
    )
    submission_name = models.TextField(
        help_text="The name of the template that was submitted",
        blank=True,
        max_length=1024,
        default="",
    )

    search_fields = [
        index.SearchField("locale"),
    ]

    @property
    def quick_reply_buttons(self):
        return self.template_quick_reply_items.all().values_list("tag__name", flat=True)

    @property
    def prefix(self):
        return self.name.lower().replace(" ", "_")

    def status(self):
        return "Live" if self.live else "Draft"

    def __str__(self):
        """String repr of this snippet."""
        return self.name

    def save_revision(
        self,
        user: Any | None = None,
        submitted_for_moderation: bool = False,
        approved_go_live_at: Any | None = None,
        changed: bool = True,
        log_action: bool = False,
        previous_revision: Any | None = None,
        clean: bool = True,
    ) -> Any:
        previous_revision = self.get_latest_revision()
        revision = super().save_revision(
            user,
            submitted_for_moderation,
            approved_go_live_at,
            changed,
            log_action,
            previous_revision,
            clean,
        )

        if not settings.WHATSAPP_CREATE_TEMPLATES:
            return revision

        # If there are any missing fields in the previous revision, then carry on
        if previous_revision:
            previous_revision = previous_revision.as_object()
            previous_revision_fields = previous_revision.fields
        else:
            previous_revision_fields = ()

        if self.fields == previous_revision_fields:
            return revision

        self.template_name = self.create_whatsapp_template_name()
        try:
            response_json = create_standalone_whatsapp_template(
                name=self.template_name,
                message=self.message,
                category=self.category,
                locale=self.locale,
                quick_replies=[b["value"]["title"] for b in self.buttons.raw_data],
                image_obj=self.image,
                example_values=[v["value"] for v in self.example_values.raw_data],
            )
            revision.content["name"] = self.name
            revision.content["submission_name"] = self.template_name
            revision.content["submission_status"] = self.SubmissionStatus.SUBMITTED
            revision.content["submission_result"] = (
                f"Success! Template ID = {response_json['id']}"
            )
        except TemplateSubmissionServerException as tsse:
            logger.exception(f"TemplateSubmissionServerException: {str(tsse)} ")
            revision.content["name"] = self.name
            revision.content["submission_name"] = self.template_name
            revision.content["submission_status"] = self.SubmissionStatus.FAILED
            revision.content["submission_result"] = (
                "An Internal Server Error has occurred.  Please try again later or contact developer support"
            )
        except TemplateSubmissionClientException as tsce:
            revision.content["name"] = self.name
            revision.content["submission_name"] = self.template_name
            revision.content["submission_status"] = self.SubmissionStatus.FAILED
            revision.content["submission_result"] = str(tsce)

        revision.save(update_fields=["content"])
        return revision

    def check_matching_braces(self, message: str = message) -> str:
        """
        Check if the number of opening and closing braces match in the message.
        Returns an error message if they don't match, otherwise returns an empty string.
        """
        result = ""
        count_opening_braces = message.count("{{")
        count_closing_braces = message.count("}}")

        if count_opening_braces != count_closing_braces:
            result = f"Please provide variables with matching sets of braces. You provided {count_opening_braces} sets of opening braces, and {count_closing_braces} sets of closing braces."

        return result

    def clean(self) -> None:
        result = super().clean()
        errors: dict[str, list[ValidationError]] = {}

        # The name is needed for all templates to generate a name for the template
        if not self.name:
            errors.setdefault("name", []).append(
                ValidationError("All WhatsApp templates need a name.")
            )

        message = self.message
        try:
            variables = validate_template_variables(message)
            print(f"Variables validated: {variables}")
        except TemplateVariableError as tve:
            errors.setdefault("message", []).append(ValidationError(tve.message))

        example_values = self.example_values.raw_data
        for ev in example_values:
            if "," in ev["value"]:
                errors["example_values"] = ValidationError(
                    "Example values cannot contain commas"
                )
        message = self.message

        # Matches "{1}" and "{11}", not "{{1}", "{a}" or "{1 "
        single_braces = re.findall(r"[^{]{(\d*?)}", message)
        # TODO: Replace with PyParsing

        if single_braces:
            errors.setdefault("message", []).append(
                ValidationError(
                    f"Please provide variables with valid double braces. You provided single braces {single_braces}."
                )
            )

        brace_mismatches = self.check_matching_braces(message)

        if brace_mismatches:
            errors.setdefault("message", []).append(ValidationError(brace_mismatches))
            # TODO: Replace with PyParsing

        vars_in_msg = re.findall(r"{{(.*?)}}", message)
        non_digit_variables = [var for var in vars_in_msg if not var.isdecimal()]

        if non_digit_variables:
            errors.setdefault("message", []).append(
                ValidationError(
                    f"Please provide numeric variables only. You provided {non_digit_variables}."
                )
            )

        # Check variables are sequential
        actual_digit_variables = [var for var in vars_in_msg if var.isdecimal()]
        expected_variables = [str(j + 1) for j in range(len(actual_digit_variables))]
        if actual_digit_variables != expected_variables:
            errors.setdefault("message", []).append(
                {
                    "message": ValidationError(
                        f'Variables must be sequential, starting with "{{1}}". You provided "{actual_digit_variables}"'
                    )
                }
            )

        # Check matching number of placeholders and example values
        if len(example_values) != len(vars_in_msg):
            errors.setdefault("message", []).append(
                {
                    "message": ValidationError(
                        f"Mismatch in number of placeholders and example values. Found {len(vars_in_msg)} placeholder(s) and {len(example_values)} example values."
                    )
                }
            )

        if errors:
            raise ValidationError(errors)

        return result

    @property
    def fields(self):
        """
        Returns a tuple of fields that can be used to determine template equality
        """
        return (
            self.name,
            self.message,
            self.category,
            self.locale,
            sorted(self.quick_reply_buttons),
            self.image,
            self.example_values,
        )

    def create_whatsapp_template_name(self) -> str:
        return f"{self.prefix}_{self.get_latest_revision().pk}"
