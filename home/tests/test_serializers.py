import pytest
from wagtail.models import Locale  # type: ignore

from home.models import Assessment, ContentPage, HomePage
from home.serializers import (
    QuestionField,
    format_whatsapp_message,
    has_next_message,
    has_previous_message,
)

from .page_builder import (
    MBlk,
    MBody,
    PageBuilder,
    SBlk,
    SBody,
    UBlk,
    UBody,
    VarMsg,
    VBlk,
    VBody,
    WABlk,
    WABody,
)


def create_content_page(
    wa_body_count: int = 1,
    wa_gender_var: list[str] | None = None,
) -> ContentPage:
    """
    Helper function to create pages needed for each test.

    Parameters
    ----------
    wa_body_count : int
        How many WhatsApp message bodies to create on the content page.
    wa_gender_var: list[str]
        Variation restriction
    """
    title = "default page"
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    parent = main_menu

    if wa_gender_var is None:
        wa_gender_var = []

    bodies = [
        MBody(title, [MBlk("Messenger 1"), MBlk("Messenger 2")]),
        SBody(title, [SBlk("SMS 1"), SBlk("SMS 2")]),
        UBody(title, [UBlk("USSD 1"), UBlk("USSD 2")]),
        VBody(title, [VBlk("Viber 1"), VBlk("Viber 2")]),
    ]

    for i in range(wa_body_count):
        wa_body = f"WhatsApp {i+1}"

        variation_messages = [
            VarMsg(f"WhatsApp Varied {i}", gender=gender)
            for i, gender in enumerate(wa_gender_var, 1)
        ]

        bodies.append(
            WABody(title, [WABlk(wa_body, variation_messages=variation_messages)])
        )

    content_page = PageBuilder.build_cp(
        parent=parent,
        slug=title.replace(" ", "-"),
        title=title,
        bodies=bodies,
    )
    return content_page


@pytest.fixture()
def create_form_pages() -> None:
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    PageBuilder.build_cp(
        parent=main_menu,
        slug="high-inflection",
        title="High Inflection",
        bodies=[
            WABody("High Inflection", [WABlk("*High Inflection Page")]),
            MBody("High inflection", [MBlk("High Inflection Page")]),
        ],
    )
    PageBuilder.build_cp(
        parent=main_menu,
        slug="medium-score",
        title="Medium Score",
        bodies=[
            WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
            MBody("Medium Score", [MBlk("Medium Inflection Page")]),
        ],
    )

    PageBuilder.build_cp(
        parent=main_menu,
        slug="low-score",
        title="Low Score",
        bodies=[
            WABody("Low Score", [WABlk("*Low Inflection Page")]),
            MBody("Low Score", [MBlk("Low Inflection Page")]),
        ],
    )

    PageBuilder.build_cp(
        parent=main_menu,
        slug="skip-score",
        title="Skip Score",
        bodies=[
            WABody("Skip Score", [WABlk("*Skip Result Page")]),
            MBody("Skip Score", [MBlk("Skip Result Page")]),
        ],
    )


def create_form_with_fields() -> Assessment:
    """
    Create form with an explainer field and pass it
    through the serializer
    """

    form = Assessment.objects.create(
        title="test page",
        slug="test-page",
        version="v1.0",
        locale=Locale.objects.get(language_code="en"),
        high_result_page=ContentPage.objects.get(slug="high-inflection"),
        high_inflection=3,
        medium_result_page=ContentPage.objects.get(slug="medium-score"),
        medium_inflection=2,
        low_result_page=ContentPage.objects.get(slug="low-score"),
        skip_threshold=2,
        skip_high_result_page=ContentPage.objects.get(slug="skip-score"),
        generic_error="error",
        questions=[
            {
                "type": "categorical_question",
                "value": {
                    "question": "test question",
                    "explainer": "We need to know this",
                    "error": "test error",
                    "answers": [
                        {
                            "id": "eb96ad43-c231-4493-a235-de88e60219ea",
                            "type": "item",
                            "value": {"score": 2.0, "answer": "A"},
                        },
                        {
                            "id": "06576523-e9de-4585-a8cd-08cafd6ef56d",
                            "type": "item",
                            "value": {"score": 1.0, "answer": "B"},
                        },
                        {
                            "id": "c2d71503-92bf-4557-b198-dac64737e27c",
                            "type": "item",
                            "value": {"score": 2.0, "answer": "C"},
                        },
                    ],
                },
            }
        ],
    )
    return form


