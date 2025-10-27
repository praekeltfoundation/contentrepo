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

    for related in page.related_pages:
        related_page = get_related_page_as_content_page(related.value)
        related_pages.append(
            {
                "slug": related_page.slug,
                "title": format_title(related_page, request),
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
    if not content_page.whatsapp_body:
        return []

    messages = []
    for block in content_page.whatsapp_body:
        if str(block.block_type) == "Whatsapp_Message":
            message = {}
            message["text"] = block.value["message"]

            # Get just the ID for images and media
            if block.value.get("image"):
                message["image"] = block.value["image"].id if hasattr(block.value["image"], 'id') else block.value["image"]
            if block.value.get("media"):
                message["media"] = block.value["media"].id if hasattr(block.value["media"], 'id') else block.value["media"]

            messages.append(message)

    return messages


def format_detail_url(obj, request):
    router = request.wagtailapi_router

    if not obj.slug:
        # TODO: Add test for pages and templates
        raise Exception(
            f"Error finding detail URL. Blank slug detected for {type(obj)} id={obj.id} {obj} - OBJVars = {vars(obj)}"
        )
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
        depth = 1  # Include related fields

    def to_representation(self, instance):
        request = self.context["request"]
        return_drafts = request.query_params.get("return_drafts", "").lower() == "true"
        if return_drafts:
            return super().to_representation(instance.get_latest_revision().as_object())

        return super().to_representation(instance)

    def get_title(self, obj):
        return format_title(page=obj, request=self.context["request"])

    def get_detail_url(self, obj):
        return format_detail_url(obj=obj, request=self.context["request"])

    def get_messages(self, obj):
        return format_messages(page=obj, request=self.context["request"])

    def get_related_pages(self, obj):
        return format_related_pages(page=obj, request=self.context["request"])


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(default="default-slug")
    locale = serializers.CharField(source="locale.language_code", default="en")
    revision = serializers.IntegerField(source="get_latest_revision.id")
    buttons = serializers.SerializerMethodField()
    example_values = serializers.SerializerMethodField(default=["Example Value 1"])
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

    def to_representation(self, instance):
        request = self.context["request"]
        return_drafts = request.query_params.get("return_drafts", "").lower() == "true"
        if return_drafts:
            return super().to_representation(instance.get_latest_revision().as_object())

        return super().to_representation(instance)

    def get_buttons(self, obj):
        return format_buttons_and_list_items(obj.buttons.raw_data)

    def get_example_values(self, obj):
        return format_example_values(obj.example_values.raw_data)

    def get_detail_url(self, obj):
        return format_detail_url(obj=obj, request=self.context["request"])
