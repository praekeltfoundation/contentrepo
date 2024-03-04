import pytest

from home.models import ContentPage, HomePage
from home.serializers import (
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
    wa_var: int = 0,
) -> ContentPage:
    """
    Helper function to create pages needed for each test.

    Parameters
    ----------
    wa_body_count : int
        How many WhatsApp message bodies to create on the content page.
    wa_var: int
        How many WhatsApp variation message bodies to create on the content page. All variations will be on gender
    """
    title = "default page"
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    parent = main_menu

    bodies = [
        MBody(
            title,
            [
                MBlk("*Default Messenger Content* 🏥1"),
                MBlk("*Default Messenger Content* 2🏥"),
            ],
        ),
        SBody(
            title, [SBlk("*Default SMS Content* 1"), SBlk("*Default SMS Content*2 ")]
        ),
        UBody(
            title,
            [UBlk("*Default USSD Content* 1"), UBlk("*Default USSD Content* 2")],
        ),
        VBody(
            title,
            [VBlk("*Default Viber Content* 1"), VBlk("*Default Viber Content* 2")],
        ),
    ]
    gender_variations = ["female", "male", "non-binary", "rather not say"]

    for i in range(wa_body_count):
        wa_body = f"*Default WhatsApp Content {i+1}* 🏥"

        variation_messages = [
            VarMsg(
                wa_body.replace("Default", f"Varied {var+1}"),
                gender=gender_variations[var],
            )
            for var in range(wa_var)
        ]

        bodies.append(
            WABody(
                title,
                [
                    WABlk(
                        wa_body,
                        variation_messages=variation_messages,
                    )
                ],
            )
        )

    content_page = PageBuilder.build_cp(
        parent=parent,
        slug=title.replace(" ", "-"),
        title=title,
        bodies=bodies,
        tags=[],
        quick_replies=[],
        triggers=[],
        publish=True,
    )
    return content_page


@pytest.mark.django_db
class TestHasNextMessage:
    # Test has_next_message
    def test_next_message_whatsapp(self) -> None:
        """Checks if the next message matches up.
        Index of first message is 0, next message is then message 2 with index 1"""
        page = create_content_page(wa_body_count=2, wa_var=0)
        assert page.whatsapp_body
        assert has_next_message(0, page, "whatsapp") == 2

    def test_no_next_message_for_viber(self) -> None:
        """On a page with 2 viber messages, the next message is None"""
        page = create_content_page()
        assert page.viber_body
        assert has_next_message(2, page, "viber") is None

    def test_next_message_for_viber(self) -> None:
        """On a page with 2 viber messages, the next message is None"""
        page = create_content_page()
        assert page.viber_body
        assert has_next_message(1, page, "viber") is None

    def test_no_next_message_for_invalid_platform(self) -> None:
        """Returns none on a platform that is unrecognised"""
        page = create_content_page()
        assert has_next_message(0, page, "email") is None

    def test_no_next_message_for_null_content_page(self) -> None:
        """has_next_message cannot be called on None"""
        with pytest.raises(AttributeError):
            has_next_message(0, None, "whatsapp")

    def test_no_next_message_empty_body(self) -> None:
        """No next message on a page with no whatsapp body"""
        page = create_content_page(wa_body_count=0)
        assert has_next_message(0, page, "whatsapp") is None

    def test_no_next_message_on_last_message(self) -> None:
        """last messages' next message is None"""
        page = create_content_page(wa_body_count=1)
        assert has_next_message(1, page, "whatsapp") is None

    def test_next_message_on_first_message_of_many(self) -> None:
        """Page with many whatsapp messages has a next message on the first"""
        page = create_content_page(wa_body_count=5)
        assert has_next_message(0, page, "whatsapp") == 2

    def test_next_message_large_input(self) -> None:
        """Check next message for very long message sets"""
        page = create_content_page(wa_body_count=1000)
        # second to last message has index 998, last message has index 999 but is message 1000
        assert has_next_message(998, page, "whatsapp") == 999 + 1


@pytest.mark.django_db
class TestHasPreviousMessage:
    # Test has_previous_message
    def test_no_previous_message_on_0_whatsapp_messages(self) -> None:
        """First WA message has no previous message"""
        page = create_content_page(wa_body_count=0)
        assert has_previous_message(0, page, "whatsapp") is None

    def test_previous_message_on_whatsapp_message(self) -> None:
        """Second WA message has a previous message"""
        page = create_content_page(wa_body_count=2)
        assert has_previous_message(1, page, "whatsapp") == 1

    def test_previous_message_on_sms_message(self) -> None:
        """Second SMS message has a previous message"""
        page = create_content_page()
        assert has_previous_message(1, page, "sms") == 1

    def test_no_previous_message_on_invalid_platform(self) -> None:
        """An invalid plaform type returns None"""
        page = create_content_page()
        assert has_previous_message(1, page, "email") is None

    def test_previous_message_with_multiple_messages(self) -> None:
        """Page with 3 WA messages, 3rd message has previous message"""
        page = create_content_page(wa_body_count=3)
        assert has_previous_message(2, page, "whatsapp") == 2

    def test_no_previous_message_at_first_message(self) -> None:
        """Page with 3 WA messages, 1st message has no previous message"""
        page = create_content_page(wa_body_count=3)
        assert has_previous_message(0, page, "whatsapp") is None


@pytest.mark.django_db
class TestFormatMessage:
    def test_format_whatsapp_message_with_empty_input(self) -> None:
        "Page with no wa messages"
        page = create_content_page(wa_body_count=0)
        with pytest.raises(IndexError):
            format_whatsapp_message(0, page, "whatsapp")

    def test_format_whatsapp_message_with_null_input(self) -> None:
        """Invalid input should raise AttributeError"""
        with pytest.raises(AttributeError):
            format_whatsapp_message(None, None, None)

    def test_format_whatsapp_message_with_invalid_index(self) -> None:
        """Page with 1 wa message should throw an error on request for 11th message"""
        page = create_content_page(wa_body_count=1)
        with pytest.raises(IndexError):
            format_whatsapp_message(10, page, "whatsapp")

    def test_format_whatsapp_message_happy_case_single_variation_message(self) -> None:
        page = create_content_page(wa_body_count=1, wa_var=1)
        result = format_whatsapp_message(0, page, "whatsapp")

        expected_result = {
            "type": "Whatsapp_Message",
            "value": {
                "image": None,
                "document": None,
                "media": None,
                "message": "*Default WhatsApp Content 1* 🏥",
                "example_values": [],
                "variation_messages": [
                    {
                        "profile_field": "gender",
                        "value": "female",
                        "message": "*Varied 1 WhatsApp Content 1* 🏥",
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

    def test_format_whatsapp_message_happy_case_no_variation_messages(self) -> None:
        page = create_content_page(wa_body_count=1)
        result = format_whatsapp_message(0, page, "whatsapp")
        expected_result = {
            "type": "Whatsapp_Message",
            "value": {
                "image": None,
                "document": None,
                "media": None,
                "message": "*Default WhatsApp Content 1* 🏥",
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
