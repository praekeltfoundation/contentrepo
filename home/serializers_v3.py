from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail import blocks
from wagtail.api.v2.serializers import PageSerializer
from wagtail.api.v2.utils import get_object_detail_url

from home.models import Assessment, ContentPage, WhatsAppTemplate


def format_title(page, request):
    channel = ""
    title_to_return = ""
    if "channel" in request.query_params:
        channel = request.query_params.get("channel", "").lower()

    if channel != "" and channel != "web":
        title_to_return = getattr(page, f"{channel}_title")

    if title_to_return == "":
        title_to_return = page.title

    return title_to_return


def get_related_page_as_content_page(page):
    if page.id:
        return ContentPage.objects.filter(id=page.id).first()


def format_related_pages(page, request):
    related_pages = []
    channel = ""
    if "channel" in request.query_params:
        channel = request.query_params.get("channel", "").lower()

    for related in page.related_pages:
        related_page = get_related_page_as_content_page(related.value)
        if channel != "" and channel != "web":
            channel_title = getattr(related_page, f"{channel}_title")
            if channel_title == "":
                channel_title = related_page.title
            related_pages.append(
                {
                    "slug": related_page.slug,
                    "title": channel_title,
                }
            )

        else:
            related_pages.append(
                {
                    "slug": related_page.slug,
                    "title": related_page.title,
                }
            )

    return related_pages


def format_generic_channel_body(page, channel):
    if channel == "web":
        channel_body = page.body
    else:
        channel_body = getattr(page, f"{channel}_body")

        if channel_body._raw_data != []:
            try:
                return OrderedDict(
                    [
                        ("text", channel_body._raw_data[0]["value"]["message"]),
                    ]
                )
            except IndexError:
                raise ValidationError("The requested message does not exist")
        else:
            return OrderedDict(
                [
                    ("text", []),
                ]
            )


def format_messages(page, request):
    channel = ""

    if "channel" in request.query_params:
        channel = request.query_params.get("channel", "").lower()
        return_drafts = request.query_params.get("return_drafts", "").lower() == "true"

        if getattr(page, f"enable_{channel}") or return_drafts:
            if channel == "whatsapp":
                return format_whatsapp_body_V3(page)
            else:
                return format_generic_channel_body(page, channel)

    return OrderedDict([("text", page.body._raw_data)])


def format_buttons_and_list_items(given_list: blocks.StreamValue.StreamChild):
    button_dicts = []

    for button in given_list:
        button_dict = {"type": button["type"], "title": button["value"]["title"]}
        if button["type"] == "go_to_page":
            if button["value"].get("page") is None:
                continue
            content_page = ContentPage.objects.get(id=button["value"].get("page"))

            button_dict["slug"] = content_page.slug
        if button["type"] == "go_to_form":
            # Exclude buttons that has deleted forms that they are linked to it
            if button["value"].get("form") is None:
                continue

            assessment = Assessment.objects.get(id=button["value"].get("form"))
            button_dict["slug"] = assessment.slug

        button_dicts.append(button_dict)

    return button_dicts


def format_example_values(given_list: blocks.StreamValue.StreamChild):
    example_values = list(given_list)
    string_list = [d["value"] for d in example_values]
    return string_list


def format_variation_messages(given_list: blocks.list_block.ListValue):
    variation_messages = []
    for var in given_list:
        variation_messages.append(
            {
                "profile_field": var["variation_restrictions"].raw_data[0]["type"],
                "value": var["variation_restrictions"].raw_data[0]["value"],
                "message": var["message"],
            }
        )
    return variation_messages


def format_whatsapp_body_V3(content_page):
    message_number = 0
    messages = []

    for block in content_page.whatsapp_body:
        message_number += 1  # noqa: SIM113

        if str(block.block_type) == "Whatsapp_Template":
            template = block.value

            messages.append(
                OrderedDict(
                    [
                        ("type", block.block_type),
                        ("slug", template.slug),
                        # TODO: Add test for this image check
                        ("image", template.image.id if template.image else None),
                        ("media", None),
                        ("document", None),
                        ("text", template.message),
                        (
                            "buttons",
                            format_buttons_and_list_items(template.buttons.raw_data),
                        ),
                        (
                            "example_values",
                            format_example_values(template.example_values.raw_data),
                        ),
                        ("category", template.category),
                        ("submission_name", template.submission_name),
                        ("submission_status", template.submission_status),
                        ("submission_result", template.submission_result),
                    ]
                )
            )

        elif str(block.block_type) == "Whatsapp_Message":
            message = block.value

            image = message["image"]
            image = image.id if image is not None else None

            media = message["media"]
            media = media.id if media is not None else None

            document = message["document"]
            document = document.id if document is not None else None

            messages.append(
                OrderedDict(
                    [
                        ("type", block.block_type),
                        ("image", image),
                        ("media", media),
                        ("document", document),
                        ("text", message["message"]),
                        (
                            "buttons",
                            format_buttons_and_list_items(message["buttons"].raw_data),
                        ),
                        (
                            "list_items",
                            format_buttons_and_list_items(
                                message["list_items"].raw_data
                            ),
                        ),
                        ("list_title", message["list_title"]),
                        (
                            "variation_messages",
                            format_variation_messages(message["variation_messages"]),
                        ),
                    ]
                )
            )
        else:
            # TODO: Exclude from coverage, or remove this code.  Code unreachable unless we add a new block type
            raise Exception("Unknown Block Type detected")

    return messages


def format_detail_url(obj, request):
    router = request.wagtailapi_router
    detail_url = get_object_detail_url(router, request, type(obj), obj.slug)
    query_params = request.query_params
    if query_params:
        detail_url = (
            f"{detail_url}?{'&'.join([f'{k}={v}' for k, v in query_params.items()])}"
        )
    return detail_url


class ContentPageSerializerV3(PageSerializer):
    title = serializers.SerializerMethodField()
    slug = serializers.SlugField(read_only=True)
    messages = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()
    related_pages = serializers.SerializerMethodField()
    meta_fields = []

    class Meta:
        model = ContentPage
        fields = [
            "slug",
            "detail_url",
            "locale",
            "title",
            "subtitle",
            "messages",
            "tags",
            "triggers",
            "has_children",
            "related_pages",
        ]

    def get_title(self, obj):
        return format_title(page=obj, request=self.context["request"])

    def get_detail_url(self, obj):
        return format_detail_url(obj=obj, request=self.context["request"])

    def get_messages(self, obj):
        return format_messages(page=obj, request=self.context["request"])

    def get_related_pages(self, obj):
        return format_related_pages(page=obj, request=self.context["request"])


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    locale = serializers.CharField(source="locale.language_code")
    revision = serializers.IntegerField(source="get_latest_revision.id")
    buttons = serializers.SerializerMethodField()
    example_values = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()

    meta_fields = []

    class Meta:
        model = WhatsAppTemplate
        fields = [
            "slug",
            "detail_url",
            "locale",
            "category",
            "image",
            "message",
            "example_values",
            "buttons",
            "revision",
            "status",
            "submission_name",
            "submission_status",
            "submission_result",
        ]

    def get_buttons(self, obj):
        return format_buttons_and_list_items(obj.buttons.raw_data)

    def get_example_values(self, obj):
        return format_example_values(obj.example_values.raw_data)

    def get_detail_url(self, obj):
        return format_detail_url(obj=obj, request=self.context["request"])
