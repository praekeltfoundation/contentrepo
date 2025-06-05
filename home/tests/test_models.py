import json
from io import StringIO
from typing import Any
from unittest import mock

import pytest
import responses
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from wagtail.blocks import StructBlockValidationError
from wagtail.images import get_image_model
from wagtail.models import (
    Locale,  # type: ignore
    Page,
    Workflow,
    WorkflowState,
)
from wagtail.test.utils import WagtailPageTests

from home.models import (
    ContentPage,
    ContentPageIndex,
    GoToPageButton,
    HomePage,
    IntegerQuestionBlock,
    NextMessageButton,
    OrderedContentSet,
    PageView,
    SMSBlock,
    USSDBlock,
    WhatsappBlock,
    WhatsAppTemplate,
)
from home.whatsapp import submit_to_meta_action

from .page_builder import PageBtn, PageBuilder, WABlk, WABody
from .utils import create_page, create_page_rating


def create_user() -> User:
    user = User.objects.create(username="testuser", email="testuser@example.com")
    return user


class MyPageTests(WagtailPageTests):
    def test_contentpage_structure(self) -> None:
        """
        A ContentPage can only be created under a ContentPageIndex or another ContentPage.
        A ContentIndexPage can only be created under the HomePage.
        """
        self.assertCanNotCreateAt(Page, ContentPage)
        self.assertCanNotCreateAt(HomePage, ContentPage)
        self.assertCanNotCreateAt(ContentPage, ContentPageIndex)
        self.assertCanNotCreateAt(Page, ContentPageIndex)


