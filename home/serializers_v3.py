from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail import blocks
from wagtail.api.v2.serializers import (
    PageLocaleField,
    PageSerializer,
)

from home.models import Assessment, ContentPage, WhatsAppTemplate

# class TitleField(serializers.Field):
#     """
#     Serializes the "Title" field.
#     """

#     def get_attribute(self, instance):
#         return instance

#     def to_representation(self, page):
#         request = self.context["request"]
#         return title_field_representation(page, request)


def title_field_representation(page, request):
    if "whatsapp" in request.GET and page.enable_whatsapp is True:
        if page.whatsapp_title:
            return page.whatsapp_title
    if "sms" in request.GET and page.enable_sms is True:
        if page.sms_title:
            return page.sms_title
    if "ussd" in request.GET and page.enable_ussd is True:
        if page.ussd_title:
            return page.ussd_title
    elif "messenger" in request.GET and page.enable_messenger is True:
        if page.messenger_title:
            return page.messenger_title
    elif "viber" in request.GET and page.enable_viber is True:
        if page.viber_title:
            return page.viber_title
    return page.title


class HasChildrenField(serializers.Field):
    """
    Serializes the "has_children" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        return has_children_field_representation(page)


def has_children_field_representation(page):
    return page.has_children


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


# def format_whatsapp_template_message(message: str) -> dict[str, Any]:
#     text = {
#         "value": {
#             "variation_messagesss": [],
#             "list_items": [],
#             "list_items_v2": [],
#             "buttons": [],
#             "message": message,
#         }
#     }
#     return text


############# V3 API Only Serializers & Methods Below
class BodyField(serializers.Field):
    """
    Serializes the "body" field.

    Example:
    "body": {
        "message": 1,
        "next_message": 2,
        "previous_message": None,
        "total_messages": 3,
        "text": "body based on platform requested"
    }
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        request = self.context["request"]
        return body_field_representation_V3(page, request)


def body_field_representation_V3(page, request):
    print(f"BV3 - {page.title}")
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
            # TODO: I copied this bit from the import/export file.  Do we want it here as well?
            # Exclude buttons that has deleted pages that they are linked to it
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
    print("Running format_whatsapp_body_V3")
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
                        # ("image", template.image),
                        ("video", None),
                        ("document", None),
                        ("message", template.message),
                        (
                            "buttons",
                            format_buttons_and_list_items(template.buttons.raw_data),
                        ),
                        (
                            "example_values",
                            format_example_values(template.example_values.raw_data),
                        ),
                        ("name", template.name),
                        ("category", template.category),
                        ("submission_name", template.submission_name),
                        ("submission_status", template.submission_status),
                        ("submission_result", template.submission_result),
                        # ("template_id", template.id),
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


class ContentPageSerializerV3(PageSerializer):
    # meta_fields = [
    #     "slug",
    #     "title",
    # ]

    class Meta:
        model = ContentPage
        # fields = [
        #     "title",
        #     "slug",
        # ]
        fields = "__all__"

    title = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    body = BodyField(read_only=True)
    messages = serializers.SerializerMethodField()

    def get_messages(self, obj):
        request = self.context["request"]
        messages = body_field_representation_V3(obj, request)

        return messages


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    # TODO: @Rudi This  Meta fields bit below was added to limit new fields automatically being added to the api automatically but it doesn't seem to do anything
    class Meta:
        model = WhatsAppTemplate
        # fields = ["locale"]
        # fields = ["category", "image", "buttons"]
        # exclude = ["buttons"]

    # TODO: @Rudi - is it a problem using PageLocaleField here, even though this model is not related to Page at all?
    locale = PageLocaleField(read_only=True)
    revision = serializers.IntegerField(source="get_latest_revision.id")
    buttons = serializers.SerializerMethodField()
    example_values = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()

    def get_buttons(self, obj):
        buttons = list(obj.buttons.raw_data)
        for button in buttons:
            if "id" in button:
                del button["id"]
        return buttons

    def get_example_values(self, obj):
        example_values = list(obj.example_values.raw_data)
        string_list = [d["value"] for d in example_values]
        return string_list

    def get_slug(self, obj):
        slug = "TODO:"

        return slug
