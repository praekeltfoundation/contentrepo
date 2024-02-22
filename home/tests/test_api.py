import json
import queue
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from pytest_django.asserts import assertTemplateUsed
from wagtail import blocks

from home.content_import_export import import_content
from home.models import (
    ContentPage,
    HomePage,
    OrderedContentSet,
    PageView,
    VariationBlock,
)

from .page_builder import (
    MBlk,
    MBody,
    PageBuilder,
    SBlk,
    SBody,
    UBlk,
    UBody,
    WABlk,
    WABody,
)
from .utils import create_page


# use this to access the admin interface
@pytest.fixture()
def admin_client(client, django_user_model):
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_superuser(**creds)
    client.login(**creds)
    return client


@pytest.fixture()
def uclient(client, django_user_model):
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_user(**creds)
    client.login(**creds)
    return client


@pytest.mark.django_db
class TestContentPageAPI:
    def create_content_page(
        self, parent=None, title="default page", tags=[], wa_body_count=1
    ):
        if not parent:
            home_page = HomePage.objects.first()
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
            parent = main_menu

        bodies = [
            MBody(title, [MBlk("*Default Messenger Content* 🏥")]),
            SBody(title, [SBlk("*Default SMS Content* ")]),
            UBody(title, [UBlk("*Default USSD Content* ")]),
        ]

        for i in range(wa_body_count):
            wa_body = f"*Default WhatsApp Content {i+1}* 🏥"
            bodies.append(WABody(title, [WABlk(wa_body)]))

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=bodies,
            tags=tags,
            quick_replies=[],
            triggers=[],
        )
        return content_page

    def test_import_button_text(self, admin_client):
        """
        Test that the import button on picker button template has the correct text
        """
        page = self.create_content_page()
        url = f"/admin/pages/{page.id}/edit/"
        response = admin_client.get(url)

        assert response.status_code == 200
        content_str = response.content.decode("utf-8")

        # Use BeautifulSoup to parse the HTML content
        soup = BeautifulSoup(content_str, "html.parser")

        # confirm the correct template is rendered
        assertTemplateUsed(response, "wagtail_content_import/picker_buttons_base.html")

        # Find the div with the specified class
        div_element = soup.find(
            "div", class_="content-import button button-longrunning dropdown-toggle"
        )

        # Check if the text is present in the div's contents
        assert div_element and "Import web from doc" in div_element.get_text(
            strip=True
        ), "Text not found on the page."

    def test_login_required(self, client):
        """
        Users that aren't logged in shouldn't be allowed to access the API
        """
        response = client.get("/api/v2/pages/?tag=menu")
        assert response.status_code == 401

    def test_tag_filtering(self, uclient):
        """
        If a tag filter is provided, only pages with matching tags are returned.

        FIXME:
         * We should probably split this one too
        """
        page = self.create_content_page(tags=["menu"])
        self.create_content_page(page, title="Content Page 1")
        self.create_content_page(page, title="Content Page 2")
        unpublished_page = self.create_content_page(
            page, title="Unpublished Page", tags=["Menu"]
        )
        unpublished_page.unpublish()

        # it should return 1 page for correct tag, excluding unpublished pages with the
        # same tag
        response = uclient.get("/api/v2/pages/?tag=menu")
        content = json.loads(response.content)
        assert content["count"] == 1

        # it should return 1 page for Uppercase tag
        response = uclient.get("/api/v2/pages/?tag=Menu")
        content = json.loads(response.content)
        assert content["count"] == 1

        # it should not return any pages for bogus tag
        response = uclient.get("/api/v2/pages/?tag=bogus")
        content = json.loads(response.content)
        assert content["count"] == 0

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v2/pages/")
        content = json.loads(response.content)
        assert content["count"] == 3

        # If QA flag is sent then it should return pages with tags in the draft
        response = uclient.get("/api/v2/pages/?tag=Menu&qa=True")
        content = json.loads(response.content)
        assert content["count"] == 2

    def test_whatsapp_draft(self, uclient):
        """
        Unpublished whatsapp pages are returned if the qa param is set.
        """
        page = self.create_content_page()
        page.unpublish()

        url = f"/api/v2/pages/{page.id}/?whatsapp=True&qa=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but whatsapp content is returned
        assert not page.live
        body = content["body"]["text"]["value"]["message"].replace("\r", "")
        assert body == "*Default WhatsApp Content 1* 🏥"

    def test_messenger_draft(self, uclient):
        """
        Unpublished messenger pages are returned if the qa param is set.
        """
        page = self.create_content_page()
        page.unpublish()

        url = f"/api/v2/pages/{page.id}/?messenger=True&qa=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but messenger content is returned
        assert not page.live
        body = content["body"]["text"]["message"].replace("\r", "")
        assert body == "*Default Messenger Content* 🏥"

    def test_whatsapp_disabled(self, uclient):
        """
        It should not return the web body if enable_whatsapp=false
        """
        page = self.create_content_page()
        page.enable_whatsapp = False
        page.save_revision().publish()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        assert response.content == b""

    def test_message_number_specified(self, uclient):
        """
        It should only return the 11th paragraph if 11th message is requested
        """
        page = self.create_content_page(wa_body_count=15)

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True&message=11")
        content = json.loads(response.content)

        assert content["body"]["message"] == 11
        assert content["body"]["next_message"] == 12
        assert content["body"]["previous_message"] == 10
        body = content["body"]["text"]["value"]["message"]
        assert body == "*Default WhatsApp Content 11* 🏥"

    def test_no_message_number_specified(self, uclient):
        """
        It should only return the first paragraph if no specific message is requested
        """
        page = self.create_content_page()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        content = response.json()

        assert content["body"]["message"] == 1
        assert content["body"]["previous_message"] is None
        assert content["body"]["total_messages"] == 1
        assert content["body"]["revision"] == page.get_latest_revision().id
        body = content["body"]["text"]["value"]["message"]
        assert body == "*Default WhatsApp Content 1* 🏥"

    def test_message_number_requested_out_of_range(self, uclient):
        """
        It should return an appropriate error if requested message index is out of range
        """
        page = self.create_content_page()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True&message=3")

        assert response.status_code == 400
        assert response.json() == ["The requested message does not exist"]

    def test_message_number_requested_invalid(self, uclient):
        """
        It should return an appropriate error if requested message is not a positive
        integer value
        """
        page = self.create_content_page()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True&message=notint")

        assert response.status_code == 400
        assert response.json() == [
            "Please insert a positive integer for message in the query string"
        ]

    def test_number_of_queries(self, uclient, django_assert_num_queries):
        """
        Make sure we aren't making an enormous number of queries.

        FIXME:
         * Should we document what these queries actually are?
        """
        # Run this once without counting, because there are two queries at the
        # end that only happen if this is the first test that runs.
        page = self.create_content_page()
        page = self.create_content_page(page, title="Content Page 1")
        uclient.get("/api/v2/pages/")
        with django_assert_num_queries(8):
            uclient.get("/api/v2/pages/")

    def test_detail_view_content(self, uclient):
        """
        Fetching the detail view of a page returns the page content.
        """
        page = self.create_content_page(tags=["self_help"])
        response = uclient.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"

        assert content == {
            "id": page.id,
            "title": "default page",
            "subtitle": "",
            "body": {"text": []},
            "tags": ["self_help"],
            "triggers": [],
            "quick_replies": [],
            "related_pages": [],
            "has_children": False,
        }

    def test_detail_view_increments_count(self, uclient):
        """
        Fetching the detail view of a page increments the view count.
        """
        page = self.create_content_page()
        assert PageView.objects.count() == 0

        uclient.get(f"/api/v2/pages/{page.id}/")
        assert PageView.objects.count() == 1
        view = PageView.objects.last()
        assert view.message is None

        uclient.get(f"/api/v2/pages/{page.id}/")
        uclient.get(f"/api/v2/pages/{page.id}/")
        assert PageView.objects.count() == 3
        view = PageView.objects.last()
        assert view.message is None

    def test_detail_view_with_children(self, uclient):
        """
        Fetching the detail view of a page with children indicates that the
        page has children.
        """
        page = self.create_content_page()
        self.create_content_page(page, title="Content Page 1")
        self.create_content_page(page, title="Content Page 2")

        response = uclient.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"

        assert content["has_children"] is True

    def test_detail_view_whatsapp_message(self, uclient):
        """
        Fetching a detail page and selecting the WhatsApp content returns the
        first WhatsApp message in the body.
        """
        page = self.create_content_page()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"

        assert content["id"] == page.id
        assert content["title"] == "default page"

        # There's a lot of body, so only check selected fields.
        body = content.pop("body")
        assert body["message"] == 1
        assert body["next_message"] is None
        assert body["previous_message"] is None
        assert body["total_messages"] == 1
        assert body["text"]["type"] == "Whatsapp_Message"
        assert body["text"]["value"]["message"] == "*Default WhatsApp Content 1* 🏥"

    def test_detail_view_no_content_page(self, uclient):
        """
        We get a validation error if we request a page that doesn't exist.

        FIXME:
         * Is 400 (ValidationError) really an appropriate response code for
           this? 404 seems like a better fit for failing to find a page we're
           looking up by id.
        """
        # it should return the validation error for content page that doesn't exist
        response = uclient.get("/api/v2/pages/1/")
        assert response.status_code == 400

        content = response.json()
        assert content == {"page": ["Page matching query does not exist."]}
        assert content.get("page") == ["Page matching query does not exist."]


