from django.test import TestCase

from home.models import ContentPage
from home.wagtail_hooks import ContentPageAdmin


class ContentPageAdminTests(TestCase):
    def test_body_text_truncation(self):
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
        admin = ContentPageAdmin()

        self.assertEqual(len(admin.web_body(page)), 200)
        self.assertEqual(len(admin.wa_body(page)), 200)
        self.assertEqual(len(admin.mess_body(page)), 200)
        self.assertEqual(len(admin.vib_body(page)), 200)
        # Web body is different to the rest because of the html
        self.assertEqual(admin.web_body(page)[-6:], "test …")
        self.assertEqual(admin.wa_body(page)[-5:], "test…")
        self.assertEqual(admin.mess_body(page)[-5:], "test…")
        self.assertEqual(admin.vib_body(page)[-5:], "test…")