class ContentPageTests(TestCase):
    def test_page_and_revision_rating(self) -> None:
        page = create_page()

        self.assertEqual(page.page_rating, "(no ratings yet)")
        self.assertEqual(page.latest_revision_rating, "(no ratings yet)")

        create_page_rating(page)
        create_page_rating(page, False)
        create_page_rating(page)

        self.assertEqual(page.page_rating, "2/3 (66%)")
        self.assertEqual(page.latest_revision_rating, "2/3 (66%)")

        page.save_revision()
        create_page_rating(page)
        self.assertEqual(page.latest_revision_rating, "1/1 (100%)")

    def test_save_page_view(self) -> None:
        page = create_page()

        self.assertEqual(PageView.objects.count(), 0)

        page.save_page_view({"data__save": "this", "dont_save": "this"})

        self.assertEqual(PageView.objects.count(), 1)

        view = PageView.objects.last()
        self.assertEqual(view.page.id, page.id)
        self.assertEqual(view.revision.id, page.get_latest_revision().id)
        self.assertEqual(view.data, {"save": "this"})

    def test_for_missing_migrations(self) -> None:
        output = StringIO()
        call_command("makemigrations", no_input=True, dry_run=True, stdout=output)
        self.assertEqual(
            output.getvalue().strip(),
            "No changes detected",
            f"There are missing migrations:\n {output.getvalue()}",
        )

    def test_get_all_links(self) -> None:
        """
        ContentPage.get_all_links() should return two lists with all ContentPage and
        OrderedContentSet links.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        test_page = PageBuilder.build_cp(
            parent=main_menu, slug="page1", title="Page1", bodies=[]
        )
        page_with_links = PageBuilder.build_cp(
            parent=main_menu,
            slug="page2",
            title="Page2",
            bodies=[
                WABody(
                    "Page2",
                    [
                        WABlk(
                            "Page2 WA Body",
                            buttons=[PageBtn("Import Export", page=test_page)],
                        )
                    ],
                )
            ],
        )
        page_with_links = PageBuilder.link_related(page_with_links, [test_page])

        ocs = OrderedContentSet(
            name="Test set", slug="test", locale=Locale.objects.get(language_code="en")
        )
        ocs.pages.append(("pages", {"contentpage": test_page}))
        ocs.save()
        ocs.save_revision().publish()

        page_links, ocs_links, wat_links = test_page.get_all_links()

        self.assertListEqual(
            [
                (
                    f"/admin/pages/{page_with_links.id}/edit/#tab-whatsapp",
                    "Page2 - WhatsApp: Go to button",
                ),
                (
                    f"/admin/pages/{page_with_links.id}/edit/#tab-promotional",
                    "Page2 - Related Page",
                ),
            ],
            page_links,
        )
        self.assertListEqual(
            [(f"/admin/snippets/home/orderedcontentset/edit/{ocs.id}/", "Test set")],
            ocs_links,
        )

    def test_get_all_links_no_links(self) -> None:
        """
        ContentPage.get_all_links() should return two empty lists if there are no links
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        test_page = PageBuilder.build_cp(
            parent=main_menu, slug="page1", title="Page1", bodies=[]
        )

        page_links, ocs_links, wat_links = test_page.get_all_links()

        self.assertListEqual([], page_links)
        self.assertListEqual([], ocs_links)

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    @pytest.mark.xfail(
        reason="This fails because we can't get locale to create the page, "
        "these tests will be changed once whatsapp templates are separated."
    )
    def test_template_create_with_pt_language(
        self, mock_create_whatsapp_template: Any
    ) -> None:
        page = create_page(is_whatsapp_template=True)
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        mock_create_whatsapp_template.assert_called_with(
            f"wa-title_{page.get_latest_revision().id}",
            "Test WhatsApp Message 1",
            "UTILITY",
            pt,
            [],
            None,
            [],
        )

    def test_body_text_truncation(self) -> None:
        """
        Body text for web, whatsapp, messenger, and viber, should be truncated in this
        list view
        """
        page = ContentPage(
            body=[("paragraph", "test " * 100)],
        )

        page.whatsapp_body.append(("Whatsapp_Message", {"message": "test " * 100}))
        page.messenger_body.append(("messenger_block", {"message": "test " * 100}))
        page.viber_body.append(("viber_message", {"message": "test " * 100}))

        self.assertEqual(len(page.web_body()), 200)
        self.assertEqual(len(page.wa_body()), 200)
        self.assertEqual(len(page.mess_body()), 200)
        self.assertEqual(len(page.vib_body()), 200)

        # Web body is different to the rest because of the html
        self.assertEqual(page.web_body()[-6:], "test …")
        self.assertEqual(page.wa_body()[-5:], "test…")
        self.assertEqual(page.mess_body()[-5:], "test…")
        self.assertEqual(page.vib_body()[-5:], "test…")

    def test_new_template_displays_correctly(self) -> None:
        page = create_page(
            is_new_whatsapp_template=True, whatsapp_template_slug="test-template"
        )

        self.assertEqual(
            page.wa_body(), "Test Whatsapp Template message\nTest WhatsApp Message 1"
        )