def create_form_with_missing_fields() -> Assessment:
    """
    Create form without an explainer field and pass it
    through the serializer
    """

    form = Assessment.objects.create(
        title="Test",
        slug="test",
        locale=Locale.objects.get(language_code="en"),
        high_result_page=ContentPage.objects.get(slug="high-inflection"),
        high_inflection=3,
        medium_result_page=ContentPage.objects.get(slug="medium-score"),
        medium_inflection=2,
        low_result_page=ContentPage.objects.get(slug="low-score"),
        skip_threshold=2,
        skip_high_result_page=ContentPage.objects.get(slug="skip-score"),
        generic_error="error",
        questions=[
            {
                "type": "categorical_question",
                "value": {
                    "question": "test question",
                    "error": "test error",
                    "answers": [
                        {
                            "id": "eb96ad43-c231-4493-a235-de88e60219ea",
                            "type": "item",
                            "value": {"score": 2.0, "answer": "A"},
                        },
                        {
                            "id": "06576523-e9de-4585-a8cd-08cafd6ef56d",
                            "type": "item",
                            "value": {"score": 1.0, "answer": "B"},
                        },
                        {
                            "id": "c2d71503-92bf-4557-b198-dac64737e27c",
                            "type": "item",
                            "value": {"score": 2.0, "answer": "C"},
                        },
                    ],
                },
            }
        ],
    )
    return form


@pytest.mark.django_db
class TestHasNextMessage:
    def test_next_messages_whatsapp(self) -> None:
        """
        WhatsApp The next message after the last message is None.
        Index of first message is 0, next message is then message 2 with index 1
        """
        page = create_content_page(wa_body_count=2, wa_gender_var=["female"])
        assert page.whatsapp_body
        assert has_next_message(2, page, "whatsapp") is None
        assert has_next_message(0, page, "whatsapp") == 2

    def test_next_messages_for_viber(self) -> None:
        """
        Viber The next message after the last message is None.
        Next message after 1st message (index 0) is message 2 (index 1)
        """
        page = create_content_page()
        assert page.viber_body
        assert has_next_message(2, page, "viber") is None
        assert has_next_message(0, page, "viber") == 2

    def test_next_messages_for_sms(self) -> None:
        """
        SMS The next message after the last message is None.
        Next message after 1st message (index 0) is message 2 (index 1)
        """
        page = create_content_page()
        assert page.sms_body
        assert has_next_message(2, page, "sms") is None
        assert has_next_message(0, page, "sms") == 2

    def test_next_messages_for_ussd(self) -> None:
        """
        USSD The next message after the last message is None.
        Next message after 1st message (index 0) is message 2 (index 1)
        """
        page = create_content_page()
        assert page.ussd_body
        assert has_next_message(2, page, "ussd") is None
        assert has_next_message(0, page, "ussd") == 2

    def test_next_messages_for_messenger(self) -> None:
        """
        Messenger The next message after the last message is None.
        Next message after 1st message (index 0) is message 2 (index 1)
        """
        page = create_content_page()
        assert page.messenger_body
        assert has_next_message(2, page, "messenger") is None
        assert has_next_message(0, page, "messenger") == 2

    def test_no_next_message_for_invalid_platform(self) -> None:
        """
        Returns none on a platform that is unrecognised
        """
        page = create_content_page()
        assert has_next_message(0, page, "email") is None

    def test_no_next_message_for_null_content_page(self) -> None:
        """
        has_next_message cannot be called on None
        """
        with pytest.raises(AttributeError):
            has_next_message(0, None, "whatsapp")

    def test_no_next_message_empty_body(self) -> None:
        """
        No next message on a page with no whatsapp body
        """
        page = create_content_page(wa_body_count=0)
        assert page.whatsapp_body._raw_data == []
        assert has_next_message(0, page, "whatsapp") is None

    def test_no_next_message_on_last_message(self) -> None:
        """
        last messages' next message is None
        """
        page = create_content_page(wa_body_count=2)
        # first asser that the previous message has a next message,
        # added due to confusing indexing
        assert has_next_message(0, page, "whatsapp") == 2
        # then assert that the last message has no next message
        assert has_next_message(1, page, "whatsapp") is None

    def test_next_message_on_first_message_of_many(self) -> None:
        """
        Page with many whatsapp messages has a next message on the first
        """
        page = create_content_page(wa_body_count=5)
        assert page.whatsapp_body
        assert has_next_message(0, page, "whatsapp") == 2

    def test_next_message_large_input(self) -> None:
        """
        Check next message for very long message sets
        """
        page = create_content_page(wa_body_count=1000)
        assert page.whatsapp_body
        # second to last message has index 998, last message has index 999 but is message 1000
        assert has_next_message(998, page, "whatsapp") == 999 + 1


