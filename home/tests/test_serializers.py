import pytest

from home.models import ContentPage, HomePage
from home.serializers import (format_whatsapp_message, has_next_message,
                              has_previous_message)

from .page_builder import (MBlk, MBody, PageBuilder, SBlk, SBody, UBlk, UBody,
                           VarMsg, VBlk, VBody, WABlk, WABody)


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
