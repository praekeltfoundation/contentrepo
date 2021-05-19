import json
from django.test import TestCase, Client
from home.models import ContentPage
from django.core.management import call_command


class PaginationTestCase(TestCase):
    def test_pagination(self):
        self.client = Client()
        # import content
        args = ["home/tests/content2.csv"]
        opts = {}
        call_command('import_csv_content', *args, **opts)

        # it should only return the whatsapp body if enable_whatsapp=True
        self.content_page1 = ContentPage.objects.first()
        self.content_page1.enable_whatsapp = True
        self.content_page1.save_revision().publish()

        # it should only return the first paragraph if no specific message
        # is requested
        response = self.client.get("/api/v2/pages/4/?whatsapp=True")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 1)
        self.assertEquals(content["body"]["text"], "Whatsapp Body 1")

        # it should only return the second paragraph if 2nd message
        # is requested
        response = self.client.get("/api/v2/pages/4/?whatsapp=True&message=2")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 2)
        self.assertEquals(content["body"]["text"], "whatsapp body2")

        # it should return an appropriate error if requested message index
        # is out of range
        response = self.client.get("/api/v2/pages/4/?whatsapp=True&message=3")
        content = json.loads(response.content)
        self.assertEquals(
            content, {'detail': 'The requested message does not exist'})

        # it should return an appropriate error if requested message is not
        # a positive integer value
        response = self.client.get(
            "/api/v2/pages/4/?whatsapp=True&message=notint")
        content = json.loads(response.content)
        self.assertEquals(
            content,
            {'detail':
             'Please insert a positive integer '
             'for message in the query string'})