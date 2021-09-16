from django.core.management import call_command
from django.test import TestCase
from home.models import ContentPage


class CSVImportTestCase(TestCase):
    def test_csv_import(self):
        "Tests importing content via csv management command"

        # assert no content pages exist
        self.assertEquals(ContentPage.objects.count(), 0)

        args = ["--path", "home/tests/content2.csv"]
        opts = {}
        call_command("import_csv_content", *args, **opts)

        # assert 3 content pages were created
        self.assertEquals(ContentPage.objects.count(), 3)

        page_1 = ContentPage.objects.first()
        page_3 = ContentPage.objects.last()

        # assert 3 correct titles
        self.assertEquals(page_1.title, "Web Title 1")
        self.assertEquals(page_3.title, "Web Title 3")

        self.assertTrue(page_1.enable_whatsapp)
        self.assertTrue(page_3.enable_whatsapp)

        # assert parent linked correctly
        self.assertEquals(page_3.get_parent().title, "Web Title 1")

        # assert correct rich text blocks with markdown
        self.assertEquals(str(page_1.body[0].render()), "This is a nice body")
        self.assertEquals(str(page_1.body[1].render()), "<h2>With two paragraphs</h2>")
        self.assertTrue("Whatsapp Body 3" in page_3.whatsapp_body[0].render())

        # assert correct tags
        self.assertEquals(page_1.tags.first().name, "tag1")
        self.assertEquals(page_1.tags.last().name, "tag2")

        # assert handles empty csv field
        self.assertEquals(len(page_3.messenger_body), 0)
