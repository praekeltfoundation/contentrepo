from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail.api.v2.serializers import BaseSerializer, PageSerializer

from home.models import ContentPage, ContentPageRating, PageView


class TitleField(serializers.Field):
    """
    Serializes the "Title" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        request = self.context["request"]
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


class SubtitleField(serializers.Field):
    """
    Serializes the "Subtitle" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        return page.subtitle


class HasChildrenField(serializers.Field):
    """
    Serializes the "has_children" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
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


def format_whatsapp_message(message_index, content_page, platform):
    # Flattens the variation_messages field in the whatsapp message
    text = content_page.whatsapp_body._raw_data[message_index]
    variation_messages = text["value"].get("variation_messages", [])
    new_var_messages = []
    for var in variation_messages:
        new_var_messages.append(
            {
                "profile_field": var["value"]["variation_restrictions"][0]["type"],
                "value": var["value"]["variation_restrictions"][0]["value"],
                "message": var["value"]["message"],
            }
        )
    text["value"]["variation_messages"] = new_var_messages

    return text


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
        if "message" in request.GET:
            try:
                message = int(request.GET["message"]) - 1
            except ValueError:
                raise ValidationError(
                    "Please insert a positive integer for message in "
                    "the query string"
                )
        else:
            message = 0

        if "whatsapp" in request.GET and (
            page.enable_whatsapp is True
            or ("qa" in request.GET and request.GET["qa"] == "True")
        ):
            if page.whatsapp_body != []:
                try:
                    return OrderedDict(
                        [
                            ("message", message + 1),
                            (
                                "next_message",
                                has_next_message(message, page, "whatsapp"),
                            ),
                            (
                                "previous_message",
                                has_previous_message(message, page, "whatsapp"),
                            ),
                            ("total_messages", len(page.whatsapp_body._raw_data)),
                            (
                                "text",
                                format_whatsapp_message(message, page, "whatsapp"),
                            ),
                            ("revision", page.get_latest_revision().id),
                            ("is_whatsapp_template", page.is_whatsapp_template),
                            ("whatsapp_template_name", page.whatsapp_template_name),
                            (
                                "whatsapp_template_category",
                                page.whatsapp_template_category,
                            ),
                        ]
                    )
                except IndexError:
                    raise ValidationError("The requested message does not exist")
        elif "sms" in request.GET and (
            page.enable_sms is True
            or ("qa" in request.GET and request.GET["qa"] == "True")
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


class RelatedPagesField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def get_related_page_as_content_page(self, page):
        if page.id:
            return ContentPage.objects.filter(id=page.id).first()

    def to_representation(self, page):
        request = self.context["request"]
        related_pages = []
        for related in page.related_pages:
            related_page = self.get_related_page_as_content_page(related.value)
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
                    "id": related.id,
                    "value": related_page.id,
                    "title": title,
                }
            )
        return related_pages


class ContentPageSerializer(PageSerializer):
    title = TitleField(read_only=True)
    subtitle = SubtitleField(read_only=True)
    body = BodyField(read_only=True)
    has_children = HasChildrenField(read_only=True)
    related_pages = RelatedPagesField(read_only=True)


class ContentPageRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPageRating
        fields = "__all__"
        read_only_fields = ("id", "timestamp")


class PageViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageView
        fields = "__all__"
        read_only_fields = ("id", "timestamp")


class NameField(serializers.Field):
    """
    Serializes the "name" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        return instance.name


class PagesField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def get_page_as_content_page(self, page):
        if page.id:
            return ContentPage.objects.filter(id=page.id).first()

    def to_representation(self, instance):
        request = self.context["request"]
        pages = []
        for member in instance.pages:
            page = self.get_page_as_content_page(member.value)
            title = page.title
            if "whatsapp" in request.GET and page.enable_whatsapp is True:
                if page.whatsapp_title:
                    title = page.whatsapp_title
            elif "sms" in request.GET and page.enable_sms is True:
                if page.sms_title:
                    title = page.sms_title
            elif "ussd" in request.GET and page.enable_ussd is True:
                if page.ussd_title:
                    title = page.ussd_title
            elif "messenger" in request.GET and page.enable_messenger is True:
                if page.messenger_title:
                    title = page.messenger_title
            elif "viber" in request.GET and page.enable_viber is True:
                if page.viber_title:
                    title = page.viber_title
            page_data = {
                "id": page.id,
                "title": title,
            }
            if "show_related" in request.GET and bool(request.GET["show_related"]):
                page_data["related_pages"] = [p.value.id for p in page.related_pages]
            if "show_tags" in request.GET and bool(request.GET["show_tags"]):
                page_data["tags"] = [x.name for x in page.tags.all()]

            pages.append(page_data)
        return pages


class OrderedPagesField(serializers.Field):
    def get_attribute(self, instance):
        return instance

    def get_page_as_content_page(self, page):
        if page.id:
            return ContentPage.objects.filter(id=page.id).first()

    def to_representation(self, instance):
        request = self.context["request"]
        pages = []
        for member in instance.pages:
            page = self.get_page_as_content_page(member.value.get("contentpage"))
            title = page.title if page else ""
            if "whatsapp" in request.GET and page.enable_whatsapp is True:
                if page.whatsapp_title:
                    title = page.whatsapp_title
            elif "sms" in request.GET and page.enable_sms is True:
                if page.sms_title:
                    title = page.sms_title
            elif "ussd" in request.GET and page.enable_ussd is True:
                if page.ussd_title:
                    title = page.ussd_title
            elif "messenger" in request.GET and page.enable_messenger is True:
                if page.messenger_title:
                    title = page.messenger_title
            elif "viber" in request.GET and page.enable_viber is True:
                if page.viber_title:
                    title = page.viber_title
            page_data = {
                "id": page.id if page else "",
                "title": title,
                "time": member.value.get("time"),
                "unit": member.value.get("unit"),
                "before_or_after": member.value.get("before_or_after"),
                "contact_field": member.value.get("contact_field"),
            }
            if "show_related" in request.GET and bool(request.GET["show_related"]):
                page_data["related_pages"] = [p.value.id for p in page.related_pages]
            if "show_tags" in request.GET and bool(request.GET["show_tags"]):
                page_data["tags"] = [x.name for x in page.tags.all()]

            pages.append(page_data)
        return pages


class ProfileFieldsField(serializers.Field):
    """
    Serializes the "profile_fields" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        text = []
        for field in instance.profile_fields.raw_data:
            text.append(
                {
                    "profile_field": field["type"],
                    "value": field["value"],
                }
            )
        return text


class OrderedContentSetSerializer(BaseSerializer):
    name = NameField(read_only=True)
    pages = OrderedPagesField(read_only=True)
    profile_fields = ProfileFieldsField(read_only=True)


# TODO: Figure out what fields tomake part of this serialiser
class WhatsAppTemplateSerializer(BaseSerializer):
    name = NameField(read_only=True)
    body = BodyField(read_only=True)
