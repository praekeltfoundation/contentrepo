import json
from pathlib import Path

from django.test import Client, TestCase
from wagtail import blocks

from home.models import ContentPage, PageView
from home.utils import import_content

from .utils import create_page


class PaginationTestCase(TestCase):
    def setUp(self):
        path = Path("home/tests/content2.csv")
        with path.open(mode="rb") as f:
            import_content(f, "CSV")
        self.content_page1 = ContentPage.objects.first()

    def test_tag_filtering(self):
        self.client = Client()
        # it should return 1 page for correct tag
        response = self.client.get("/api/v2/pages/?tag=menu")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 1)
        # it should return 1 page for Uppercase tag
        response = self.client.get("/api/v2/pages/?tag=Menu")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 1)
        # it should not return any pages for bogus tag
        response = self.client.get("/api/v2/pages/?tag=bogus")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 0)
        # it should return all pages for no tag
        response = self.client.get("/api/v2/pages/")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 59)

    def test_pagination(self):
        self.client = Client()
        # it should return the web body if enable_whatsapp=false
        self.content_page1.enable_whatsapp = False
        self.content_page1.save_revision().publish()
        response = self.client.get("/api/v2/pages/5/?whatsapp=True")
        content = json.loads(response.content)
        self.assertNotEquals(content["body"]["text"], "Whatsapp Body 1")
        self.assertEquals(content["body"]["text"], [])

        # it should only return the whatsapp body if enable_whatsapp=True
        self.content_page1.enable_whatsapp = True
        self.content_page1.save_revision().publish()

        # it should only return the first paragraph if no specific message
        # is requested
        response = self.client.get("/api/v2/pages/5/?whatsapp=True")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 1)
        self.assertEquals(content["body"]["previous_message"], None)
        self.assertEquals(content["body"]["total_messages"], 1)
        self.assertEquals(
            content["body"]["revision"], self.content_page1.get_latest_revision().id
        )
        self.assertTrue(
            "*Welcome to HealthAlert*" in content["body"]["text"]["value"]["message"]
        )

        # it should return an appropriate error if requested message index
        # is out of range
        response = self.client.get("/api/v2/pages/5/?whatsapp=True&message=3")
        content = json.loads(response.content)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(content, ["The requested message does not exist"])

        # it should return an appropriate error if requested message is not
        # a positive integer value
        response = self.client.get("/api/v2/pages/5/?whatsapp=True&message=notint")
        content = json.loads(response.content)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            content,
            ["Please insert a positive integer " "for message in the query string"],
        )

        body = []
        for i in range(15):
            block = blocks.StructBlock([("message", blocks.TextBlock())])
            block_value = block.to_python({"message": f"WA Message {i+1}"})
            body.append(("Whatsapp_Message", block_value))

        self.content_page1.whatsapp_body = body
        self.content_page1.save_revision().publish()

        # it should only return the 11th paragraph if 11th message
        # is requested
        response = self.client.get("/api/v2/pages/5/?whatsapp=True&message=11")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 11)
        self.assertEquals(content["body"]["next_message"], 12)
        self.assertEquals(content["body"]["previous_message"], 10)
        self.assertEquals(content["body"]["text"]["value"]["message"], "WA Message 11")

    def test_detail_view(self):
        ContentPage.objects.all().delete()
        self.assertEquals(PageView.objects.count(), 0)

        page = create_page(tags=["tag1", "tag2"])

        # it should return the correct details
        response = self.client.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        self.assertEquals(content["id"], page.id)
        self.assertEquals(content["title"], page.title)
        self.assertEquals(content["tags"], ["tag1", "tag2"])
        self.assertFalse(content["has_children"])

        self.assertEquals(PageView.objects.count(), 1)

        # if there are children pages
        create_page("child page", page.title)

        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        content = response.json()

        self.assertTrue(content["has_children"])

        self.assertEquals(PageView.objects.count(), 2)
        view = PageView.objects.last()
        self.assertEquals(view.message, None)

        # if we select the whatsapp content
        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()

        self.assertEquals(content["title"], page.whatsapp_title)

        self.assertEquals(PageView.objects.count(), 3)
        view = PageView.objects.last()
        self.assertEquals(view.message, 1)
