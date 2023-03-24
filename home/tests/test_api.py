import json
from pathlib import Path

from django.test import Client, TestCase
from wagtail import blocks

from home.utils import import_content

from .utils import create_page

from home.models import (  # isort:skip
    ContentPage,
    OrderedContentSet,
    PageView,
    VariationBlock,
)


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
        self.assertEquals(content["count"], 5)

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
            block = blocks.StructBlock(
                [
                    ("message", blocks.TextBlock()),
                    ("variation_messages", blocks.ListBlock(VariationBlock())),
                ]
            )
            block_value = block.to_python(
                {"message": f"WA Message {i+1}", "variation_messages": []}
            )
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

    def test_detail_view_with_variations(self):
        ContentPage.objects.all().delete()
        self.assertEquals(PageView.objects.count(), 0)

        # variations should be in the whatsapp content
        page = create_page(tags=["tag1", "tag2"], add_variation=True)

        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()

        var_content = content["body"]["text"]["value"]["variation_messages"]
        self.assertEquals(1, len(var_content))
        self.assertEquals(var_content[0]["profile_field"], "gender")
        self.assertEquals(var_content[0]["value"], "female")
        self.assertEquals(var_content[0]["message"], "Test Title - female variation")

        self.assertEquals(PageView.objects.count(), 1)
        view = PageView.objects.last()
        self.assertEquals(view.message, 1)

    def test_whatsapp_body(self):
        """
        Should have the WhatsApp specific fields included in the body; if it's a
        template, what's the template name, the text body of the message.
        """
        ContentPage.objects.all().delete()
        page = create_page(
            is_whatsapp_template=True, whatsapp_template_name="test_template"
        )

        # it should return the correct details
        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp")
        content = response.json()
        self.assertTrue(content["body"]["is_whatsapp_template"])
        self.assertEqual(content["body"]["whatsapp_template_name"], "test_template")
        self.assertEqual(
            content["body"]["text"]["value"]["message"], "Test WhatsApp Message 1"
        )


class OrderedContentSetTestCase(TestCase):
    def setUp(self):
        path = Path("home/tests/content2.csv")
        with path.open(mode="rb") as f:
            import_content(f, "CSV")
        self.content_page1 = ContentPage.objects.first()
        self.ordered_content_set = OrderedContentSet.objects.create(
            name="Test set",
            pages=[
                {"type": "pages", "value": self.content_page1.id},
            ],
            profile_fields=[
                {"type": "gender", "value": "female"},
            ],
        )

    def test_orderedcontent_endpoint(self):
        self.client = Client()
        # it should return a list of ordered sets and show the profile fields
        response = self.client.get("/api/v2/orderedcontent/")
        content = json.loads(response.content)
        self.assertEquals(content["count"], 1)
        self.assertEquals(content["results"][0]["name"], self.ordered_content_set.name)
        self.assertEquals(
            content["results"][0]["profile_fields"][0],
            {"profile_field": "gender", "value": "female"},
        )

    def test_orderedcontent_detail_endpoint(self):
        self.client = Client()
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/"
        )
        content = json.loads(response.content)
        self.assertEquals(content["name"], self.ordered_content_set.name)
        self.assertEquals(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEquals(
            content["pages"][0],
            {"id": self.content_page1.id, "title": self.content_page1.title},
        )

    def test_orderedcontent_detail_endpoint_rel_pages_flag(self):
        rel_page = create_page("Related Page")
        self.content_page1.related_pages = [
            {"type": "related_page", "value": rel_page.id},
        ]
        self.content_page1.save_revision().publish()

        self.client = Client()
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_related=true"
        )
        content = json.loads(response.content)
        self.assertEquals(content["name"], self.ordered_content_set.name)
        self.assertEquals(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEquals(
            content["pages"][0],
            {
                "id": self.content_page1.id,
                "title": self.content_page1.title,
                "related_pages": [rel_page.id],
            },
        )

    def test_orderedcontent_detail_endpoint_tags_flag(self):
        self.client = Client()
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_tags=true"
        )
        content = json.loads(response.content)
        self.assertEquals(content["name"], self.ordered_content_set.name)
        self.assertEquals(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEquals(
            content["pages"][0]["tags"], [t.name for t in self.content_page1.tags.all()]
        )
