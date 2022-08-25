from collections import OrderedDict

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail.api.v2.serializers import PageSerializer

from home.models import ContentPageRating, PageView


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
    elif platform == "viber":
        messages_length = len(content_page.viber_body._raw_data) - 1
    elif platform == "messenger":
        messages_length = len(content_page.messenger_body._raw_data) - 1
    if messages_length == message_index:
        return None
    elif messages_length > message_index:
        return message_index + 2


def has_previous_message(message_index, content_page, platform):
    messages_length = None
    if platform == "whatsapp":
        messages_length = len(content_page.whatsapp_body._raw_data) - 1
    elif platform == "viber":
        messages_length = len(content_page.viber_body._raw_data) - 1
    elif platform == "messenger":
        messages_length = len(content_page.messenger_body._raw_data) - 1
    if messages_length != 0 and message_index > 0:
        return message_index


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
        if "whatsapp" in request.GET and page.enable_whatsapp is True:
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
                            ("text", page.whatsapp_body._raw_data[message]),
                            ("revision", page.get_latest_revision().id),
                        ]
                    )
                except IndexError:
                    raise ValidationError("The requested message does not exist")
        elif "messenger" in request.GET and page.enable_messenger is True:
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
        elif "viber" in request.GET and page.enable_viber is True:
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

    def to_representation(self, page):
        request = self.context["request"]
        related_pages = []
        for related in page.related_pages:
            related_page = related.value
            title = related_page.title
            if "whatsapp" in request.GET and related_page.enable_whatsapp is True:
                if related_page.whatsapp_title:
                    title = related_page.whatsapp_title
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