@pytest.mark.django_db
class TestWhatsAppMessages:
    """
    FIXME:
     * Should some of the WhatsApp tests from TestPagination live here instead?
    """

    def test_whatsapp_detail_view_with_button(self, uclient):
        """
        Next page buttons in WhatsApp messages are present in the message body.
        """
        page = ContentPage(
            title="test",
            slug="text",
            enable_whatsapp=True,
            whatsapp_body=[
                {
                    "type": "Whatsapp_Message",
                    "value": {
                        "message": "test message",
                        "buttons": [
                            {"type": "next_message", "value": {"title": "Tell me more"}}
                        ],
                    },
                }
            ],
        )
        homepage = HomePage.objects.first()
        homepage.add_child(instance=page)
        page.save_revision().publish()

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()
        [button] = content["body"]["text"]["value"]["buttons"]
        button.pop("id")
        assert button == {"type": "next_message", "value": {"title": "Tell me more"}}

    def test_whatsapp_template(self, uclient):
        """
        FIXME:
         * Is this actually a template message?
        """
        page = ContentPage(
            title="test",
            slug="text",
            enable_whatsapp=True,
            whatsapp_body=[
                {
                    "type": "Whatsapp_Message",
                    "value": {
                        "message": "test message",
                        "buttons": [
                            {"type": "next_message", "value": {"title": "Tell me more"}}
                        ],
                    },
                }
            ],
            whatsapp_template_category="MARKETING",
        )
        homepage = HomePage.objects.first()
        homepage.add_child(instance=page)
        page.save_revision().publish()

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()
        body = content["body"]
        assert body["whatsapp_template_category"] == "MARKETING"

    def test_whatsapp_body(self, uclient):
        """
        Should have the WhatsApp specific fields included in the body; if it's a
        template, what's the template name, the text body of the message.
        """
        page = create_page(
            is_whatsapp_template=True, whatsapp_template_name="test_template"
        )

        # it should return the correct details
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp")
        content = response.json()
        assert content["body"]["is_whatsapp_template"]
        assert content["body"]["whatsapp_template_name"] == "test_template"
        assert content["body"]["text"]["value"]["message"] == "Test WhatsApp Message 1"

    def test_whatsapp_detail_view_with_variations(self, uclient):
        """
        Variation blocks in WhatsApp messages are present in the message body.
        """
        # variations should be in the whatsapp content
        page = create_page(tags=["tag1", "tag2"], add_variation=True)

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()

        var_content = content["body"]["text"]["value"]["variation_messages"]
        assert len(var_content) == 1
        assert var_content[0]["profile_field"] == "gender"
        assert var_content[0]["value"] == "female"
        assert var_content[0]["message"] == "Test Title - female variation"

        assert PageView.objects.count() == 1
        view = PageView.objects.last()
        assert view.message == 1


