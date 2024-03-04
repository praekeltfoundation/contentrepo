import logging
import re

from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase, TaggedItemBase
from wagtail import blocks
from wagtail.api import APIField
from wagtail.blocks import StreamBlockValidationError, StructBlockValidationError
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import DraftStateMixin, Page, Revision, RevisionMixin
from wagtail.models.sites import Site
from wagtail.search import index
from wagtail_content_import.models import ContentImportMixin
from wagtailmedia.blocks import AbstractMediaChooserBlock

from .panels import PageRatingPanel
from .whatsapp import create_whatsapp_template

from .constants import (  # isort:skip
    AGE_CHOICES,
    GENDER_CHOICES,
    RELATIONSHIP_STATUS_CHOICES,
    model,
)
from wagtail.admin.panels import (  # isort:skip
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
    TitleFieldPanel,
)

logger = logging.getLogger(__name__)


class UniqueSlugMixin:
    """
    Ensures that slugs are unique per locale
    """

    def is_slug_available(self, slug):
        pages = Page.objects.filter(
            locale=self.locale_id or self.get_default_locale(), slug=slug
        )
        if self.pk is not None:
            pages = pages.exclude(pk=self.pk)
        return not pages.exists()

    def get_unique_slug(self, slug):
        suffix = 1
        candidate_slug = slug
        while not self.is_slug_available(candidate_slug):
            suffix += 1
            candidate_slug = f"{slug}-{suffix}"
        return candidate_slug

    def clean(self):
        super().clean()

        if not self.is_slug_available(self.slug):
            page = Page.objects.get(locale=self.locale, slug=self.slug)
            raise ValidationError(
                {
                    "slug": _(
                        "The slug '%(page_slug)s' is already in use at '%(page_url)s'"
                    )
                    % {"page_slug": self.slug, "page_url": page.url}
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
    def render_basic(self, value, context=None):
        pass


def get_valid_profile_values(field):
    site = Site.objects.get(is_default_site=True)
    site_settings = SiteSettings.for_site(site)

    profile_values = {}

    for profile_block in site_settings.profile_field_options:
        profile_values[profile_block.block_type] = list(profile_block.value)
    try:
        return profile_values[field]
    except KeyError:
        return []


def get_gender_choices():
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = dict(GENDER_CHOICES)
    return [(g, choices[g]) for g in get_valid_profile_values("gender")]


def get_age_choices():
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = dict(AGE_CHOICES)
    return [(a, choices[a]) for a in get_valid_profile_values("age")]


def get_relationship_choices():
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
        help_text="text for the button, up to 20 characters.",
        validators=(MaxLengthValidator(20),),
    )


class GoToPageButton(blocks.StructBlock):
    title = blocks.CharBlock(
        help_text="text for the button, up to 20 characters.",
        validators=(MaxLengthValidator(20),),
    )
    page = blocks.PageChooserBlock(help_text="page the button should go to")


class WhatsappBlock(blocks.StructBlock):
    MEDIA_CAPTION_MAX_LENGTH = 1024
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
        [("next_message", NextMessageButton()), ("go_to_page", GoToPageButton())],
        required=False,
        max_num=3,
    )
    list_items = blocks.ListBlock(
        blocks.CharBlock(label="Title"),
        default=[],
        help_text="List item title, up to 24 characters.",
        required=False,
        max_num=10,
        validators=(MaxLengthValidator(24)),
    )

    footer = blocks.CharBlock(
        help_text="Footer cannot exceed 60 characters.",
        required=False,
        validators=(MaxLengthValidator(60),),
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"

    def clean(self, value):
        result = super().clean(value)
        num_vars_in_msg = len(re.findall(r"{{\d+}}", result["message"]))
        errors = {}
        example_values = result["example_values"]
        for ev in example_values:
            if "," in ev:
                errors["example_values"] = ValidationError(
                    "Example values cannot contain commas"
                )
        if num_vars_in_msg > 0:
            num_example_values = len(example_values)
            if num_vars_in_msg != num_example_values:
                errors["example_values"] = ValidationError(
                    f"The number of example values provided ({num_example_values}) "
                    f"does not match the number of variables used in the template ({num_vars_in_msg})",
                )

        if (result["image"] or result["document"] or result["media"]) and len(
            result["message"]
        ) > self.MEDIA_CAPTION_MAX_LENGTH:
            errors["message"] = ValidationError(
                "A WhatsApp message with media cannot be longer than "
                f"{self.MEDIA_CAPTION_MAX_LENGTH} characters, your message is "
                f"{len(result['message'])} characters long"
            )

        list_items = result["list_items"]
        for item in list_items:
            if len(item) > 24:
                errors["list_items"] = ValidationError(
                    "List item title maximum charactor is 24 "
                )

        if len(list_items) > 10:
            errors["list_items"] = ValidationError("List item can only add 10 items")

        if errors:
            raise StructBlockValidationError(errors)
        return result


class SMSBlock(blocks.StructBlock):
    message = blocks.TextBlock(
        help_text="each message cannot exceed 160 characters.",
        validators=(MaxLengthValidator(160),),
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

    def clean(self, value):
        result = super().clean(value)
        errors = {}

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
    subpage_types = [
        "ContentPageIndex",
    ]


class ContentPageIndex(UniqueSlugMixin, Page):
    subpage_types = [
        "ContentPage",
    ]

    include_in_homepage = models.BooleanField(default=False)

    @property
    def has_children(self):
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
    class WhatsAppTemplateCategory(models.TextChoices):
        MARKETING = "MARKETING", _("Marketing")
        UTILITY = "UTILITY", _("Utility")

    parent_page_type = [
        "ContentPageIndex",
    ]

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

    embedding = models.JSONField(blank=True, null=True)

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

    @property
    def whatsapp_template_example_values(self):
        example_values = self.whatsapp_body.raw_data[0]["value"].get(
            "example_values", []
        )
        return [v["value"] for v in example_values]

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
    def quick_reply_buttons(self):
        return self.quick_reply_items.all().values_list("tag__name", flat=True)

    @property
    def whatsapp_template_fields(self):
        """
        Returns a tuple of fields that can be used to determine template equality
        """
        return (
            self.whatsapp_template_body,
            sorted(self.quick_reply_buttons),
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
            sorted(self.quick_reply_buttons),
            self.whatsapp_template_image,
            self.whatsapp_template_example_values,
        )

        return self.whatsapp_template_name

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

    def clean(self):
        result = super().clean()
        errors = {}

        # The WA title is needed for all templates to generate a name for the template
        if self.is_whatsapp_template and not self.whatsapp_title:
            errors.setdefault("whatsapp_title", []).append(
                ValidationError("All WhatsApp templates need a title.")
            )
        # The variable check is only for templates
        if self.is_whatsapp_template and len(self.whatsapp_body.raw_data) > 0:
            whatsapp_message = self.whatsapp_body.raw_data[0]["value"]["message"]

            right_mismatch = re.findall(r"(?<!\{){[^{}]*}\}", whatsapp_message)
            left_mismatch = re.findall(r"\{{[^{}]*}(?!\})", whatsapp_message)
            mismatches = right_mismatch + left_mismatch

            if mismatches:
                errors.setdefault("whatsapp_body", []).append(
                    StreamBlockValidationError(
                        {
                            0: StreamBlockValidationError(
                                {
                                    "message": ValidationError(
                                        f"Please provide variables with matching braces. You provided {mismatches}."
                                    )
                                }
                            )
                        }
                    )
                )

            vars_in_msg = re.findall(r"{{(.*?)}}", whatsapp_message)
            non_digit_variables = [var for var in vars_in_msg if not var.isdecimal()]

            if non_digit_variables:
                errors.setdefault("whatsapp_body", []).append(
                    StreamBlockValidationError(
                        {
                            0: StreamBlockValidationError(
                                {
                                    "message": ValidationError(
                                        f"Please provide numeric variables only. You provided {non_digit_variables}."
                                    )
                                }
                            )
                        }
                    )
                )

            # Check variable order
            actual_digit_variables = [var for var in vars_in_msg if var.isdecimal()]
            expected_variables = [
                str(j + 1) for j in range(len(actual_digit_variables))
            ]
            if actual_digit_variables != expected_variables:
                errors.setdefault("whatsapp_body", []).append(
                    StreamBlockValidationError(
                        {
                            0: StreamBlockValidationError(
                                {
                                    "message": ValidationError(
                                        f'Variables must be sequential, starting with "{{1}}". Your first variable was "{actual_digit_variables}"'
                                    )
                                }
                            )
                        }
                    )
                )

        if errors:
            raise ValidationError(errors)

        return result


@receiver(pre_save, sender=ContentPage)
def update_embedding(sender, instance, *args, **kwargs):
    from .word_embedding import preprocess_content_for_embedding

    if not model:
        return

    embedding = {}
    if instance.enable_web:
        content = []
        for block in instance.body:
            content.append(block.value.source)
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["web"] = {"values": [float(i) for i in model.encode(body)]}
    if instance.enable_whatsapp:
        content = []
        for block in instance.whatsapp_body:
            content.append(block.value["message"])
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["whatsapp"] = {"values": [float(i) for i in model.encode(body)]}
    if instance.enable_sms:
        content = []
        for block in instance.sms_body:
            content.append(block.value["message"])
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["sms"] = {"values": [float(i) for i in model.encode(body)]}
    if instance.enable_ussd:
        content = []
        for block in instance.ussd_body:
            content.append(block.value["message"])
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["ussd"] = {"values": [float(i) for i in model.encode(body)]}
    if instance.enable_messenger:
        content = []
        for block in instance.messenger_body:
            content.append(block.value["message"])
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["messenger"] = {"values": [float(i) for i in model.encode(body)]}
    if instance.enable_viber:
        content = []
        for block in instance.viber_body:
            content.append(block.value["message"])
        body = preprocess_content_for_embedding("/n/n".join(content))
        embedding["viber"] = {"values": [float(i) for i in model.encode(body)]}

    instance.embedding = embedding


class OrderedContentSet(DraftStateMixin, RevisionMixin, index.Indexed, models.Model):
    revisions = GenericRelation(
        "wagtailcore.Revision", related_query_name="orderedcontentset"
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
                        ("time", blocks.IntegerBlock(min_value=0, required=False)),
                        (
                            "unit",
                            blocks.ChoiceBlock(
                                choices=[
                                    ("minutes", "Minutes"),
                                    ("hours", "Hours"),
                                    ("days", "Days"),
                                    ("months", "Months"),
                                ],
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
                                required=False,
                            ),
                        ),
                        (
                            "contact_field",
                            blocks.CharBlock(
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

    def status(self):
        return "Live" if self.live else "Draft"

    panels = [
        FieldPanel("name"),
        FieldPanel("profile_fields"),
        FieldPanel("pages"),
    ]

    api_fields = [
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




class WhatsAppTemplate(models.Model):    
    class WhatsAppTemplateCategory(models.TextChoices):
        MARKETING = "MARKETING", _("Marketing")
        UTILITY = "UTILITY", _("Utility")


    name = models.CharField(max_length=512, blank=True, default="")
    category = models.CharField(
        max_length=14,
        choices=WhatsAppTemplateCategory.choices,
        default=WhatsAppTemplateCategory.UTILITY,
    )
    body = StreamField(
        [
            (
                "Whatsapp_Message",
                WhatsappBlock(
                    help_text="Each message will be sent with the text and media"
                ),
            ),
        ],
        blank=True,
        null=True,
        use_json_field=True,
    )

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("name"),
                FieldPanel("is_whatsapp_template"),
                FieldPanel("category"),
                FieldPanel("body"),
            ],
            heading="Whatsapp Template",
        ),
    ]

    