@pytest.mark.django_db
class TestHasPreviousMessage:
    def test_no_previous_message_on_0_whatsapp_messages(self) -> None:
        """
        First WA message has no previous message
        """
        page = create_content_page(wa_body_count=0)
        assert page.whatsapp_body._raw_data == []
        assert has_previous_message(0, page, "whatsapp") is None

    def test_previous_message_on_whatsapp_message(self) -> None:
        """
        Second WA message has a previous message
        """
        page = create_content_page(wa_body_count=2)
        assert page.whatsapp_body
        assert has_previous_message(1, page, "whatsapp") == 1

    def test_previous_message_on_sms_message(self) -> None:
        """
        Second SMS message has a previous message
        """
        page = create_content_page()
        assert page.sms_body
        assert has_previous_message(1, page, "sms") == 1

    def test_previous_message_on_ussd_message(self) -> None:
        """
        Second USSD message has a previous message
        """
        page = create_content_page()
        assert page.ussd_body
        assert has_previous_message(1, page, "ussd") == 1

    def test_previous_message_on_viber_message(self) -> None:
        """
        Second Viber message has a previous message
        """
        page = create_content_page()
        assert page.viber_body
        assert has_previous_message(1, page, "viber") == 1

    def test_previous_message_on_messenger_message(self) -> None:
        """
        Second Messenger message has a previous message
        """
        page = create_content_page()
        assert page.messenger_body
        assert has_previous_message(1, page, "messenger") == 1

    def test_no_previous_message_on_invalid_platform(self) -> None:
        """
        An invalid plaform type returns None
        """
        page = create_content_page()
        assert has_previous_message(1, page, "email") is None

    def test_previous_message_with_multiple_messages(self) -> None:
        """
        Page with 3 WA messages, 3rd message has previous message
        """
        page = create_content_page(wa_body_count=3)
        assert has_previous_message(2, page, "whatsapp") == 2

    def test_no_previous_message_at_first_message(self) -> None:
        """
        Page with 3 WA messages, 1st message has no previous message
        """
        page = create_content_page(wa_body_count=3)
        assert has_previous_message(0, page, "whatsapp") is None


@pytest.mark.django_db
class TestFormatMessage:
    def test_with_empty_input(self) -> None:
        "Page with no wa messages"
        page = create_content_page(wa_body_count=0)
        assert page.whatsapp_body._raw_data == []
        with pytest.raises(IndexError):
            format_whatsapp_message(0, page, "whatsapp")

    def test_with_null_input(self) -> None:
        """
        Invalid input should raise AttributeError
        """
        with pytest.raises(AttributeError):
            format_whatsapp_message(None, None, None)

    def test_with_invalid_index(self) -> None:
        """
        Page with 1 wa message should throw an error on request for 11th message
        """
        page = create_content_page(wa_body_count=1)
        assert page.whatsapp_body
        assert len(page.whatsapp_body) == 1
        with pytest.raises(IndexError):
            format_whatsapp_message(10, page, "whatsapp")

    def test_happy_case_single_variation_message(self) -> None:
        """
        Check whatsapp message for a page with 1 whatsapp message and 1 variation message
        """
        page = create_content_page(wa_body_count=1, wa_gender_var=["female"])
        result = format_whatsapp_message(0, page, "whatsapp")

        expected_result = {
            "type": "Whatsapp_Message",
            "value": {
                "image": None,
                "document": None,
                "media": None,
                "message": "WhatsApp 1",
                "example_values": [],
                "variation_messages": [
                    {
                        "profile_field": "gender",
                        "value": "female",
                        "message": "WhatsApp Varied 1",
                    }
                ],
                "next_prompt": None,
                "buttons": [],
                "list_items": [],
                "footer": "",
            },
            "id": f'{result["id"]}',
        }

        assert result == expected_result

    def test_happy_case_no_variation_messages(self) -> None:
        """
        Check whatsapp message for a page with 1 whatsapp message and 0 variation message
        """
        page = create_content_page(wa_body_count=1)
        result = format_whatsapp_message(0, page, "whatsapp")
        expected_result = {
            "type": "Whatsapp_Message",
            "value": {
                "image": None,
                "document": None,
                "media": None,
                "message": "WhatsApp 1",
                "example_values": [],
                "variation_messages": [],
                "next_prompt": None,
                "buttons": [],
                "list_items": [],
                "footer": "",
            },
            "id": f'{result["id"]}',
        }
        assert result == expected_result


@pytest.mark.usefixtures("create_form_pages")
@pytest.mark.django_db
class TestAssessmentSerializer:
    def test_form_with_fields(self) -> None:
        """
        Test form with all fields
        """
        page = create_form_with_fields()
        form_page = QuestionField()
        result = form_page.to_representation(page)
        expected_result = [
            {
                "question_type": "categorical_question",
                "question": "test question",
                "explainer": "We need to know this",
                "error": "test error",
                "min": None,
                "max": None,
                "answers": [
                    {"score": 2.0, "answer": "A"},
                    {"score": 1.0, "answer": "B"},
                    {"score": 2.0, "answer": "C"},
                ],
            }
        ]
        result[0].pop("id")
        assert result == expected_result

    def test_form_with_missing_fields(self) -> None:
        """
        Test form with missing fields.
        Ex: explainer field
        """
        page = create_form_with_missing_fields()
        form_page = QuestionField()
        result = form_page.to_representation(page)
        expected_result = [
            {
                "question_type": "categorical_question",
                "question": "test question",
                "explainer": None,
                "error": "test error",
                "min": None,
                "max": None,
                "answers": [
                    {"score": 2.0, "answer": "A"},
                    {"score": 1.0, "answer": "B"},
                    {"score": 2.0, "answer": "C"},
                ],
            }
        ]
        result[0].pop("id")
        assert result == expected_result
