import json
import queue
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from wagtail import blocks

from home.content_import_export import import_content

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
            import_content(f, "CSV", queue.Queue())
        self.content_page1 = ContentPage.objects.first()
        self.user_credentials = {"username": "test", "password": "test"}
        self.user = get_user_model().objects.create_user(**self.user_credentials)
        self.client.login(**self.user_credentials)
        self.content_page2 = ContentPage.objects.last()

    def test_login_required(self):
        """
        Users that aren't logged in shouldn't be allowed to access the API
        """
        client = Client()
        response = client.get("/api/v2/pages/?tag=menu")
        self.assertEqual(response.status_code, 401)

    def test_tag_filtering(self):
        # it should return 1 page for correct tag
        response = self.client.get("/api/v2/pages/?tag=menu")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # it should return 1 page for Uppercase tag
        response = self.client.get("/api/v2/pages/?tag=Menu")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # it should not return any pages for bogus tag
        response = self.client.get("/api/v2/pages/?tag=bogus")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 0)
        # it should return all pages for no tag
        response = self.client.get("/api/v2/pages/")
        content = json.loads(response.content)
        # exclude home pages and index pages
        self.assertEqual(content["count"], 3)
        # it should not return pages with tags in the draft
        create_page(tags=["Menu"]).unpublish()
        response = self.client.get("/api/v2/pages/?tag=Menu")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # If QA flag is sent then it should return pages with tags in the draft
        response = self.client.get("/api/v2/pages/?tag=Menu&qa=True")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 2)

    def test_platform_filtering(self):
        # web page
        self.content_page1.enable_messenger = False
        self.content_page1.enable_whatsapp = False
        self.content_page1.enable_viber = False
        # This page has web_title, but not web_body. It's unclear what the
        # importer should do in that case, to enable web explicitly.
        self.content_page1.enable_web = True
        self.content_page1.save_revision().publish()
        # whatsapp page
        self.content_page2.enable_messenger = False
        self.content_page2.enable_web = False
        self.content_page2.enable_viber = False
        self.content_page2.save_revision().publish()
        # messenger page
        [page3] = ContentPage.objects.exclude(
            pk__in=[self.content_page1, self.content_page2]
        )[:1]
        page3.enable_web = False
        page3.enable_whatsapp = False
        page3.enable_viber = False
        page3.save_revision().publish()

        # it should return only web pages if filtered
        response = self.client.get("/api/v2/pages/?web=true")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # it should return only whatsapp pages if filtered
        response = self.client.get("/api/v2/pages/?whatsapp=true")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # it should return only messenger pages if filtered
        response = self.client.get("/api/v2/pages/?messenger=true")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 1)
        # it should return only viber pages if filtered
        response = self.client.get("/api/v2/pages/?viber=true")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 0)
        # it should return all pages for no filter
        response = self.client.get("/api/v2/pages/")
        content = json.loads(response.content)
        # exclude home pages and index pages
        self.assertEqual(content["count"], 3)

    def test_whatsapp_draft(self):
        self.content_page2.unpublish()
        page_id = self.content_page2.id
        url = f"/api/v2/pages/{page_id}/?whatsapp=True&qa=True"
        # it should return specific page that is in draft
        response = self.client.get(url)
        content = json.loads(response.content)
        message = "\n".join(
            [
                "*Self-help programs* 🌬️",
                "",
                "Reply with a number to take part in a *free* self-help program created by WHO.",
                "",
                "1. Quit tobacco 🚭",
                "_Stop smoking with the help of a guided, 42-day program._",
                "2. Manage your stress 🧘🏽‍♀️",
                "_Learn how to cope with stress and improve your wellbeing._",
            ]
        )
        # the page is not live but whatsapp content is returned
        self.assertEqual(self.content_page2.live, False)
        self.assertEqual(
            content["body"]["text"]["value"]["message"].replace("\r", ""),
            message,
        )

    def test_messenger_draft(self):
        self.content_page2.unpublish()
        page_id = self.content_page2.id
        url = f"/api/v2/pages/{page_id}/?messenger=True&qa=True"
        # it should return specific page that is in draft
        response = self.client.get(url)

        message = "\n".join(
            [
                "*Self-help programs* 🌬️",
                "",
                "Reply with a number to take part in a *free* self-help program created by WHO.",
                "",
                "1. Quit tobacco 🚭",
                "_Stop smoking with the help of a guided, 42-day program._",
                "2. Manage your stress 🧘🏽‍♀️",
                "_Learn how to cope with stress and improve your wellbeing._",
            ]
        )
        content = json.loads(response.content)

        # the page is not live but messenger content is returned
        self.assertEqual(self.content_page2.live, False)
        self.assertEqual(content["body"]["text"]["message"].replace("\r", ""), message)

    def test_pagination(self):
        # it should not return the web body if enable_whatsapp=false
        self.content_page1.enable_whatsapp = False
        self.content_page1.save_revision().publish()
        response = self.client.get(
            f"/api/v2/pages/{self.content_page1.id}/?whatsapp=True"
        )

        content = response.content
        self.assertEqual(content, b"")

        # it should only return the whatsapp body if enable_whatsapp=True
        self.content_page1.enable_whatsapp = True
        self.content_page1.save_revision().publish()

        # it should only return the first paragraph if no specific message
        # is requested
        response = self.client.get(
            f"/api/v2/pages/{self.content_page1.id}/?whatsapp=True"
        )
        content = json.loads(response.content)
        self.assertEqual(content["body"]["message"], 1)
        self.assertEqual(content["body"]["previous_message"], None)
        self.assertEqual(content["body"]["total_messages"], 1)
        self.assertEqual(
            content["body"]["revision"], self.content_page1.get_latest_revision().id
        )
        self.assertTrue(
            "*Welcome to HealthAlert*" in content["body"]["text"]["value"]["message"]
        )

        # it should return an appropriate error if requested message index
        # is out of range
        response = self.client.get(
            f"/api/v2/pages/{self.content_page1.id}/?whatsapp=True&message=3"
        )
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(content, ["The requested message does not exist"])

        # it should return an appropriate error if requested message is not
        # a positive integer value
        response = self.client.get(
            f"/api/v2/pages/{self.content_page1.id}/?whatsapp=True&message=notint"
        )
        content = json.loads(response.content)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
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
        response = self.client.get(
            f"/api/v2/pages/{self.content_page1.id}/?whatsapp=True&message=11"
        )
        content = json.loads(response.content)
        self.assertEqual(content["body"]["message"], 11)
        self.assertEqual(content["body"]["next_message"], 12)
        self.assertEqual(content["body"]["previous_message"], 10)
        self.assertEqual(content["body"]["text"]["value"]["message"], "WA Message 11")

    def test_number_of_queries(self):
        with self.assertNumQueries(14):
            self.client.get("/api/v2/pages/")

    def test_detail_view(self):
        ContentPage.objects.all().delete()
        self.assertEqual(PageView.objects.count(), 0)

        page = create_page(tags=["tag1", "tag2"])

        # it should return the correct details
        response = self.client.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        self.assertEqual(content["id"], page.id)
        self.assertEqual(content["title"], page.title)
        self.assertEqual(content["tags"], ["tag1", "tag2"])
        self.assertFalse(content["has_children"])

        self.assertEqual(PageView.objects.count(), 1)

        # if there are children pages
        create_page("child page", page.title)

        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        content = response.json()

        self.assertTrue(content["has_children"])

        self.assertEqual(PageView.objects.count(), 2)
        view = PageView.objects.last()
        self.assertEqual(view.message, None)

        # if we select the whatsapp content
        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()

        self.assertEqual(content["title"], page.whatsapp_title)

        self.assertEqual(PageView.objects.count(), 3)
        view = PageView.objects.last()
        self.assertEqual(view.message, 1)

    def test_detail_view_with_variations(self):
        ContentPage.objects.all().delete()
        self.assertEqual(PageView.objects.count(), 0)

        # variations should be in the whatsapp content
        page = create_page(tags=["tag1", "tag2"], add_variation=True)

        response = self.client.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()

        var_content = content["body"]["text"]["value"]["variation_messages"]
        self.assertEqual(1, len(var_content))
        self.assertEqual(var_content[0]["profile_field"], "gender")
        self.assertEqual(var_content[0]["value"], "female")
        self.assertEqual(var_content[0]["message"], "Test Title - female variation")

        self.assertEqual(PageView.objects.count(), 1)
        view = PageView.objects.last()
        self.assertEqual(view.message, 1)

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

    def test_detail_view_no_content_page(self):
        # it should return the validation error for content page that doesn't exist
        response = self.client.get("/api/v2/pages/1/")
        content = response.json()

        self.assertEqual(content, {"page": ["Page matching query does not exist."]})
        self.assertEqual(content.get("page"), ["Page matching query does not exist."])


