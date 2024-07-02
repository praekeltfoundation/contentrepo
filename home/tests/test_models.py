import json
from io import StringIO
from unittest import mock

import pytest
import responses
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from requests import HTTPError
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
    TemplateContentQuickReply,
    USSDBlock,
    WhatsappBlock,
    WhatsAppTemplate,
)

from .page_builder import PageBtn, PageBuilder, WABlk, WABody
from .utils import create_page, create_page_rating


def create_user():
    user = User.objects.create(username="testuser", email="testuser@example.com")
    return user


class MyPageTests(WagtailPageTests):
    def test_contentpage_structure(self):
        """
        A ContentPage can only be created under a ContentPageIndex or another ContentPage.
        A ContentIndexPage can only be created under the HomePage.
        """
        self.assertCanNotCreateAt(Page, ContentPage)
        self.assertCanNotCreateAt(HomePage, ContentPage)
        self.assertCanNotCreateAt(ContentPage, ContentPageIndex)
        self.assertCanNotCreateAt(Page, ContentPageIndex)


class ContentPageTests(TestCase):
    def test_page_and_revision_rating(self):
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

    def test_save_page_view(self):
        page = create_page()

        self.assertEqual(PageView.objects.count(), 0)

        page.save_page_view({"data__save": "this", "dont_save": "this"})

        self.assertEqual(PageView.objects.count(), 1)

        view = PageView.objects.last()
        self.assertEqual(view.page.id, page.id)
        self.assertEqual(view.revision.id, page.get_latest_revision().id)
        self.assertEqual(view.data, {"save": "this"})

    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_on_save_deactivated(self, mock_create_whatsapp_template):
        create_page(is_whatsapp_template=True)
        mock_create_whatsapp_template.assert_not_called()

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_on_save(self):
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        page = create_page(is_whatsapp_template=True)

        request = responses.calls[0].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [{"text": "Test WhatsApp Message 1", "type": "BODY"}],
            "language": "en_US",
            "name": f"wa_title_{page.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_with_buttons_on_save(self, mock_create_whatsapp_template):
        page = create_page(is_whatsapp_template=True, has_quick_replies=True)
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_with(
            f"wa_title_{page.get_latest_revision().id}",
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            ["button 1", "button 2"],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_with_example_values_on_save(
        self, mock_create_whatsapp_template
    ):
        page = create_page(is_whatsapp_template=True, add_example_values=True)
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_with(
            f"wa_title_{page.get_latest_revision().id}",
            "Test WhatsApp Message with two variables, {{1}} and {{2}}",
            "UTILITY",
            en,
            [],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_updated_on_change(self, mock_create_whatsapp_template):
        """
        If the content is changed, the template should be resubmitted with an updated
        template name
        """
        page = create_page(is_whatsapp_template=True, has_quick_replies=True)
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_once_with(
            f"wa_title_{page.get_latest_revision().pk}",
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            ["button 1", "button 2"],
            None,
            [],
        )

        mock_create_whatsapp_template.reset_mock()
        page.whatsapp_body.raw_data[0]["value"]["message"] = "Test WhatsApp Message 2"
        revision = page.save_revision()
        revision.publish()

        expected_title = f"wa_title_{page.get_latest_revision().pk}"
        mock_create_whatsapp_template.assert_called_once_with(
            expected_title,
            "Test WhatsApp Message 2",
            "UTILITY",
            en,
            ["button 1", "button 2"],
            None,
            [],
        )
        page.refresh_from_db()
        self.assertEqual(page.whatsapp_template_name, expected_title)
        self.assertEqual(revision.as_object().whatsapp_template_name, expected_title)

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_not_submitted_on_no_change(self, mock_create_whatsapp_template):
        """
        If the content is not changed, the template should not be resubmitted
        """
        page = create_page(is_whatsapp_template=True, has_quick_replies=True)
        page.get_latest_revision().publish()
        page.refresh_from_db()
        expected_template_name = f"wa_title_{page.get_latest_revision().pk}"
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            ["button 1", "button 2"],
            None,
            [],
        )

        mock_create_whatsapp_template.reset_mock()
        page.save_revision().publish()
        mock_create_whatsapp_template.assert_not_called()
        page.refresh_from_db()
        self.assertEqual(page.whatsapp_template_name, expected_template_name)

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_submitted_when_is_whatsapp_template_is_set(
        self, mock_create_whatsapp_template
    ):
        """
        If the is_whatsapp_template was not enabled on the content, but is changed,
        then it should submit, even if the content hasn't changed.
        """
        page = create_page(is_whatsapp_template=False, has_quick_replies=True)
        page.get_latest_revision().publish()
        page.refresh_from_db()
        mock_create_whatsapp_template.assert_not_called()

        page.is_whatsapp_template = True
        page.save_revision().publish()

        page.refresh_from_db()
        expected_template_name = f"wa_title_{page.get_latest_revision().pk}"
        self.assertEqual(page.whatsapp_template_name, expected_template_name)
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            ["button 1", "button 2"],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_submitted_with_no_whatsapp_previous_revision(
        self, mock_create_whatsapp_template
    ):
        """
        If the previous revision didn't have any whatsapp messages, it should still
        successfully submit a whatsapp template
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        page = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[],
        )
        wa_block = WABody("WA Title", [WABlk("Test WhatsApp Message 1")])
        wa_block.set_on(page)
        page.is_whatsapp_template = True
        page.save_revision()

        expected_template_name = f"wa_title_{page.get_latest_revision().pk}"
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            [],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_not_submitted_with_no_message(
        self, mock_create_whatsapp_template
    ):
        """
        If the page doesn't have any whatsapp messages, then it shouldn't be submitted
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[WABody("WA Title", [])],
            whatsapp_template_name="WA_Title_1",
        )

        mock_create_whatsapp_template.assert_not_called()

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_submitted_with_no_title(self, mock_create_whatsapp_template):
        """
        If the page is a WA template and how no title, then it shouldn't be submitted
        """

        with self.assertRaises(ValidationError):
            home_page = HomePage.objects.first()
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

            PageBuilder.build_cp(
                parent=main_menu,
                slug="template-no-title",
                title="HealthAlert menu",
                bodies=[WABody("", [])],
                whatsapp_template_name="WA_Title_1",
            )

        mock_create_whatsapp_template.assert_not_called()

    def test_clean_text_valid_variables(self):
        """
        The message should accept variables if and only if they are numeric and ordered
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        with self.assertRaises(ValidationError):
            PageBuilder.build_cp(
                parent=main_menu,
                slug="ha-menu",
                title="HealthAlert menu",
                bodies=[
                    WABody(
                        "WA Title",
                        [
                            WABlk(
                                "{{2}}{{1}} {{foo}} {{mismatch1} {mismatch2}}",
                            )
                        ],
                    )
                ],
                whatsapp_template_name="WA_Title_1",
            )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_create_whatsapp_template_submit_no_error_message(
        self, mock_create_whatsapp_template
    ):
        """
        Should not return an error message if template was submitted successfully
        """
        page = create_page(is_whatsapp_template=True)
        page.get_latest_revision().publish()
        expected_template_name = f"wa_title_{page.get_latest_revision().pk}"
        en = Locale.objects.get(language_code="en")
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
            en,
            [],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_create_whatsapp_template_submit_return_error(
        self, mock_create_whatsapp_template
    ):
        """
        Test the error message on template submission failure
        If template submission fails user should get descriptive error instead of internal server error
        """
        mock_create_whatsapp_template.side_effect = HTTPError("Failed")

        with self.assertRaises(ValidationError) as e:
            create_page(is_whatsapp_template=True)

        self.assertRaises(ValidationError)
        self.assertEqual(e.exception.message, "Failed to submit template")

    def test_for_missing_migrations(self):
        output = StringIO()
        call_command("makemigrations", no_input=True, dry_run=True, stdout=output)
        self.assertEqual(
            output.getvalue().strip(),
            "No changes detected",
            "There are missing migrations:\n %s" % output.getvalue(),
        )

    def test_get_all_links(self):
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

        ocs = OrderedContentSet(name="Test set")
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

    def test_get_all_links_no_links(self):
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
    def test_template_create_with_pt_language(self, mock_create_whatsapp_template):
        page = create_page(is_whatsapp_template=True)
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        mock_create_whatsapp_template.assert_called_with(
            f"wa_title_{page.get_latest_revision().id}",
            "Test WhatsApp Message 1",
            "UTILITY",
            pt,
            [],
            None,
            [],
        )


class OrderedContentSetTests(TestCase):
    def test_get_gender_none(self):
        """
        Ordered Content Sets without a gender selected should return None
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.save()
        self.assertIsNone(ordered_content_set.get_gender())

    def test_get_gender(self):
        """
        Ordered Content Sets with a gender selected should return the appropriate gender
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_gender(), "female")

    def test_status_draft(self):
        """
        Draft Ordered Content Sets should return a draft status
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        ordered_content_set.unpublish()
        self.assertEqual(ordered_content_set.status(), "Draft")

    def test_status_live(self):
        """
        Live Ordered Content Sets should return a live status
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.status(), "Live")

    def test_status_live_plus_draft(self):
        """
        An Ordered Content Sets that is published and being drafted should return a live and draft status
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.save()
        ordered_content_set.profile_fields.append(("gender", "female"))
        ordered_content_set.save_revision()
        self.assertEqual(ordered_content_set.status(), "Live + Draft")

    def test_get_relationship(self):
        """
        Ordered Content Sets with a relationship selected should return the appropriate relationship
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_relationship(), "single")

    def test_get_age(self):
        """
        Ordered Content Sets with an age selected should return the choosen age
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.profile_fields.append(("age", "15-18"))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.get_age(), "15-18")

    def test_get_page(self):
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

        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.pages.append(("pages", {"contentpage": page}))
        ordered_content_set.pages.append(("pages", {"contentpage": page2}))
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.page(), ["ha-menu", "page2-menu"])

    def test_get_none_page(self):
        """
        Ordered Content Sets with no page selected should return the default value -
        """
        ordered_content_set = OrderedContentSet(name="Test Title")
        ordered_content_set.save()
        self.assertEqual(ordered_content_set.page(), ["-"])

    def test_status_live_plus_in_moderation(self):
        requested_by = create_user()
        ordered_content_set = OrderedContentSet(name="Test Title")
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

    def test_status_in_moderation(self):
        requested_by = create_user()
        ordered_content_set = OrderedContentSet(name="Test Title", live=False)
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
        image=None,
        document=None,
        media=None,
        message="",
        variation_messages=None,
        example_values=None,
        next_prompt="",
        buttons=None,
        list_items=None,
        footer="",
    ):
        return {
            "image": image,
            "document": document,
            "media": media,
            "message": message,
            "example_values": example_values,
            "variation_messages": variation_messages,
            "next_prompt": next_prompt,
            "buttons": buttons or [],
            "list_items": list_items or [],
            "footer": footer,
        }

    def create_image(self, width=0, height=0):
        Image = get_image_model()
        return Image.objects.create(width=width, height=height)

    def test_clean_text_char_limit(self):
        """Text messages should be limited to 4096 characters"""
        WhatsappBlock().clean(self.create_message_value(message="a" * 4096))

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(self.create_message_value(message="a" * 4097))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])

    def test_clean_media_char_limit(self):
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

    def test_buttons_limit(self):
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

    def test_buttons_char_limit(self):
        """WhatsApp button labels have a character limit"""
        NextMessageButton().clean({"title": "test"})
        GoToPageButton().clean({"title": "test", "page": 1})

        with self.assertRaises(StructBlockValidationError) as e:
            NextMessageButton().clean({"title": "a" * 21})
        self.assertEqual(list(e.exception.block_errors.keys()), ["title"])

        with self.assertRaises(StructBlockValidationError) as e:
            GoToPageButton().clean({"title": "a" * 21})
        self.assertEqual(list(e.exception.block_errors.keys()), ["title"])

    def test_list_items_limit(self):
        """WhatsApp messages can only have up to 10 list items"""
        list_item = WhatsappBlock().child_blocks["list_items"]
        items = list_item.to_python([f"test {_}" for _ in range(12)])

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(
                self.create_message_value(message="a", list_items=items)
            )
        self.assertEqual(list(e.exception.block_errors.keys()), ["list_items"])

    def test_list_items_character_limit(self):
        """WhatsApp list item title can only have up to 24 char"""
        list_item = WhatsappBlock().child_blocks["list_items"]

        WhatsappBlock().clean(
            self.create_message_value(
                message="a",
                list_items=[
                    "test more that max char",
                ],
            )
        )

        with self.assertRaises(StructBlockValidationError) as e:
            items = list_item.to_python(
                ["test limit", "it should fail as the title is above max"]
            )
            WhatsappBlock().clean(
                self.create_message_value(message="a", list_items=items)
            )

        self.assertEqual(list(e.exception.block_errors.keys()), ["list_items"])