class OrderedContentSetTests(TestCase):
    def test_get_gender_none(self) -> None:
        """
        Ordered Content Sets without a gender selected should return None
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.save()
        self.assertIsNone(ordered_content_set.get_gender())

    def test_get_gender(self) -> None:
        """
        Ordered Content Sets with a gender selected should return the appropriate gender
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_gender(), "female")

    def test_status_draft(self) -> None:
        """
        Draft Ordered Content Sets should return a draft status
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        ordered_content_set.unpublish()
        self.assertEqual(ordered_content_set.status(), "Draft")

    def test_status_live(self) -> None:
        """
        Live Ordered Content Sets should return a live status
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.status(), "Live")

    def test_status_live_plus_draft(self) -> None:
        """
        An Ordered Content Sets that is published and being drafted should return a live and draft status
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.save()
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save_revision()
        self.assertEqual(ordered_content_set.status(), "Live + Draft")

    def test_get_relationship(self) -> None:
        """
        Ordered Content Sets with a relationship selected should return the appropriate relationship
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_relationship(), "single")

    def test_get_age(self) -> None:
        """
        Ordered Content Sets with an age selected should return the choosen age
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.profile_fields.append(("age", "15-18"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_age(), "15-18")

    def test_get_page(self) -> None:
        """
        Ordered Content Sets with an page selected should return a list of the choosen page. We compare
        the unique slug of a page
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        page = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[],
        )
        page2 = PageBuilder.build_cp(
            parent=main_menu,
            slug="page2-menu",
            title="page2 menu",
            bodies=[],
        )
        page.save_revision()

        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.pages.append(("pages", {"contentpage": page}))
        ordered_content_set.pages.append(("pages", {"contentpage": page2}))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.page(), ["ha-menu", "page2-menu"])

    def test_get_none_page(self) -> None:
        """
        Ordered Content Sets with no page selected should return the default value -
        """
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="ordered-set-2",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.page(), ["-"])

    def test_status_live_plus_in_moderation(self) -> None:
        requested_by = create_user()
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            slug="test",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.save()
        workflow = Workflow.objects.create(name="Test Workflow", active="t")
        content_type = ContentType.objects.get_for_model(ordered_content_set)
        WorkflowState.objects.create(
            content_type=content_type,
            object_id=ordered_content_set.id,
            workflow_id=workflow.id,
            status="in_progress",
            requested_by=requested_by,
            current_task_state=None,
            base_content_type=content_type,
        )

        assert ordered_content_set.status() == "Live + In Moderation"

    def test_status_in_moderation(self) -> None:
        requested_by = create_user()
        ordered_content_set = OrderedContentSet(
            name="Test Title",
            live=False,
            slug="test",
            locale=Locale.objects.get(language_code="en"),
        )
        ordered_content_set.save()
        workflow = Workflow.objects.create(name="Test Workflow", active="t")
        content_type = ContentType.objects.get_for_model(ordered_content_set)
        WorkflowState.objects.create(
            content_type=content_type,
            object_id=ordered_content_set.id,
            workflow_id=workflow.id,
            status="in_progress",
            requested_by=requested_by,
            current_task_state=None,
            base_content_type=content_type,
        )

        assert ordered_content_set.status() == "In Moderation"


class WhatsappBlockTests(TestCase):
    def create_message_value(
        self,
        image: Any = None,
        document: Any = None,
        media: Any = None,
        message: str = "",
        variation_messages: Any = None,
        next_prompt: str = "",
        buttons: Any = None,
        list_items: Any = None,
        footer: str = "",
    ) -> dict[str, Any]:
        return {
            "image": image,
            "document": document,
            "media": media,
            "message": message,
            "variation_messages": variation_messages,
            "next_prompt": next_prompt,
            "buttons": buttons or [],
            "list_items": list_items or [],
            "footer": footer,
        }

    def create_image(self, width: int = 0, height: int = 0) -> Any:
        Image = get_image_model()
        return Image.objects.create(width=width, height=height)

    def test_clean_text_char_limit(self) -> None:
        """Text messages should be limited to 4096 characters"""
        WhatsappBlock().clean(self.create_message_value(message="a" * 4096))

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(self.create_message_value(message="a" * 4097))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])

    def test_clean_media_char_limit(self) -> None:
        """Media messages should be limited to 1024 characters"""
        image = self.create_image()
        WhatsappBlock().clean(
            self.create_message_value(image=image, message="a" * 1024)
        )

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(
                self.create_message_value(message="a" * 1025, image=image)
            )
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])

    def test_buttons_limit(self) -> None:
        """WhatsApp messages can only have up to 3 buttons"""
        buttons_block = WhatsappBlock().child_blocks["buttons"]
        buttons = buttons_block.to_python(
            [{"type": "next_message", "value": {"title": "test"}} for _ in range(3)]
        )
        WhatsappBlock().clean(self.create_message_value(message="a", buttons=buttons))

        with self.assertRaises(StructBlockValidationError) as e:
            buttons = buttons_block.to_python(
                [{"type": "next_message", "value": {"title": "test"}} for _ in range(4)]
            )
            WhatsappBlock().clean(
                self.create_message_value(message="a", buttons=buttons)
            )
        self.assertEqual(list(e.exception.block_errors.keys()), ["buttons"])

    def test_buttons_char_limit(self) -> None:
        """WhatsApp button labels have a character limit"""
        NextMessageButton().clean({"title": "test"})
        GoToPageButton().clean({"title": "test", "page": 1})

        with self.assertRaises(StructBlockValidationError) as e:
            NextMessageButton().clean({"title": "a" * 21})
        self.assertEqual(list(e.exception.block_errors.keys()), ["title"])

        with self.assertRaises(StructBlockValidationError) as e:
            GoToPageButton().clean({"title": "a" * 21})
        self.assertEqual(list(e.exception.block_errors.keys()), ["title"])

    def test_list_items_limit(self) -> None:
        """WhatsApp messages can only have up to 10 list items"""
        list_item = WhatsappBlock().child_blocks["list_items"]
        items = list_item.to_python(
            [
                {"type": "next_message", "value": {"title": f"test {_}"}}
                for _ in range(12)
            ]
        )

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(
                self.create_message_value(message="a", list_items=items)
            )
        self.assertEqual(list(e.exception.block_errors.keys()), ["list_items"])

    def test_list_items_character_limit(self) -> None:
        """WhatsApp list item title can only have up to 24 char"""
        list_item = WhatsappBlock().child_blocks["list_items"]

        items = list_item.to_python(
            [
                {
                    "type": "next_message",
                    "value": {"title": "test more that max char"},
                },
            ]
        )

        WhatsappBlock().clean(self.create_message_value(message="a", list_items=items))

        with self.assertRaises(StructBlockValidationError) as e:
            items = list_item.to_python(
                [
                    {"type": "next_message", "value": {"title": "test limit"}},
                    {
                        "type": "next_message",
                        "value": {"title": "it should fail as the title is above max"},
                    },
                ]
            )
            WhatsappBlock().clean(
                self.create_message_value(message="a", list_items=items)
            )

        self.assertEqual(list(e.exception.block_errors.keys()), ["list_items"])


