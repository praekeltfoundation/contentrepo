import json
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile

import responses
from django.core.management import call_command
from django.test import TestCase
from wagtail.images.models import Image
from wagtail.models import Locale, Page

from home.models import ContentPage, HomePage

IMG_DATA_BASE = Path("home/tests/import-export-data")


class ImportJsonContentTestCase(TestCase):
    def setUp(self):
        english_locale, _ = Locale.objects.get_or_create(language_code="en")

        root_page, _created = Page.objects.get_or_create(title="Root", slug="root")
        if not HomePage.objects.filter(slug="english-home").exists():
            home_page = HomePage(
                title="English Home", slug="english-home", locale=english_locale
            )
            root_page.add_child(instance=home_page)
            home_page.save()
        else:
            home_page = HomePage.objects.get(slug="english-home")

        self.home_page = home_page
        self.sample_json = {
            "data": [
                {
                    "question": "Sample question (en)",
                    "answer": "Sample answer",
                    "attachment_media_type": "image",
                    "attachment_media_object": {"filename": "sample_image.jpg"},
                    "attachment_uri": "http://storage.googleapis.com/turn-media-store/uploads/sample_image.jpg",
                }
            ]
        }

    @responses.activate
    def test_image_handling(self):
        """
        Test case for handling image attachments in imported JSON content.
        Verifies that the image is correctly downloaded and attached to the content page.
        """
        image_path = IMG_DATA_BASE / "sample_image.jpg"
        with image_path.open("rb") as f:
            image_data = f.read()

        responses.add(
            responses.GET,
            "http://storage.googleapis.com/turn-media-store/uploads/sample_image.jpg",
            body=image_data,
            status=200,
        )

        out = StringIO()

        with NamedTemporaryFile() as tempfile:
            tempfile_path = Path(tempfile.name)
            with tempfile_path.open("w") as f:
                json.dump(self.sample_json, f)
            call_command("import_json_content_turn", tempfile.name, stdout=out)

        self.assertIn("Successfully imported Content Pages", out.getvalue())

        content_page = ContentPage.objects.first()
        assert content_page.whatsapp_body, "whatsapp_body is not set correctly"
        image = content_page.whatsapp_body[0].value["image"]
        self.assertEqual(image.title, "sample_image.jpg")

    @responses.activate
    def test_plain_text_handling(self):
        """
        Test case for handling plain text attachments in imported JSON content.
        Verifies that the text content is correctly attached to the content page
        and that no image is present.
        """
        sample_json = {
            "data": [
                {
                    "question": "Sample question (en)",
                    "answer": "Sample text answer",
                    "attachment_media_type": "text",
                    "attachment_media_object": None,
                    "attachment_uri": None,
                }
            ]
        }

        out = StringIO()

        with NamedTemporaryFile() as tempfile:
            tempfile_path = Path(tempfile.name)
            with tempfile_path.open("w") as f:
                json.dump(sample_json, f)
            call_command("import_json_content_turn", tempfile.name, stdout=out)

        self.assertIn("Successfully imported Content Pages", out.getvalue())

        content_page = ContentPage.objects.first()
        self.assertIsNotNone(content_page)
        self.assertEqual(content_page.title, "Sample question (en)")
        self.assertEqual(
            content_page.whatsapp_body[0].value["message"], "Sample text answer"
        )
        self.assertIsNone(content_page.whatsapp_body[0].value.get("image"))

    def tearDown(self):
        Page.objects.all().delete()
        Image.objects.all().delete()
        Locale.objects.all().delete()
