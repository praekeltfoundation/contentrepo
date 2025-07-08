from collections import OrderedDict
from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from wagtail.api.v2.serializers import (
    BaseSerializer,
    PageLocaleField,
    PageSerializer,
)
from wagtail.api.v2.utils import get_object_detail_url

from home.models import ContentPage, ContentPageRating, PageView, WhatsAppTemplate


class TitleField(serializers.Field):
    """
    Serializes the "Title" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        request = self.context["request"]
        return title_field_representation(page, request)


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


class SubtitleField(serializers.Field):
    """
    Serializes the "Subtitle" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        return subtitle_field_representation(page)


def subtitle_field_representation(page):
    return page.subtitle


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


def format_whatsapp_template_message(message_index, content_page) -> dict[str, Any]:
    block = content_page.whatsapp_body._raw_data[message_index]
    wa_template = WhatsAppTemplate.objects.get(id=block["value"])

    text = {
        "id": str(wa_template.id),
        # Even though this is technically of type a Whatsapp_Template, we "pretend" this is a Whatsapp_Message object
        # to retain the v2 api behaviour. We also return some fields as null or empty values, for the same reason
        "type": "Whatsapp_Message",
        "value": {
            "image": wa_template.image.id if wa_template.image else "",
            "media": None,
            "footer": "",
            "buttons": wa_template.buttons._raw_data,
            "message": wa_template.message,
            "document": None,
            "list_items": [],
            "list_title": "",
            "next_prompt": "",
            "example_values": wa_template.example_values._raw_data,
            "variation_messages": [],
        },
    }
    return text


def format_whatsapp_message(message_index, content_page, platform):
    text = content_page.whatsapp_body._raw_data[message_index]

    if str(text["type"]) == "Whatsapp_Message":
        # Flattens the variation_messages field in the whatsapp message
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

        # For backwards compatibility we are exposing the new format under list_items_v2, and maintaining list_items the way it was.
        # For example:

        if text["value"]["list_items"]:
            text["value"]["list_items_v2"] = text["value"]["list_items"]

            current_list_items = text["value"]["list_items"]
            list_items = [
                {"id": item["id"], "type": "item", "value": item["value"]["title"]}
                for item in current_list_items
            ]
            text["value"]["list_items"] = list_items

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
        return body_field_representation(page, request)


