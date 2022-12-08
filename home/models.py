from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import CheckboxSelectMultiple
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase, TaggedItemBase
from wagtail import blocks
from wagtail.api import APIField
from wagtail.contrib.settings.models import BaseSetting, register_setting
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page, Revision
from wagtail.models.sites import Site
from wagtail_content_import.models import ContentImportMixin
from wagtailmedia.blocks import AbstractMediaChooserBlock

from .constants import AGE_CHOICES, GENDER_CHOICES, RELATIONSHIP_STATUS_CHOICES
from .panels import PageRatingPanel
from .whatsapp import create_whatsapp_template

from wagtail.admin.panels import (  # isort:skip
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)


@register_setting
class SiteSettings(BaseSetting):
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


class MediaBlock(AbstractMediaChooserBlock):
    def render_basic(self, value, context=None):
        pass


def get_valid_profile_values(field):
    site = Site.objects.get(is_default_site=True)
    if site and site.sitesettings:
        profile_values = {}

        for profile_block in site.sitesettings.profile_field_options:
            profile_values[profile_block.block_type] = [b for b in profile_block.value]
        try:
            return profile_values[field]
        except KeyError:
            return []
    return []


def get_gender_choices():
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = {k: v for k, v in GENDER_CHOICES}
    return [(g, choices[g]) for g in get_valid_profile_values("gender")]


def get_age_choices():
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = {k: v for k, v in AGE_CHOICES}
    return [(a, choices[a]) for a in get_valid_profile_values("age")]


def get_relationship_choices():
    # Wrapper for get_profile_field_choices that can be passed as a callable
    choices = {k: v for k, v in RELATIONSHIP_STATUS_CHOICES}
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
        max_lenth=4096,
        help_text="each message cannot exceed 4096 characters.",
    )


class WhatsappBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    document = DocumentChooserBlock(icon="document", required=False)
    media = MediaBlock(icon="media", required=False)
    message = blocks.TextBlock(
        max_lenth=4096, help_text="each message cannot exceed 4096 characters."
    )
    variation_messages = blocks.ListBlock(VariationBlock(), default=[])
    next_prompt = blocks.CharBlock(
        max_length=20, help_text="prompt text for next message", required=False
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class ViberBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    message = blocks.TextBlock(
        max_lenth=7000, help_text="each message cannot exceed 7000 characters."
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class MessengerBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    message = blocks.TextBlock(
        max_lenth=2000, help_text="each message cannot exceed 2000 characters."
    )

    class Meta:
        icon = "user"
        form_classname = "whatsapp-message-block struct-block"


class HomePage(Page):
    subpage_types = [
        "ContentPageIndex",
    ]


class ContentPageIndex(Page):
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


class ContentPage(Page, ContentImportMixin):
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
    enable_messenger = models.BooleanField(
        default=False,
        help_text="When enabled, the API will include the messenger content",
    )
    enable_viber = models.BooleanField(
        default=False, help_text="When enabled, the API will include the viber content"
    )

    # Web page setup
    subtitle = models.CharField(max_length=200, blank=True, null=True)
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
                FieldPanel("title"),
                FieldPanel("subtitle"),
                FieldPanel("body"),
                FieldPanel("include_in_footer"),
            ],
            heading="Web",
        ),
    ]

    # whatsapp page setup
    is_whatsapp_template = models.BooleanField("Is Template", default=False)
    whatsapp_title = models.CharField(max_length=200, blank=True, null=True)
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
                FieldPanel("whatsapp_body"),
            ],
            heading="Whatsapp",
        ),
    ]

    # messenger page setup
    messenger_title = models.CharField(max_length=200, blank=True, null=True)
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
    viber_title = models.CharField(max_length=200, blank=True, null=True)
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
    def whatsapp_template_name(self):
        name = f"{self.whatsapp_title}_{self.get_latest_revision().id}"
        return name.replace(" ", "_")

    @property
    def whatsapp_template_body(self):
        return self.whatsapp_body.raw_data[0]["value"]["message"]

    def clean(self):
        message_with_media_length = 1024
        errors = []
        for message in self.whatsapp_body:
            if (
                (
                    "image" in message.value
                    and "document" in message.value
                    and "media" in message.value
                )
                and (
                    message.value["image"]
                    or message.value["document"]
                    or message.value["media"]
                )
                and len(message.value["message"]) > message_with_media_length
            ):
                errors.append(
                    f"A WhatsApp message with media cannot be longer than {message_with_media_length} characters long, your message is {len(message.value['message'])} characters long"
                )
        if errors:
            raise ValidationError(errors)

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
        response = super().save_revision(
            user,
            submitted_for_moderation,
            approved_go_live_at,
            changed,
            log_action,
            previous_revision,
            clean,
        )
        if settings.WHATSAPP_CREATE_TEMPLATES and self.is_whatsapp_template:
            create_whatsapp_template(
                self.whatsapp_template_name, self.whatsapp_template_body
            )
        return response


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
            ("VIBER", "viber"),
            ("MESSENGER", "messenger"),
            ("WEB", "web"),
        ],
        null=True,
        blank=True,
        default="web",
        max_length=20,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    page = models.ForeignKey(
        ContentPage, related_name="views", null=False, on_delete=models.CASCADE
    )
    revision = models.ForeignKey(
        Revision, related_name="views", null=False, on_delete=models.CASCADE
    )
    message = models.IntegerField(blank=True, default=None, null=True)
    data = models.JSONField(default=dict, blank=True, null=True)
