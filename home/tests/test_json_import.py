from django.core.management import call_command
from django.test import TestCase

from home.models import ContentPage


class JSONImportTestCase(TestCase):
    def test_json_import(self):
        "Tests importing content via json management command"

        # assert no content pages exist
        self.assertEqual(ContentPage.objects.count(), 0)

        args = ["home/tests/output.json"]
        opts = {}
        call_command("import_json_content", *args, **opts)

        # assert 1 content page were created
        self.assertEqual(ContentPage.objects.count(), 1)

        page_1 = ContentPage.objects.first()

        # assert corect title and subtitle
        self.assertEqual(page_1.title, "article title")
        self.assertEqual(page_1.subtitle, "article subtitle")

        # assert correct rich text blocks
        self.assertEqual(str(page_1.body[0].render()), "<p>this is some plain text</p>")
        self.assertEqual(page_1.body[1].render(), "<p>this is some richtext</p>")

        # assert correct tags
        self.assertEqual(page_1.tags.first().name, "tag1")
        self.assertEqual(page_1.tags.last().name, "tag2")
