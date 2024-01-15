from unittest import mock

from django.test import TestCase, override_settings
from wagtail.blocks import StructBlockValidationError
from wagtail.images import get_image_model

from home.models import (
    GoToPageButton,
    HomePage,
    NextMessageButton,
    PageView,
    WhatsappBlock,
)

from .page_builder import PageBuilder, WABlk, WABody
from .utils import create_page, create_page_rating


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
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_on_save(self, mock_create_whatsapp_template):
        page = create_page(is_whatsapp_template=True)
        mock_create_whatsapp_template.assert_called_with(
            f"WA_Title_{page.get_latest_revision().id}",
            "Test WhatsApp Message 1",
            "UTILITY",
            [],
            None,
            [],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_with_buttons_on_save(self, mock_create_whatsapp_template):
        page = create_page(is_whatsapp_template=True, has_quick_replies=True)
        mock_create_whatsapp_template.assert_called_with(
            f"WA_Title_{page.get_latest_revision().id}",
            "Test WhatsApp Message 1",
            "UTILITY",
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
        mock_create_whatsapp_template.assert_called_with(
            f"WA_Title_{page.get_latest_revision().id}",
            "Test WhatsApp Message with two variables, {{1}} and {{2}}",
            "UTILITY",
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
        mock_create_whatsapp_template.assert_called_once_with(
            f"WA_Title_{page.get_latest_revision().pk}",
            "Test WhatsApp Message 1",
            "UTILITY",
            ["button 1", "button 2"],
            None,
            [],
        )

        mock_create_whatsapp_template.reset_mock()
        page.whatsapp_body.raw_data[0]["value"]["message"] = "Test WhatsApp Message 2"
        revision = page.save_revision()
        revision.publish()

        expected_title = f"WA_Title_{page.get_latest_revision().pk}"
        mock_create_whatsapp_template.assert_called_once_with(
            expected_title,
            "Test WhatsApp Message 2",
            "UTILITY",
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
        expected_template_name = f"WA_Title_{page.get_latest_revision().pk}"
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
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
        expected_template_name = f"WA_Title_{page.get_latest_revision().pk}"
        self.assertEqual(page.whatsapp_template_name, expected_template_name)
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
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

        expected_template_name = f"WA_Title_{page.get_latest_revision().pk}"
        mock_create_whatsapp_template.assert_called_once_with(
            expected_template_name,
            "Test WhatsApp Message 1",
            "UTILITY",
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
            bodies=[],
            whatsapp_template_name="WA_Title_1",
        )

        mock_create_whatsapp_template.assert_not_called()


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

    def test_clean_text_valid_variables(self):
        """Text messages should only contain sequential valid variables, eg. {{1}}"""
        WhatsappBlock().clean(self.create_message_value(message="{{1}}", example_values = ["testing"]))


        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(self.create_message_value(message="{{foo}}", example_values = ["testing"]))
        self.assertEqual(list(e.exception.block_errors.keys()), ["message"])

        with self.assertRaises(StructBlockValidationError) as e:
            WhatsappBlock().clean(self.create_message_value(message="{{2}} {{1}}", example_values = ["testing", "tesing2"]))
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
