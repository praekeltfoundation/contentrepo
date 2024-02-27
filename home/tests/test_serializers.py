from typing import List, Union

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


@pytest.mark.django_db
class TestHasNextMessage:
    def create_content_page(
        self,
        parent: Union[ContentPage, None] = None,
        title: str = "default page",
        tags: Union[List[str], None] = None,
        wa_body_count: int = 1,
        publish: bool = True,
    ) -> ContentPage:
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        parent : ContentPage
            The ContentPage that will be used as the parent of the content page.

            If this is not provided, a ContentPageIndex object is created as a child of
            the default home page and that is used as the parent.
        title : str
            Title of the content page.
        tags : [str]
            List of tags on the content page.
        wa_body_count : int
            How many WhatsApp message bodies to create on the content page.
        publish: bool
            Should the content page be published or not.
        """
        if not parent:
            home_page = HomePage.objects.first()
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
            parent = main_menu

        bodies = [
            MBody(title, [MBlk("*Default Messenger Content* 🏥")]),
            SBody(title, [SBlk("*Default SMS Content* ")]),
            UBody(title, [UBlk("*Default USSD Content* ")]),
            VBody(title, [VBlk("*Default Viber Content* ")]),
        ]

        for i in range(wa_body_count):
            wa_body = f"*Default WhatsApp Content {i+1}* 🏥"
            bodies.append(WABody(title, [WABlk(wa_body)]))

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=bodies,
            tags=tags or [],
            quick_replies=[],
            triggers=[],
            publish=publish,
        )
        return content_page

    # Test has_next_message
    def test_has_next_message_whatsapp(self) -> None:
        """Checks if the next message matches up.
        Index of first message is 0, next message is then message 2 with index 1"""
        page = self.create_content_page(wa_body_count=2)
        assert page.whatsapp_body
        assert has_next_message(0, page, "whatsapp") == 2

    def test_has_next_message_viber_no_next_message(self) -> None:
        """On a page with 2 viber messages, the next message is None"""
        page = self.create_content_page()
        assert page.viber_body
        assert has_next_message(1, page, "viber") is None

    def test_has_next_message_invalid_platform(self) -> None:
        """Returns none on a platform that is unrecognised"""
        page = self.create_content_page()
        assert has_next_message(0, page, "email") is None

    def test_has_next_message_null_content_page(self) -> None:
        """has_next_message cannot be called on None"""
        with pytest.raises(AttributeError):
            has_next_message(0, None, "whatsapp")

    def test_has_next_message_empty_body(self) -> None:
        """No next message on a page with no whatsapp body"""
        page = self.create_content_page(wa_body_count=0)
        assert has_next_message(0, page, "whatsapp") is None

    def test_has_next_message_on_last_message(self) -> None:
        """last messages' next message is None"""
        page = self.create_content_page(wa_body_count=1)
        assert has_next_message(1, page, "whatsapp") is None

    def test_has_next_message_on_first_message_of_many(self) -> None:
        """Page with many whatsapp messages has a next message on the first"""
        page = self.create_content_page(wa_body_count=5)
        assert has_next_message(0, page, "whatsapp") == 2

    def test_has_next_message_large_input(self) -> None:
        """Check next message for very long message sets"""
        page = self.create_content_page(wa_body_count=1000)
        # second to last message has index 998, last message has index 999 but is message 1000
        assert has_next_message(998, page, "whatsapp") == 999 + 1