class OrderedContentSetTestCase(TestCase):
    def setUp(self):
        path = Path("home/tests/content2.csv")
        with path.open(mode="rb") as f:
            import_content(f, "CSV", queue.Queue())
        self.content_page1 = ContentPage.objects.first()
        self.ordered_content_set = OrderedContentSet(name="Test set")
        self.ordered_content_set.pages.append(
            ("pages", {"contentpage": self.content_page1})
        )
        self.ordered_content_set.profile_fields.append(("gender", "female"))
        self.ordered_content_set.save()

        self.ordered_content_set_timed = OrderedContentSet(name="Test set")
        self.ordered_content_set_timed.pages.append(
            (
                "pages",
                {
                    "contentpage": self.content_page1,
                    "time": 5,
                    "unit": "Days",
                    "before_or_after": "Before",
                    "contact_field": "EDD",
                },
            )
        )
        self.user_credentials = {"username": "test", "password": "test"}
        self.user = get_user_model().objects.create_user(**self.user_credentials)
        self.client.login(**self.user_credentials)

        self.ordered_content_set_timed.profile_fields.append(("gender", "female"))
        self.ordered_content_set_timed.save()

    def test_orderedcontent_endpoint(self):
        # it should return a list of ordered sets and show the profile fields
        response = self.client.get("/api/v2/orderedcontent/")
        content = json.loads(response.content)
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["name"], self.ordered_content_set.name)
        self.assertEqual(
            content["results"][0]["profile_fields"][0],
            {"profile_field": "gender", "value": "female"},
        )

    def test_orderedcontent_detail_endpoint(self):
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/"
        )
        content = json.loads(response.content)
        self.assertEqual(content["name"], self.ordered_content_set.name)
        self.assertEqual(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEqual(
            content["pages"][0],
            {
                "id": self.content_page1.id,
                "title": self.content_page1.title,
                "time": None,
                "unit": None,
                "before_or_after": None,
                "contact_field": None,
            },
        )

    def test_orderedcontent_detail_endpoint_timed(self):
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set_timed.id}/"
        )
        content = json.loads(response.content)
        self.assertEqual(content["name"], self.ordered_content_set_timed.name)
        self.assertEqual(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEqual(
            content["pages"][0],
            {
                "id": self.content_page1.id,
                "title": self.content_page1.title,
                "time": 5,
                "unit": "Days",
                "before_or_after": "Before",
                "contact_field": "EDD",
            },
        )

    def test_orderedcontent_detail_endpoint_rel_pages_flag(self):
        rel_page = create_page("Related Page")
        self.content_page1.related_pages = [
            {"type": "related_page", "value": rel_page.id},
        ]
        self.content_page1.save_revision().publish()

        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_related=true"
        )
        content = json.loads(response.content)
        self.assertEqual(content["name"], self.ordered_content_set.name)
        self.assertEqual(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEqual(
            content["pages"][0],
            {
                "id": self.content_page1.id,
                "title": self.content_page1.title,
                "time": None,
                "unit": None,
                "before_or_after": None,
                "contact_field": None,
                "related_pages": [rel_page.id],
            },
        )

    def test_orderedcontent_detail_endpoint_tags_flag(self):
        # it should return the list of pages that are part of the ordered content set
        response = self.client.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_tags=true"
        )
        content = json.loads(response.content)
        self.assertEqual(content["name"], self.ordered_content_set.name)
        self.assertEqual(
            content["profile_fields"][0], {"profile_field": "gender", "value": "female"}
        )
        self.assertEqual(
            content["pages"][0]["tags"], [t.name for t in self.content_page1.tags.all()]
        )