def body_field_representation(page: Any, request: Any) -> Any:
    if "message" in request.GET:
        try:
            message = int(request.GET["message"]) - 1
        except ValueError:
            raise ValidationError(
                "Please insert a positive integer for message in " "the query string"
            )
    else:
        message = 0

    if "whatsapp" in request.GET and (
        page.enable_whatsapp is True
        or ("qa" in request.GET and request.GET["qa"].lower() == "true")
    ):
        if page.whatsapp_body != []:
            try:
                api_body: OrderedDict[str, Any] = OrderedDict()
                api_body.update(
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
                    ]
                )
                # if it's a template, we need to get the template content
                block = page.whatsapp_body._raw_data[message]

                if block["type"] == "Whatsapp_Template":
                    template = WhatsAppTemplate.objects.get(id=block["value"])

                    api_body.update(
                        [
                            (
                                "text",
                                format_whatsapp_template_message(message, page),
                            ),
                            ("revision", page.get_latest_revision().id),
                            ("is_whatsapp_template", True),
                            ("whatsapp_template_name", template.submission_name),
                            (
                                "whatsapp_template_category",
                                template.category,
                            ),
                        ]
                    )

                elif block["type"] == "Whatsapp_Message":
                    # Get the formatted message
                    formatted_message = format_whatsapp_message(
                        message, page, "whatsapp"
                    )

                    # If in QA mode, modify the message
                    if "qa" in request.GET and request.GET["qa"].lower() == "true":
                        latest_revision = (
                            page.revisions.order_by("-created_at").first().as_object()
                        )
                        if (
                            isinstance(formatted_message, dict)
                            and "value" in formatted_message
                            and "message" in formatted_message["value"]
                        ):
                            formatted_message["value"][
                                "message"
                            ] = latest_revision.whatsapp_body.raw_data[message][
                                "value"
                            ][
                                "message"
                            ]  # Your modified message
                    api_body.update(
                        [
                            (
                                "text",
                                formatted_message,
                            ),
                            ("revision", page.get_latest_revision().id),
                            ("is_whatsapp_template", False),
                            ("whatsapp_template_name", ""),
                            ("whatsapp_template_category", "UTILITY"),
                        ]
                    )

                return api_body
            except IndexError:
                raise ValidationError("The requested message does not exist")
    elif "sms" in request.GET and (
        page.enable_sms is True
        or ("qa" in request.GET and request.GET["qa"].lower() == "true")
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
        or ("qa" in request.GET and request.GET["qa"].lower() == "true")
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
        or ("qa" in request.GET and request.GET["qa"].lower() == "true")
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
        or ("qa" in request.GET and request.GET["qa"].lower() == "true")
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

    def to_representation(self, page):
        request = self.context["request"]
        return related_pages_field_representation(page, request)


def get_related_page_as_content_page(page):
    if page.id:
        return ContentPage.objects.filter(id=page.id).first()


def related_pages_field_representation(page, request):
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
    # footer = serializers.CharField()

    def to_representation(self, page):
        request = self.context["request"]
        router = self.context["router"]
        return {
            "id": page.id,
            "meta": metadata_field_representation(page, request, router),
            "title": title_field_representation(page, request),
            "subtitle": subtitle_field_representation(page),
            "body": body_field_representation(page, request),
            "tags": [x.name for x in page.tags.all()],
            "triggers": [x.name for x in page.triggers.all()],
            "quick_replies": [x.name for x in page.quick_replies.all()],
            "has_children": has_children_field_representation(page),
            "related_pages": related_pages_field_representation(page, request),
        }


def metadata_field_representation(page, request, router):
    parent = {}
    page_parent = page.get_parent()
    detail_url = get_object_detail_url(router, request, type(page), page.pk)
    if page_parent:
        parent = {
            "id": page_parent.id,
            "meta": {
                "type": page_parent.cached_content_type.app_label
                + "."
                + page_parent.cached_content_type.model_class()._meta.object_name,
                "html_url": page_parent.get_full_url(),
            },
            "title": page_parent.title,
        }
    return {
        "type": page.cached_content_type.app_label
        + "."
        + page.cached_content_type.model_class()._meta.object_name,
        "detail_url": detail_url,
        "html_url": page.get_full_url(),
        "slug": page.slug,
        "show_in_menus": "true" if page.show_in_menus else "false",
        "seo_title": page.seo_title,
        "search_description": page.search_description,
        "first_published_at": page.first_published_at,
        "alias_of": page.alias_of,
        "parent": parent,
        "locale": page.locale.language_code,
    }


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


class OrderedLocaleField(serializers.Field):
    """
    Serializes the "locale" field.
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        return instance.locale.language_code


class OrderedContentSetSerializer(BaseSerializer):
    name = NameField(read_only=True)
    locale = OrderedLocaleField(read_only=True)
    pages = OrderedPagesField(read_only=True)
    profile_fields = ProfileFieldsField(read_only=True)


class QuestionField(serializers.Field):
    """
    Serializes the "question" field.

    Example:
    "question": {
        "id": "f8f4c0d8-5e5e-4b5e-9b5e-5e5e8f4c0d8",
        "question_type": "categorical_question",
        "question": "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
        "semantic_id": "wood-woodchuck"
        "explainer": None,
        "error": "Unknown answer given",
        "min": 100,
        "max": 500,
        "answers": [
            {
                "answer": "Yes",
                "score": 5.0,
                "semantic_id": "woodchuck-chuck-yes"
            }
        ]
    }
    """

    def get_attribute(self, instance):
        return instance

    def to_representation(self, page):
        questions = []

        for question in page.questions.raw_data:
            questions.append(
                {
                    "id": question["id"],
                    "question_type": question["type"],
                    "question": question["value"]["question"],
                    "explainer": question.get("value", {}).get("explainer"),
                    "error": question.get("value", {}).get("error"),
                    "min": question.get("value", {}).get("min"),
                    "max": question.get("value", {}).get("max"),
                    "semantic_id": question.get("value", {}).get("semantic_id"),
                    "answers": [
                        x.get("value", x) for x in question["value"].get("answers", [])
                    ],
                }
            )
        return questions


class AssessmentSerializer(BaseSerializer):
    locale = PageLocaleField(read_only=True)
    questions = QuestionField(read_only=True)
