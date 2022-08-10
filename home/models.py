from django.conf import settings
from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import ItemBase, TagBase, TaggedItemBase
from wagtail import blocks
from wagtail.api import APIField
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page, PageRevision
from wagtail_content_import.models import ContentImportMixin
from wagtailmedia.blocks import AbstractMediaChooserBlock

from .panels import PageRatingPanel
from .whatsapp import create_whatsapp_template

from wagtail.admin.panels import (  # isort:skip
    FieldPanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)


class MediaBlock(AbstractMediaChooserBlock):
    def render_basic(self, value, context=None):
        pass


class WhatsappBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=False)
    document = DocumentChooserBlock(icon="document", required=False)
    media = MediaBlock(icon="media", required=False)
    message = blocks.TextBlock(
        max_lenth=4096, help_text="each message cannot exceed 4096 characters."
    )
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
    tags = ClusterTaggableManager(through=ContentPageTag)
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

        self.views.create(
            **{
                "revision": self.get_latest_revision(),
                "data": data,
                "platform": f"{platform}",
            }
        )

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
        PageRevision, related_name="ratings", null=False, on_delete=models.CASCADE
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
        PageRevision, related_name="views", null=False, on_delete=models.CASCADE
    )
    data = models.JSONField(default=dict, blank=True, null=True)