@pytest.mark.django_db
class TestHasPreviousMessage:
    def create_content_page(
        self,
        parent: Union[ContentPage, None] = None,
        title: str = "default page",
        tags: Union[List[str], None] = None,
        wa_body_count: int = 1,
        publish: bool = True,
    ) -> ContentPage:
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        parent : ContentPage
            The ContentPage that will be used as the parent of the content page.

            If this is not provided, a ContentPageIndex object is created as a child of
            the default home page and that is used as the parent.
        title : str
            Title of the content page.
        tags : [str]
            List of tags on the content page.
        wa_body_count : int
            How many WhatsApp message bodies to create on the content page.
        publish: bool
            Should the content page be published or not.
        """
        if not parent:
            home_page = HomePage.objects.first()
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
            parent = main_menu

        bodies = [
            MBody(
                title,
                [
                    MBlk("*Default Messenger Content* 🏥"),
                    MBlk("*Default Messenger Content* 🏥 2"),
                ],
            ),
            SBody(
                title, [SBlk("*Default SMS Content* "), SBlk("*Default SMS Content* 2")]
            ),
            UBody(
                title,
                [UBlk("*Default USSD Content* "), UBlk("*Default USSD Content* 2")],
            ),
            VBody(
                title,
                [VBlk("*Default Viber Content* "), VBlk("*Default Viber Content* 2")],
            ),
        ]

        for i in range(wa_body_count):
            wa_body = f"*Default WhatsApp Content {i+1}* 🏥"
            bodies.append(WABody(title, [WABlk(wa_body)]))

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=bodies,
            tags=tags or [],
            quick_replies=[],
            triggers=[],
            publish=publish,
        )
        return content_page

    # Test has_previous_message
    def test_has_previous_message_with_no_previous(self) -> None:
        """First WA message has no previous message"""
        page = self.create_content_page(wa_body_count=0)
        assert has_previous_message(0, page, "whatsapp") is None

    def test_has_previous_message_with_previous_whatsapp(self) -> None:
        """Second WA message has a previous message"""
        page = self.create_content_page(wa_body_count=2)
        assert has_previous_message(1, page, "whatsapp") == 1

    def test_has_previous_message_with_previous_sms(self) -> None:
        """Second SMS message has a previous message"""
        page = self.create_content_page()
        assert has_previous_message(1, page, "sms") == 1

    def test_has_previous_message_invalid_platform(self) -> None:
        """An invalid plaform type returns None"""
        page = self.create_content_page()
        assert has_previous_message(1, page, "email") is None

    def test_has_previous_message_with_multiple_messages(self) -> None:
        """Page with 3 WA messages, 3rd message has previous message"""
        page = self.create_content_page(wa_body_count=3)
        assert has_previous_message(2, page, "whatsapp") == 2

    def test_has_previous_message_at_first_message(self) -> None:
        """Page with 3 WA messages, 1st message has no previous message"""
        page = self.create_content_page(wa_body_count=3)
        assert has_previous_message(0, page, "whatsapp") is None


@pytest.mark.django_db
class TestFormatMessage:
    def create_content_page(
        self,
        parent: Union[ContentPage, None] = None,
        title: str = "default page",
        tags: Union[List[str], None] = None,
        wa_body_count: int = 1,
        publish: bool = True,
        wa_var: int = 0,
    ) -> ContentPage:
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        parent : ContentPage
            The ContentPage that will be used as the parent of the content page.

            If this is not provided, a ContentPageIndex object is created as a child of
            the default home page and that is used as the parent.
        title : str
            Title of the content page.
        tags : [str]
            List of tags on the content page.
        wa_body_count : int
            How many WhatsApp message bodies to create on the content page.
        publish: bool
            Should the content page be published or not.
        """
        if not parent:
            home_page = HomePage.objects.first()
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
            parent = main_menu

        bodies = [
            MBody(
                title,
                [
                    MBlk("*Default Messenger Content* 🏥"),
                    MBlk("*Default Messenger Content* 🏥 2"),
                ],
            ),
            SBody(
                title, [SBlk("*Default SMS Content* "), SBlk("*Default SMS Content* 2")]
            ),
            UBody(
                title,
                [UBlk("*Default USSD Content* "), UBlk("*Default USSD Content* 2")],
            ),
            VBody(
                title,
                [VBlk("*Default Viber Content* "), VBlk("*Default Viber Content* 2")],
            ),
        ]
        gender_variations = ["female", "male", "non-binary", "rather not say"]

        for i in range(wa_body_count):
            wa_body = f"*Default WhatsApp Content {i+1}* 🏥"
            bodies.append(
                WABody(
                    title,
                    [
                        WABlk(
                            wa_body,
                            variation_messages=[
                                VarMsg(
                                    wa_body.replace("Default", f"Varied {var+1}"),
                                    gender=gender_variations[var],
                                )
                                for var in range(wa_var)
                            ],
                        )
                    ],
                )
            )

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=bodies,
            tags=tags or [],
            quick_replies=[],
            triggers=[],
            publish=publish,
        )
        return content_page

    def test_format_whatsapp_message_with_empty_input(self) -> None:
        "Page with no wa messages"
        page = self.create_content_page(wa_body_count=0)
        with pytest.raises(IndexError):
            format_whatsapp_message(0, page, "whatsapp")

    def test_format_whatsapp_message_with_null_input(self) -> None:
        """Invalid input should raise AttributeError"""
        with pytest.raises(AttributeError):
            format_whatsapp_message(None, None, None)

    def test_format_whatsapp_message_with_invalid_index(self) -> None:
        """Page with 1 wa message should throw an error on request for 11th message"""
        page = self.create_content_page(wa_body_count=1)
        with pytest.raises(IndexError):
            format_whatsapp_message(10, page, "whatsapp")

    def test_format_whatsapp_message_happy_case_single_variation_message(self) -> None:
        page = self.create_content_page(wa_body_count=1, wa_var=1)
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
        page = self.create_content_page(wa_body_count=1)
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
