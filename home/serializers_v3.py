from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail import blocks
from wagtail.api.v2.serializers import PageSerializer
from wagtail.api.v2.utils import get_object_detail_url

from home.models import Assessment, ContentPage, WhatsAppTemplate


def has_next_message(message_index, content_page, platform):
    messages_length = None
    if platform == "whatsapp":
        messages_length = len(content_page.whatsapp_body._raw_data) - 1
    elif platform == "sms":
        messages_length = len(content_page.sms_body._raw_data) - 1
    elif platform == "ussd":
        messages_length = len(content_page.ussd_body._raw_data) - 1
    elif platform == "viber":
        messages_length = len(content_page.viber_body._raw_data) - 1
    elif platform == "messenger":
        messages_length = len(content_page.messenger_body._raw_data) - 1
    else:
        return None
    if messages_length == message_index:
        return None
    elif messages_length > message_index:
        return message_index + 2


def has_previous_message(message_index, content_page, platform):
    messages_length = None
    if platform == "whatsapp":
        messages_length = len(content_page.whatsapp_body._raw_data) - 1
    elif platform == "sms":
        messages_length = len(content_page.sms_body._raw_data) - 1
    elif platform == "ussd":
        messages_length = len(content_page.ussd_body._raw_data) - 1
    elif platform == "viber":
        messages_length = len(content_page.viber_body._raw_data) - 1
    elif platform == "messenger":
        messages_length = len(content_page.messenger_body._raw_data) - 1
    else:
        return None
    if messages_length != 0 and message_index > 0:
        return message_index


def get_related_page_as_content_page(page):
    if page.id:
        return ContentPage.objects.filter(id=page.id).first()


def format_related_pages(page, request):
    related_pages = []
    for related in page.related_pages:
        related_page = get_related_page_as_content_page(related.value)
        title = related_page.title
        if "whatsapp" in request.GET and related_page.enable_whatsapp is True:
            if related_page.whatsapp_title:
                title = related_page.whatsapp_title
        elif "sms" in request.GET and related_page.enable_sms is True:
            if related_page.sms_title:
                title = related_page.sms_title
        elif "ussd" in request.GET and related_page.enable_ussd is True:
            if related_page.ussd_title:
                title = related_page.ussd_title
        elif "messenger" in request.GET and related_page.enable_messenger is True:
            if related_page.messenger_title:
                title = related_page.messenger_title
        elif "viber" in request.GET and related_page.enable_viber is True:
            if related_page.viber_title:
                title = related_page.viber_title

        related_pages.append(
            {
                "slug": related_page.slug,
                "title": title,
            }
        )
    return related_pages


def format_messages(page, request):
    message = 0
    if "whatsapp" in request.GET and (
        page.enable_whatsapp is True
        or ("qa" in request.GET and request.GET["qa"] == "True")
    ):
        if page.whatsapp_body != []:
            whatsapp_messages = format_whatsapp_body_V3(page)
            return whatsapp_messages

    elif "sms" in request.GET and (
        page.enable_sms is True or ("qa" in request.GET and request.GET["qa"] == "True")
    ):
        if page.sms_body != []:
            try:
                return OrderedDict(
                    [
                        ("message", message + 1),
                        (
                            "next_message",
                            has_next_message(message, page, "sms"),
                        ),
                        (
                            "previous_message",
                            has_previous_message(message, page, "sms"),
                        ),
                        ("total_messages", len(page.sms_body._raw_data)),
                        ("text", page.sms_body._raw_data[message]["value"]),
                    ]
                )
            except IndexError:
                raise ValidationError("The requested message does not exist")
    elif "ussd" in request.GET and (
        page.enable_ussd is True
        or ("qa" in request.GET and request.GET["qa"] == "True")
    ):
        if page.ussd_body != []:
            try:
                return OrderedDict(
                    [
                        ("message", message + 1),
                        (
                            "next_message",
                            has_next_message(message, page, "ussd"),
                        ),
                        (
                            "previous_message",
                            has_previous_message(message, page, "ussd"),
                        ),
                        ("total_messages", len(page.ussd_body._raw_data)),
                        ("text", page.ussd_body._raw_data[message]["value"]),
                    ]
                )
            except IndexError:
                raise ValidationError("The requested message does not exist")
    elif "messenger" in request.GET and (
        page.enable_messenger is True
        or ("qa" in request.GET and request.GET["qa"] == "True")
    ):
        if page.messenger_body != []:
            try:
                return OrderedDict(
                    [
                        ("message", message + 1),
                        (
                            "next_message",
                            has_next_message(message, page, "messenger"),
                        ),
                        (
                            "previous_message",
                            has_previous_message(message, page, "messenger"),
                        ),
                        ("total_messages", len(page.messenger_body._raw_data)),
                        ("text", page.messenger_body._raw_data[message]["value"]),
                    ]
                )
            except IndexError:
                raise ValidationError("The requested message does not exist")
    elif "viber" in request.GET and (
        page.enable_viber is True
        or ("qa" in request.GET and request.GET["qa"] == "True")
    ):
        if page.viber_body != []:
            try:
                return OrderedDict(
                    [
                        ("message", message + 1),
                        ("next_message", has_next_message(message, page, "viber")),
                        (
                            "previous_message",
                            has_previous_message(message, page, "viber"),
                        ),
                        ("total_messages", len(page.viber_body._raw_data)),
                        ("text", page.viber_body._raw_data[message]["value"]),
                    ]
                )
            except IndexError:
                raise ValidationError("The requested message does not exist")

    return OrderedDict(
        [
            ("text", page.body._raw_data),
        ]
    )


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
    # TODO: Can probably do this cleaner?
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
                        ("image", template.image.id),
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

            messages.append(
                OrderedDict(
                    [
                        ("type", block.block_type),
                        ("image", image),
                        ("media", message["media"]),
                        ("document", message["document"]),
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
    title = serializers.CharField(read_only=True)
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

    def get_messages(self, obj):
        return format_messages(page=obj, request=self.context["request"])

    def get_detail_url(self, obj):
        return format_detail_url(obj=obj, request=self.context["request"])

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
