from unittest import mock

from django.test import TestCase, override_settings

from home.models import PageView

from .utils import create_page, create_page_rating


class ContentPageTests(TestCase):
    def test_page_and_revision_rating(self):
        page = create_page()

        self.assertEquals(page.page_rating, "(no ratings yet)")
        self.assertEquals(page.latest_revision_rating, "(no ratings yet)")

        create_page_rating(page)
        create_page_rating(page, False)
        create_page_rating(page)

        self.assertEquals(page.page_rating, "2/3 (66%)")
        self.assertEquals(page.latest_revision_rating, "2/3 (66%)")

        page.save_revision()
        create_page_rating(page)
        self.assertEquals(page.latest_revision_rating, "1/1 (100%)")

    def test_save_page_view(self):
        page = create_page()

        self.assertEquals(PageView.objects.count(), 0)

        page.save_page_view({"data__save": "this", "dont_save": "this"})

        self.assertEquals(PageView.objects.count(), 1)

        view = PageView.objects.last()
        self.assertEquals(view.page.id, page.id)
        self.assertEquals(view.revision.id, page.get_latest_revision().id)
        self.assertEquals(view.data, {"save": "this"})

    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_on_save_deactivated(self, mock_create_whatsapp_template):
        create_page(is_whatsapp_template=True)
        mock_create_whatsapp_template.assert_not_called()

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_on_save(self, mock_create_whatsapp_template):
        create_page(is_whatsapp_template=True)
        mock_create_whatsapp_template.assert_called_with(
            "WA_Title_1", "Test WhatsApp Message 1", []
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_create_with_buttons_on_save(self, mock_create_whatsapp_template):
        create_page(is_whatsapp_template=True, has_quick_replies=True)
        mock_create_whatsapp_template.assert_called_with(
            "WA_Title_1",
            "Test WhatsApp Message 1",
            ["button 1", "button 2"],
        )

    @override_settings(WHATSAPP_CREATE_TEMPLATES=True)
    @mock.patch("home.models.create_whatsapp_template")
    def test_template_updated_on_change(self, mock_create_whatsapp_template):
        """
        If the content is changed, the template should be resubmitted with an updated
        template name
        """
        page = create_page(is_whatsapp_template=True, has_quick_replies=True)
        mock_create_whatsapp_template.assert_called_with(
            "WA_Title_1",
            "Test WhatsApp Message 1",
            ["button 1", "button 2"],
        )
        page.whatsapp_body.raw_data[0]["value"]["message"] = "Test WhatsApp Message 2"
        page.save_revision().publish()
        mock_create_whatsapp_template.assert_called_with(
            "WA_Title_2",
            "Test WhatsApp Message 2",
            ["button 1", "button 2"],
        )