@pytest.mark.django_db
class TestOrderedContentSetAPI:
    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that all the tests in this class will use.
        """
        path = Path("home/tests/content2.csv")
        with path.open(mode="rb") as f:
            import_content(f, "CSV", queue.Queue())
        self.page1 = ContentPage.objects.first()
        self.ordered_content_set = OrderedContentSet(name="Test set")
        self.ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        self.ordered_content_set.profile_fields.append(("gender", "female"))
        self.ordered_content_set.save()

        self.ordered_content_set_timed = OrderedContentSet(name="Test set")
        self.ordered_content_set_timed.pages.append(
            (
                "pages",
                {
                    "contentpage": self.page1,
                    "time": 5,
                    "unit": "Days",
                    "before_or_after": "Before",
                    "contact_field": "EDD",
                },
            )
        )

        self.ordered_content_set_timed.profile_fields.append(("gender", "female"))
        self.ordered_content_set_timed.save()

    def test_orderedcontent_endpoint(self, uclient):
        """
        The orderedcontent endpoint returns a list of ordered sets, including
        name and profile fields.
        """
        # it should return a list of ordered sets and show the profile fields
        response = uclient.get("/api/v2/orderedcontent/")
        content = json.loads(response.content)
        assert content["count"] == 2
        assert content["results"][0]["name"] == self.ordered_content_set.name
        assert content["results"][0]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

    def test_orderedcontent_detail_endpoint(self, uclient):
        """
        The orderedcontent detail page lists the pages that are part of the
        ordered set.
        """
        # it should return the list of pages that are part of the ordered content set
        response = uclient.get(f"/api/v2/orderedcontent/{self.ordered_content_set.id}/")
        content = json.loads(response.content)
        assert content["name"] == self.ordered_content_set.name
        assert content["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["pages"][0] == {
            "id": self.page1.id,
            "title": self.page1.title,
            "time": None,
            "unit": None,
            "before_or_after": None,
            "contact_field": None,
        }

    def test_orderedcontent_detail_endpoint_timed(self, uclient):
        """
        The orderedcontent detail page lists the pages that are part of the
        ordered set, including information about timing.
        """
        # it should return the list of pages that are part of the ordered content set
        response = uclient.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set_timed.id}/"
        )
        content = json.loads(response.content)
        assert content["name"] == self.ordered_content_set_timed.name
        assert content["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["pages"][0] == {
            "id": self.page1.id,
            "title": self.page1.title,
            "time": 5,
            "unit": "Days",
            "before_or_after": "Before",
            "contact_field": "EDD",
        }

    def test_orderedcontent_detail_endpoint_rel_pages_flag(self, uclient):
        """
        The orderedcontent detail page lists the pages that are part of the
        ordered set, including related pages.
        """
        rel_page = create_page("Related Page")
        self.page1.related_pages = [{"type": "related_page", "value": rel_page.id}]
        self.page1.save_revision().publish()

        # it should return the list of pages that are part of the ordered content set
        response = uclient.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_related=true"
        )
        content = json.loads(response.content)
        assert content["name"] == self.ordered_content_set.name
        assert content["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["pages"][0] == {
            "id": self.page1.id,
            "title": self.page1.title,
            "time": None,
            "unit": None,
            "before_or_after": None,
            "contact_field": None,
            "related_pages": [rel_page.id],
        }

    def test_orderedcontent_detail_endpoint_tags_flag(self, uclient):
        """
        The orderedcontent detail page lists the pages that are part of the
        ordered set, including tags.
        """
        # it should return the list of pages that are part of the ordered content set
        response = uclient.get(
            f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?show_tags=true"
        )
        content = json.loads(response.content)
        assert content["name"] == self.ordered_content_set.name
        assert content["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["pages"][0]["tags"] == [t.name for t in self.page1.tags.all()]


@pytest.mark.django_db
class TestContentPageAPI2:
    """
    Tests contentpage API without test data fixtures
    """

    def test_platform_filtering(self, uclient):
        """
        If a platform filter is provided, only pages with content for that
        platform are returned.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="main-menu-first-time-user",
            title="main menu first time user",
            bodies=[],
            web_body=["Colour"],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="health-info",
            title="health info",
            bodies=[
                WABody("health info", [WABlk("*Health information* 🏥")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="self-help",
            title="self-help",
            bodies=[
                MBody("self-help", [MBlk("*Self-help programs* 🌬️")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="self-help-sms",
            title="self-help-sms",
            bodies=[
                SBody("self-help-sms", [SBlk("*Self-help programs*SMS")]),
            ],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="self-help-ussd",
            title="self-help-ussd",
            bodies=[
                UBody("self-help-ussd", [UBlk("*Self-help programs* USSD")]),
            ],
        )

        # it should return only web pages if filtered
        response = uclient.get("/api/v2/pages/?web=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only whatsapp pages if filtered
        response = uclient.get("/api/v2/pages/?whatsapp=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only sms pages if filtered
        response = uclient.get("/api/v2/pages/?sms=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only ussd pages if filtered
        response = uclient.get("/api/v2/pages/?ussd=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only messenger pages if filtered
        response = uclient.get("/api/v2/pages/?messenger=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only viber pages if filtered
        response = uclient.get("/api/v2/pages/?viber=true")
        content = json.loads(response.content)
        assert content["count"] == 0
        # it should return all pages for no filter
        response = uclient.get("/api/v2/pages/")
        content = json.loads(response.content)
        # exclude home pages and index pages
        assert content["count"] == 5

    def test_ussd_content(self, uclient):
        """
        If a ussd query param is provided, only pages with content for that
        platform are returned.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="main-menu-first-time-user",
            title="main menu first time user",
            bodies=[],
            web_body=["Colour"],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="health-info",
            title="health info",
            bodies=[
                UBody("health info", [UBlk("*Health information* U")]),
            ],
        )

        # it should return only USSD pages if filtered
        response = uclient.get("/api/v2/pages/?ussd=true")
        content = json.loads(response.content)
        assert content["count"] == 1

    def test_sms_content(self, uclient):
        """
        If a sms query param is provided, only pages with content for that
        platform are returned.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        PageBuilder.build_cp(
            parent=main_menu,
            slug="main-menu-first-time-user",
            title="main menu first time user",
            bodies=[],
            web_body=["Colour"],
        )
        PageBuilder.build_cp(
            parent=main_menu,
            slug="health-info",
            title="health info",
            bodies=[
                SBody("health info", [SBlk("*Health information* S")]),
            ],
        )

        # it should return only USSD pages if filtered
        response = uclient.get("/api/v2/pages/?sms=true")
        content = json.loads(response.content)
        assert content["count"] == 1