class USSDBlockTests(TestCase):
    def create_message_value(
        self,
        message="",
    ):
        return {
            "message": message,
        }

    def test_clean_text_char_limit(self):
        """Text messages should be limited to 160 characters"""
        USSDBlock().clean(self.create_message_value(message="a" * 160))

        with self.assertRaises(StructBlockValidationError) as e:
            USSDBlock().clean(self.create_message_value(message="a" * 161))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])


class SMSBlockTests(TestCase):
    def create_message_value(
        self,
        message="",
    ):
        return {
            "message": message,
        }

    def test_clean_text_char_limit(self):
        """Text messages should be limited to 160 characters"""
        SMSBlock().clean(self.create_message_value(message="a" * 459))

        with self.assertRaises(StructBlockValidationError) as e:
            SMSBlock().clean(self.create_message_value(message="a" * 460))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])


@pytest.mark.django_db
class TestWhatsAppTemplate:

    def test_variables_are_numeric(self) -> None:
        """
        Template variables are numeric.
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                name="non-numeric-variable",
                message="{{foo}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": ["Please provide numeric variables only. You provided ['foo']."],
        }

    def test_variables_are_ordered(self) -> None:
        """
        Template variables are ordered.
        """
        with pytest.raises(ValidationError) as err_info:
            WhatsAppTemplate(
                name="misordered-variables",
                message="{{2}} {{1}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
            ).full_clean()

        assert err_info.value.message_dict == {
            "message": [
                "Variables must be sequential, starting with \"{1}\". You provided \"['2', '1']\""
            ],
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=False)
    @responses.activate
    def test_template_is_not_submitted_if_template_creation_is_disabled(self) -> None:
        """
        Submitting a template does nothing if WHATSAPP_CREATE_TEMPLATES is set
        to False.

        TODO: Should this be an error when template submission is its own
            separate action?
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        wat = WhatsAppTemplate(
            name="wa_title",
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
            name="wa_title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision()

        request = responses.calls[0].request
        assert json.loads(request.body) == {
            "category": "UTILITY",
            "components": [{"text": "Test WhatsApp Message 1", "type": "BODY"}],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    # TODO: Find a better way to test quick replies
    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_with_buttons(self):
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            name="wa_title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        created_qr, _ = TemplateContentQuickReply.objects.get_or_create(name="Button1")
        wat.quick_replies.add(created_qr)
        created_qr, _ = TemplateContentQuickReply.objects.get_or_create(name="Button2")
        wat.quick_replies.add(created_qr)
        wat.save()
        wat.save_revision().publish()

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
                        {"text": "Button1", "type": "QUICK_REPLY"},
                        {"text": "Button2", "type": "QUICK_REPLY"},
                    ],
                },
            ],
            "language": "en_US",
            "name": f"wa_title_{wat.get_latest_revision().id}",
        }

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @responses.activate
    def test_template_create_with_example_values(self):
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        wat = WhatsAppTemplate(
            name="wa_title",
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
    def test_template_create_failed(self):
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
            name="wa_title",
            message="Test WhatsApp Message 1",
            category="UTILITY",
            locale=Locale.objects.get(language_code="en"),
        )
        wat.save()
        wat.save_revision().publish()

        wat_from_db = WhatsAppTemplate.objects.last()
        assert wat_from_db.submission_status == "FAILED"
        assert "Error" in wat_from_db.submission_result


class IntegerQuestionBlockTests(TestCase):
    def create_min_max_value(
        self,
        min,
        max,
    ):
        return {
            "min": min,
            "max": max,
        }

    def test_clean_identical_min_max(self):
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
