import json
from wagtail.core import blocks
from django.test import TestCase, Client
from home.models import ContentPage, HomePage
from django.core.management import call_command
from taggit.models import Tag


class PaginationTestCase(TestCase):
    def create_page(self, title="Test Title", parent=None, tags=[]):
        block = blocks.StructBlock(
            [
                ("message", blocks.TextBlock()),
            ]
        )
        block_value = block.to_python({"message": "test content WA"})
        contentpage = ContentPage(
            title=title,
            subtitle="Test Subtitle",
            body="The body",
            enable_whatsapp=True,
            whatsapp_title="WA Title",
            whatsapp_body=[
                ("Whatsapp_Message", block_value),
                ("Whatsapp_Message", block_value),
            ],
        )
        for tag in tags:
            created_tag, _ = Tag.objects.get_or_create(name=tag)
            contentpage.tags.add(created_tag)
        if parent:
            parent = ContentPage.objects.filter(title=parent)[0]
            parent.add_child(instance=contentpage)
        else:
            home_page = HomePage.objects.first()
            home_page.add_child(instance=contentpage)
        contentpage.save_revision()
        return contentpage

    def test_tag_filtering(self):
        self.client = Client()
        # import content
        args = ["home/tests/content2.csv"]
        opts = {}
        call_command("import_csv_content", *args, **opts)
        self.content_page1 = ContentPage.objects.first()
        # it should return 1 page for correct tag
        response = self.client.get("/api/v2/pages/?tag=tag1")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 1)
        # it should not return any pages for bogus tag
        response = self.client.get("/api/v2/pages/?tag=bogus")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 0)
        # it should return all pages for no tag
        response = self.client.get("/api/v2/pages/")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 4)

    def test_pagination(self):
        self.client = Client()
        # import content
        args = ["home/tests/content2.csv"]
        opts = {}
        call_command("import_csv_content", *args, **opts)
        self.content_page1 = ContentPage.objects.first()

        # it should return the web body if enable_whatsapp=false
        response = self.client.get("/api/v2/pages/4/?whatsapp=True")
        content = json.loads(response.content)
        self.assertNotEquals(content["body"]["text"], "Whatsapp Body 1")
        self.assertEquals(content["body"]["text"][0]["value"], "This is a nice body")

        # it should only return the whatsapp body if enable_whatsapp=True
        self.content_page1.enable_whatsapp = True
        self.content_page1.save_revision().publish()

        # it should only return the first paragraph if no specific message
        # is requested
        response = self.client.get("/api/v2/pages/4/?whatsapp=True")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 1)
        self.assertEquals(content["body"]["next_message"], 2)
        self.assertEquals(content["body"]["previous_message"], None)
        self.assertEquals(content["body"]["total_messages"], 2)
        self.assertEquals(
            content["body"]["text"]["value"]["message"], "Whatsapp Body 1"
        )

        # it should only return the second paragraph if 2nd message
        # is requested
        response = self.client.get("/api/v2/pages/4/?whatsapp=True&message=2")
        content = json.loads(response.content)
        self.assertEquals(content["body"]["message"], 2)
        self.assertEquals(content["body"]["next_message"], None)
        self.assertEquals(content["body"]["previous_message"], 1)
        self.assertEquals(content["body"]["text"]["value"]["message"], "whatsapp body2")

        # it should return an appropriate error if requested message index
        # is out of range
        response = self.client.get("/api/v2/pages/4/?whatsapp=True&message=3")
        content = json.loads(response.content)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(content, ["The requested message does not exist"])

        # it should return an appropriate error if requested message is not
        # a positive integer value
        response = self.client.get("/api/v2/pages/4/?whatsapp=True&message=notint")
        content = json.loads(response.content)
        self.assertEquals(response.status_code, 400)
        self.assertEquals(
            content,
            ["Please insert a positive integer " "for message in the query string"],
        )

    def test_detail_view(self):
        page = self.create_page(tags=["tag1", "tag2"])

        # it should return the correct details
        response = self.client.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        self.assertEquals(content["id"], page.id)
        self.assertEquals(content["title"], page.title)
        self.assertEquals(content["tags"], ["tag1", "tag2"])
        self.assertFalse(content["has_children"])

        # if there are children pages
        self.create_page("child page", page.title)

        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        content = response.json()

        self.assertTrue(content["has_children"])

        # if we select the whatsapp content
        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        self.assertEquals(content["title"], page.whatsapp_title)