class USSDBlockTests(TestCase):
    def create_message_value(
        self,
        message: str = "",
    ) -> dict[str, str]:
        return {
            "message": message,
        }

    def test_clean_text_char_limit(self) -> None:
        """Text messages should be limited to 160 characters"""
        USSDBlock().clean(self.create_message_value(message="a" * 160))

        with self.assertRaises(StructBlockValidationError) as e:
            USSDBlock().clean(self.create_message_value(message="a" * 161))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])


class SMSBlockTests(TestCase):
    def create_message_value(
        self,
        message: str = "",
    ) -> dict[str, str]:
        return {
            "message": message,
        }

    def test_clean_text_char_limit(self) -> None:
        """Text messages should be limited to 160 characters"""
        SMSBlock().clean(self.create_message_value(message="a" * 459))

        with self.assertRaises(StructBlockValidationError) as e:
            SMSBlock().clean(self.create_message_value(message="a" * 460))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])


@pytest.mark.django_db
class WhatsAppTemplateTests(TestCase):
    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=False)
    def test_whitespace_in_positional_variables_are_invalid(self) -> None:
        """
        Whitespace in variables are invalid
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="non-numeric-variable",
                message="This is a message with 1 variables, containing whitespace {{ 1 }}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[("example_values", "Ev1")],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": ["Invalid variable name: ' 1 '"],
        }

    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=False)
    def test_non_numeric_positional_variables_are_invalid(self) -> None:
        """
        Non-numeric variables are invalid as positional vars.
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="non-numeric-variable",
                message="This is a message with 2 variables, {{1}} and {{foo}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[("example_values", "Ev1"), ("example_values", "Ev2")],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": [
                "ParseException: Please provide numeric variables only. You provided '['1', 'foo']'"
            ],
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=True)
    @responses.activate
    def test_named_variables_are_valid(self) -> None:
        """
        Named template variables must be alphanumeric or underscore
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            slug="valid-named-variables",
            message="This is a message with 2 valid named vars {{xxx}} and {{yyy}}",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
            example_values=[("example_values", "Ev1"), ("example_values", "Ev2")],
        )
        wat.save()
        wat.save_revision().publish()

        submit_to_meta_action(wat)

        wat_from_db = WhatsAppTemplate.objects.last()

        assert wat_from_db.submission_status == "SUBMITTED"
        assert "Success! Template ID " in wat_from_db.submission_result
        request = responses.calls[0].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [
                {
                    "text": "This is a message with 2 valid named vars {{xxx}} and {{yyy}}",
                    "type": "BODY",
                    "example": {"body_text": [["Ev1", "Ev2"]]},
                },
            ],
            "language": "en_US",
            "name": f"valid_named_variables_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=True)
    def test_named_variables_are_not_valid(self) -> None:
        """
        Named template variables must be alphanumeric or underscore
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="non-valid-named-variable",
                message="This is a message with a non valid named var {{1_ok_not.ok}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[("example_values", "Ev1")],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": ["Invalid variable name: '1_ok_not.ok'"],
        }

    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=True)
    def test_named_variables_dont_include_invalid_chars(self) -> None:
        """
        Named template variables must not contain invalid chars. Only alphanumeric or underscore allowed
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="non-valid-named-variable",
                message="This is a message with a valid positional var here {{1}} and a named var here{{1_ok_not.ok}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[("example_values", "Ev1"), ("example_values", "Ev2")],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": ["Invalid variable name: '1_ok_not.ok'"],
        }

    @override_settings(WHATSAPP_ALLOW_NAMED_VARIABLES=True)
    @responses.activate
    def test_template_with_all_ints_gets_validated_as_positional_variables(
        self,
    ) -> None:
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="all-int-pos-vars",
                message="Test WhatsApp Message all int placeholders {{2}} and {{1}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[
                    ("example_values", "Ev1"),
                    ("example_values", "Ev2"),
                ],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": [
                "Positional variables must increase sequentially, starting at 1. You provided \"['2', '1']\""
            ]
        }

    def test_variables_are_ordered(self) -> None:
        """
        Template variables are ordered.
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="misordered-variables",
                message="These 2 vars are the wrong way around. {{2}} and {{1}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[
                    ("example_values", "Ev1"),
                    ("example_values", "Ev2"),
                ],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": [
                "Positional variables must increase sequentially, starting at 1. You provided \"['2', '1']\""
            ]
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=False)
    @responses.activate
    def test_template_is_not_submitted_if_template_creation_is_disabled(self) -> None:
        """
        Submitting a template does nothing if WHATSAPP_CREATE_TEMPLATES is set
        to False.

        TODO: Should this be an error when template submission is its own
            separate action?
            Fritz -> I would think yes.  So that we can set a site as unable
            to create templates via the env var,
            regardless of which mechamism is used
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        wat = WhatsAppTemplate(
            slug="wa-title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision()

        assert len(responses.calls) == 0

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_simple_template_submission(self) -> None:
        """
        A simple template with no variables, media, etc. is successfully submitted.
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            slug="wa-title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision()

        submit_to_meta_action(wat)

        request = responses.calls[0].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [{"text": "Test WhatsApp Message 1", "type": "BODY"}],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_with_buttons(self) -> None:
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            slug="wa-title",
            buttons=[
                ("next_message", {"title": "Test Button"}),
            ],
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision().publish()

        submit_to_meta_action(wat)

        wat_from_db = WhatsAppTemplate.objects.last()

        assert wat_from_db.submission_status == "SUBMITTED"
        assert "Success! Template ID " in wat_from_db.submission_result
        request = responses.calls[0].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [
                {"text": "Test WhatsApp Message 1", "type": "BODY"},
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {"text": "Test Button", "type": "QUICK_REPLY"},
                    ],
                },
            ],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_resubmits_when_button_labels_change(self) -> None:
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            slug="wa-title",
            buttons=[
                ("next_message", {"title": "Test Button"}),
            ],
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision().publish()

        submit_to_meta_action(wat)

        assert len(responses.calls) == 1

        wat.buttons = [
            ("next_message", {"title": "Test Button 2"}),
        ]
        wat.save_revision().publish()

        submit_to_meta_action(wat)

        wat_from_db = WhatsAppTemplate.objects.last()

        assert wat_from_db.submission_status == "SUBMITTED"
        assert "Success! Template ID " in wat_from_db.submission_result
        assert len(responses.calls) == 2
        request = responses.calls[1].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [
                {"text": "Test WhatsApp Message 1", "type": "BODY"},
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {"text": "Test Button 2", "type": "QUICK_REPLY"},
                    ],
                },
            ],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_with_example_values(self) -> None:
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            slug="wa-title",
            message="Test WhatsApp Message with two placeholders {{1}} and {{2}}",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
            example_values=[
                ("example_values", "Ev1"),
                ("example_values", "Ev2"),
            ],
        )
        wat.save()
        wat.save_revision()

        submit_to_meta_action(wat)

        request = responses.calls[0].request

        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [
                {
                    "text": "Test WhatsApp Message with two placeholders {{1}} and {{2}}",
                    "type": "BODY",
                    "example": {"body_text": [["Ev1", "Ev2"]]},
                },
            ],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_with_more_example_values_than_vars_fails(self) -> None:
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                slug="more-ev-than-variables",
                message="Test WhatsApp Message with less placeholders {{1}} than example values",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[
                    ("example_values", "Ev1"),
                    ("example_values", "Ev2"),
                ],
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": [
                "Mismatch in number of placeholders and example values. Found 1 placeholder(s) and 2 example values."
            ]
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_failed(self) -> None:
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        error_response = {
            "error": {
                "code": 100,
                "message": "Invalid parameter",
                "type": "OAuthException",
                "error_user_msg": "There is already English (US) content for this template. You can create a new template and try again.",
                "error_user_title": "Content in This Language Already Exists",
            }
        }
        responses.add(responses.POST, url, json=error_response, status=400)

        wat = WhatsAppTemplate(
            slug="wa-title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision().publish()

        submit_to_meta_action(wat)

        wat_from_db = WhatsAppTemplate.objects.last()
        assert wat_from_db.submission_status == "FAILED"
        assert "Error" in wat_from_db.submission_result

    def test_status_live_plus_draft(self) -> None:
        """
        A WhatsAppTemplate that is published and being drafted should return a live and draft status
        """
        wat = WhatsAppTemplate(
            slug="wa-title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.name = "wa-title_2"
        wat.save_revision()
        self.assertTrue(wat.has_unpublished_changes)
        self.assertEqual(wat.status(), "Live + Draft")


class IntegerQuestionBlockTests(TestCase):
    def create_min_max_value(
        self,
        min: int,
        max: int,
    ) -> dict[str, int]:
        return {
            "min": min,
            "max": max,
        }

    def test_clean_identical_min_max(self) -> None:
        """Min and Max values must not be the same"""
        IntegerQuestionBlock().clean(self.create_min_max_value(min=40, max=50))

        with self.assertRaises(ValidationError) as e:
            IntegerQuestionBlock().clean(self.create_min_max_value(min=50, max=50))
        self.assertEqual(
            "min and max values need to be different",
            e.exception.message,
        )
        with self.assertRaises(ValidationError) as e:
            IntegerQuestionBlock().clean(self.create_min_max_value(min=50, max=40))
        self.assertEqual(
            "min cannot be greater than max",
            e.exception.message,
        )
        with self.assertRaises(ValidationError) as e:
            IntegerQuestionBlock().clean(self.create_min_max_value(min=-50, max=40))
        self.assertEqual(
            "min and max cannot be less than zero",
            e.exception.message,
        )
        with self.assertRaises(ValidationError) as e:
            IntegerQuestionBlock().clean(self.create_min_max_value(min=50, max=-40))
        self.assertEqual(
            "min and max cannot be less than zero",
            e.exception.message,
        )
        with self.assertRaises(ValidationError) as e:
            IntegerQuestionBlock().clean(self.create_min_max_value(min=-60, max=-50))
        self.assertEqual(
            "min and max cannot be less than zero",
            e.exception.message,
        )
