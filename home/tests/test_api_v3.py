import json
from pathlib import Path
from typing import Any

import pytest
from django.core.files.base import File  # type: ignore
from django.core.files.images import ImageFile  # type: ignore
from wagtail.documents.models import Document  # type: ignore
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale
from wagtailmedia.models import Media  # type: ignore


from home.models import HomePage, WhatsAppTemplate

from .page_builder import (
    MBlk,
    MBody,
    PageBuilder,
    SBlk,
    SBody,
    UBlk,
    UBody,
    VBlk,
    VBody,
    WABlk,
    WABody,
)

TEST_STATIC_PATH = Path("home/tests/test_static")
ALL_CHANNELS_EXCL_WHATSAPP = ["viber", "messenger", "ussd", "sms"]
ALL_CHANNELS = ALL_CHANNELS_EXCL_WHATSAPP + ["whatsapp"]


@pytest.fixture()
def uclient(client, django_user_model):
    """
    Access the user interface
    """
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_user(**creds)
    client.login(**creds)
    return client


def mk_test_img() -> Image:
    img_path = TEST_STATIC_PATH / "test.jpeg"
    img = Image(
        title="default image title",
        file=ImageFile(img_path.open("rb"), name=img_path.name),
    )
    img.save()
    return img


def mk_test_media() -> File:
    media_path = TEST_STATIC_PATH / "test.mp4"
    media = Media(
        title="default media title",
        file=File(media_path.open("rb"), name=media_path.name),
    )
    media.save()
    return media


def mk_test_doc() -> Document:
    doc_path = TEST_STATIC_PATH / "test.txt"
    doc = Document(
        title="default doc title", file=File(doc_path.open("rb"), name=doc_path.name)
    )
    doc.save()
    return doc


@pytest.mark.django_db
class TestWhatsAppTemplateAPIV3:
    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that the tests in this class will use.
        """
        # TODO: Rework all tests to use fixture data as far as possible
        self.locale_pt, _ = Locale.objects.get_or_create(language_code="pt")
        self.locale_en, _ = Locale.objects.get_or_create(language_code="en")

    @classmethod
    def create_whatsapp_template(
        self,
        slug="default-slug",
        message="Default message",
        buttons=None,
        image=None,
        example_values=None,
        category="UTILITY",
        locale=None,
        publish=False,
    ) -> WhatsAppTemplate:
        if locale:
            locale = Locale.objects.get(language_code=locale)

        template = WhatsAppTemplate(
            slug=slug,
            message=message,
            buttons=buttons,
            example_values=example_values,
            image=image,
            category=category,
            locale=locale,
        )
        template.save()

        rev = template.save_revision()
        if publish:
            rev.publish()
        else:
            template.unpublish()
        template.refresh_from_db()
        return template

    def test_login_required(self, client):
        """
        Users that aren't logged in shouldn't be allowed to access the API
        """
        response = client.get("/api/v3/whatsapptemplates/")
        assert response.status_code == 401

    def test_slug_not_found(self, uclient):
        """
        If a slug can't be found, the error is handled gracefully
        """
        self.create_whatsapp_template(
            slug="some-test-template",
            message="*Default unpublished template * 🏥",
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = "/api/v3/whatsapptemplates/a-slug-that-doesnt-exist/?return_drafts=True"
        response = uclient.get(url)
        content = response.json()
        assert content == {"template": ["Template matching query does not exist."]}

    def test_template_list_drafts(self, uclient):
        """
        If we create a draft template we can find it in the listing view with return_drafts=true
        """
        self.create_whatsapp_template(
            slug="test-template-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
        )

        response = uclient.get("/api/v3/whatsapptemplates/?return_drafts=True")
        content = json.loads(response.content)

        assert content["count"] == 1
        assert content["results"][0]["slug"] == "test-template-1"

    def test_template_list_published(self, uclient):
        """
        Only published templates show up in the listing view by default.
        """
        self.create_whatsapp_template(
            slug="test-template-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        self.create_whatsapp_template(
            slug="test-template-2",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=False,
        )

        response = uclient.get("/api/v3/whatsapptemplates/")
        content = json.loads(response.content)

        assert content["count"] == 1
        assert content["results"][0]["slug"] == "test-template-1"

    def test_template_list_filter_locale(self, uclient):
        """
        Can filter template list by locale
        """
        self.create_whatsapp_template(
            slug="test-template-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        self.create_whatsapp_template(
            slug="test-template-2",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        self.create_whatsapp_template(
            slug="test-template-2",
            message="This is a test message",
            category="UTILITY",
            locale="pt",
            publish=True,
        )

        response = uclient.get("/api/v3/whatsapptemplates/?locale=pt")
        content = json.loads(response.content)

        assert content["count"] == 1
        assert content["results"][0]["slug"] == "test-template-2"

    def test_template_list_filter_slug(self, uclient):
        """
        Can filter template list by slug
        """
        self.create_whatsapp_template(
            slug="test-template-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        self.create_whatsapp_template(
            slug="test-template-2",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        self.create_whatsapp_template(
            slug="test-other-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        response = uclient.get("/api/v3/whatsapptemplates/?slug=other")
        content = json.loads(response.content)

        assert content["count"] == 1
        assert content["results"][0]["slug"] == "test-other-1"

    def test_template_list_unpublished_after_published(self, uclient):
        """
        If we have a published template that has had new draft revisions after the published one,
        the unpublished details will be returned if return_drafts is set to true
        """
        template = self.create_whatsapp_template(
            slug="test-template-2",
            message="*Default published template 1* 🏥",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        template.message = "Message changed in unpublished revision"
        template.save_revision()

        url = "/api/v3/whatsapptemplates/?return_drafts=true"
        response = uclient.get(url)
        content = response.json()
        assert (
            content["results"][0]["message"]
            == "Message changed in unpublished revision"
        )

    def test_template_detail_draft(self, uclient):
        """
        Unpublished templates are returned if the return_drafts param is set.
        """
        template = self.create_whatsapp_template(
            slug="test-template-2",
            message="*Default unpublished template 1* 🏥",
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = f"/api/v3/whatsapptemplates/{template.id}/?return_drafts=True"
        response = uclient.get(url)
        content = response.json()

        assert content["message"] == "*Default unpublished template 1* 🏥"

    def test_template_detail_published_only(self, uclient):
        """
        If we have a published page that an unpublished drafts
        only the published template details are returned if the return_drafts
        param is not set to true.
        """
        template = self.create_whatsapp_template(
            slug="test-template-2",
            message="*Default published template 1* 🏥",
            category="UTILITY",
            locale="en",
            publish=True,
        )

        template.message = "Message changed in unpublished revision"
        template.save_revision()

        url = f"/api/v3/whatsapptemplates/{template.id}/"
        response = uclient.get(url)
        content = response.json()
        assert content["message"] == "*Default published template 1* 🏥"

        url = f"/api/v3/whatsapptemplates/{template.id}/?return_drafts=true"
        response = uclient.get(url)
        content = response.json()

        assert content["message"] == "Message changed in unpublished revision"

    def test_template_detail_buttons(self, uclient):
        """
        The buttons are returned correctly in the detail view for unpublished templates.
        """
        template = self.create_whatsapp_template(
            slug="test-template-1",
            message="*Default template 1* 🏥",
            buttons=[
                ("next_message", {"title": "Test Button 2"}),
            ],
            image=None,
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = f"/api/v3/whatsapptemplates/{template.id}/?return_drafts=True"
        response = uclient.get(url)
        content = response.json()

        assert content["buttons"] == [
            {"title": "Test Button 2", "type": "next_message"}
        ]

    def test_template_detail_image(self, uclient):
        """
        The image is returned correctly in the detail view for unpublished templates.
        """
        mk_test_img()
        image_obj = Image.objects.first()

        template = self.create_whatsapp_template(
            slug="test-template-1",
            message="*Default template 1* 🏥",
            image=image_obj,
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = f"/api/v3/whatsapptemplates/{template.id}/?return_drafts=True"
        response = uclient.get(url)
        content = response.json()
        assert content["image"] == image_obj.id

    def test_template_detail_example_values(self, uclient):
        """
        The example values are returned correctly in the detail view for unpublished templates.
        """

        template = self.create_whatsapp_template(
            slug="test-template-1",
            message="*Default template with 2 placeholders {{1}} and {{2}}* 🏥",
            example_values=[
                ("example_values", "Ev1"),
                ("example_values", "Ev2"),
            ],
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = f"/api/v3/whatsapptemplates/{template.id}/?return_drafts=True"
        response = uclient.get(url)
        content = response.json()
        assert content["example_values"] == ["Ev1", "Ev2"]


@pytest.mark.django_db
class TestContentPageAPIV3:
    """
    FIXME
    ----------
    Whatsapp body : Currently tests are split into whatsapp and not-whatsapp.
        This is because the whatsapp body is different from the others such that
        content is extracted by content["body"]["text"]["value"] for whatsapp and
        content["body"]["text"] for other bodies. This should be changed down the line.
    """

    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that the tests in this class will use.
        """
        # TODO: Rework all tests to use fixture data as far as possible
        self.locale_pt, _ = Locale.objects.get_or_create(language_code="pt")
        self.locale_en, _ = Locale.objects.get_or_create(language_code="en")

    def create_content_page(
        self,
        parent=None,
        title="default page",
        slug="default-slug",
        tags=None,
        body_type="whatsapp",
        body_count=1,
        publish=True,
        web_body=None,
    ):
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        parent : ContentPage
            The ContentPage that will be used as the parent of the content page.

            If this is not provided, a ContentPageIndex object is created as a child of
            the default home page and that is used as the parent.
        title : str
            Title of the content page.
        tags : [str]
            List of tags on the content page.
        body_type : str
            Which body type the test messages should be. It can be WhatsApp, Messenger,
            SMS, USSD or Viber. Not case sensitive.

            This can be set to None to have no message bodies. It defaults to WhatsApp
        body_count : int
            How many message bodies to create on the content page.
        publish: bool
            Should the content page be published or not.
        web_body : str
            The web body of the content page.
        """

        if not parent:
            home_page = HomePage.objects.first()
            main_menu = home_page.get_children().filter(slug="main-menu").first()
            if not main_menu:
                main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
            parent = main_menu

        # Normalise body_type to remove case sensitivity
        if body_type:
            body_type = body_type.casefold()

        bodies = []

        for i in range(body_count):
            msg_body = f"*Default {body_type} Content {i+1}* 🏥"
            match body_type:
                case "whatsapp":
                    bodies.append(WABody(f"{title} for {body_type}", [WABlk(msg_body)]))
                case "messenger":
                    bodies.append(MBody(f"{title} for {body_type}", [MBlk(msg_body)]))
                case "sms":
                    bodies.append(SBody(f"{title} for {body_type}", [SBlk(msg_body)]))
                case "ussd":
                    bodies.append(UBody(f"{title} for {body_type}", [UBlk(msg_body)]))
                case "viber":
                    bodies.append(VBody(f"{title} for {body_type}", [VBlk(msg_body)]))
                case None:
                    pass
                case _:
                    raise ValueError(
                        f"{body_type} not a valid channel, valid options include, whatsapp, messenger, sms, ussd, viber or None"
                    )

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-").lower(),
            title=title,
            bodies=bodies,
            tags=tags or [],
            quick_replies=[],
            triggers=[],
            publish=publish,
            web_body=web_body,
        )

        return content_page

    def test_login_required(self, client):
        """
        Users that aren't logged in shouldn't be allowed to access the API
        """
        response = client.get("/api/v3/pages/?tag=menu")
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
        self.create_content_page(
            page, title="Unpublished Page", tags=["Menu"], publish=False
        )

        # it should return 1 page for correct tag, excluding unpublished pages with the
        # same tag
        response = uclient.get("/api/v3/pages/?tag=menu")

        content = json.loads(response.content)
        assert content["count"] == 1

        # it should return 1 page for Uppercase tag
        response = uclient.get("/api/v3/pages/?tag=Menu")
        content = json.loads(response.content)
        assert content["count"] == 1

        # it should not return any pages for bogus tag
        response = uclient.get("/api/v3/pages/?tag=bogus")
        content = json.loads(response.content)
        assert content["count"] == 0

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v3/pages/")
        content = json.loads(response.content)
        assert content["count"] == 3

        # If return_drafts flag is sent then it should return pages with tags in the draft
        response = uclient.get("/api/v3/pages/?tag=Menu&return_drafts=True")
        content = json.loads(response.content)
        assert content["count"] == 2

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v3/pages/?tag=")
        content = json.loads(response.content)
        assert content["count"] == 3

        # If return_drafts flag is sent then it should return pages with tags in the draft
        response = uclient.get("/api/v3/pages/?tag=Menu&return_drafts=True")
        content = json.loads(response.content)
        assert content["count"] == 2

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v3/pages/?tag=")
        content = json.loads(response.content)
        assert content["count"] == 3

    def test_channel_filtering(self, uclient):
        """
        If a channel filter is provided, only pages with content for that
        channel are returned.
        """
        self.create_content_page(web_body=["Colour"], body_type=None)
        self.create_content_page(title="Health Info")
        self.create_content_page(title="Self Help", body_type="messenger")
        self.create_content_page(title="Self Help SMS", body_type="sms")
        self.create_content_page(title="Self Help USSD", body_type="ussd")
        # it should return only web pages if filtered
        response = uclient.get("/api/v3/pages/?channel=web")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only whatsapp pages if filtered
        response = uclient.get("/api/v3/pages/?channel=whatsapp")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only sms pages if filtered
        response = uclient.get("/api/v3/pages/?channel=sms")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only ussd pages if filtered
        response = uclient.get("/api/v3/pages/?channel=ussd")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only messenger pages if filtered
        response = uclient.get("/api/v3/pages/?channel=messenger")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only viber pages if filtered
        response = uclient.get("/api/v3/pages/?channel=viber")
        content = json.loads(response.content)
        assert content["count"] == 0
        # it should return all pages for no filter
        response = uclient.get("/api/v3/pages/")
        content = json.loads(response.content)

        # exclude home pages and index pages
        assert content["count"] == 5

    def test_whatsapp_draft(self, uclient):
        """
        Unpublished whatsapp pages are returned if the return_drafts param is set.
        """
        page = self.create_content_page(publish=False)

        url = f"/api/v3/pages/{page.id}/?channel=whatsapp&return_drafts=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but whatsapp content is returned
        assert not page.live

        body = content["messages"][0]["text"]
        assert body == "*Default whatsapp Content 1* 🏥"

    @pytest.mark.parametrize("channel", ALL_CHANNELS_EXCL_WHATSAPP)
    def test_message_draft(self, uclient, channel):
        """
        Unpublished <channel> pages are returned if the qa param is set.
        """
        page = self.create_content_page(publish=False, body_type=channel)

        url = f"/api/v3/pages/{page.id}/?channel={channel}&return_drafts=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()
        # the page is not live but messenger content is returned
        assert not page.live
        body = content["messages"]["text"]
        assert body == f"*Default {channel} Content 1* 🏥"

    @pytest.mark.parametrize("channel", ALL_CHANNELS)
    def test_channel_disabled(self, uclient, channel):
        """
        It should not return the body if enable_<channel>=false
        """
        page = self.create_content_page(body_type=channel)

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={channel}")
        assert response.content != b""

        setattr(page, f"enable_{channel}", False)
        page.save_revision().publish()

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={channel}")
        content = response.json()

        # The page is return successfully, but the list of messages is empty
        assert response.status_code == 200
        assert content["messages"] == {"text": []}

    def test_detail_view_unknown_channel(self, uclient):
        """
        It should not return the body for a requested channel that does not exist
        """
        # TODO JT:
        channel = "unknown"
        page = self.create_content_page()

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={channel}")

        assert response.status_code == 400
        content = json.loads(response.content)
        assert (
            content["channel"][0] == "Channel matching query 'unknown' does not exist."
        )

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
        uclient.get("/api/v3/pages/")

        with django_assert_num_queries(12):
            uclient.get("/api/v3/pages/")

    @pytest.mark.parametrize("channel", ALL_CHANNELS)
    def test_detail_view_content(self, uclient, channel):
        """
        Fetching the detail view of a page returns the page content.
        """
        page = self.create_content_page(tags=["self_help"], body_type=channel)
        response = uclient.get(f"/api/v3/pages/{page.id}/")
        content = response.json()
        assert content["slug"] == page.slug
        assert content["locale"] == "en"
        assert content["detail_url"] == f"http://localhost/api/v3/pages/{page.slug}/"

        assert content == {
            "title": "default page",
            "slug": "default-page",
            "detail_url": "http://localhost/api/v3/pages/default-page/",
            "subtitle": "",
            "locale": "en",
            "messages": {"text": []},
            "tags": ["self_help"],
            "triggers": [],
            "related_pages": [],
            "has_children": False,
        }

    def test_detail_view_with_children(self, uclient):
        """
        Fetching the detail view of a page with children indicates that the
        page has children.
        """
        page = self.create_content_page()
        self.create_content_page(page, title="Content Page 1")
        self.create_content_page(page, title="Content Page 2")

        response = uclient.get(f"/api/v3/pages/{page.id}/")
        content = response.json()

        assert content["slug"] == page.slug
        assert content["locale"] == "en"
        assert content["detail_url"] == f"http://localhost/api/v3/pages/{page.slug}/"
        assert content["has_children"] is True

    def test_detail_view_no_content_page(self, uclient):
        """
        We get a validation error if we request a page that doesn't exist.
        """
        # it should return the validation error for content page that doesn't exist
        response = uclient.get("/api/v3/pages/some-slug-with-no-page/")
        assert response.status_code == 404

        content = response.json()

        assert content == {"page": ["Page matching query does not exist."]}
        assert content.get("page") == ["Page matching query does not exist."]

    def test_detail_view_by_slug(self, uclient):
        """
        We can use the page slug in detail view URL
        """
        # it should return the validation error for content page that doesn't exist
        page1 = self.create_content_page(title="Content Page 1")

        response = uclient.get(f"/api/v3/pages/{page1.slug}/")
        content = response.json()

        assert response.status_code == 200

        assert content == {
            "slug": "content-page-1",
            "detail_url": "http://localhost/api/v3/pages/content-page-1/",
            "locale": "en",
            "title": "Content Page 1",
            "subtitle": "",
            "messages": {"text": []},
            "tags": [],
            "triggers": [],
            "has_children": False,
            "related_pages": [],
        }

    def test_detail_view_by_slug_not_on_drafts(self, uclient):
        """
        Looking up a page by slug, only works on published slugs. Draft slugs are ignored.
        """
        default_page = self.create_content_page(title="default-page")
        page_1 = self.create_content_page(default_page, title="Content Page 1")
        self.create_content_page(default_page, title="Content Page 2")

        page_1.slug = "unpublished-slug-change"
        page_1.save_revision()

        response = uclient.get(f"/api/v3/pages/{page_1.slug}/")
        content = response.json()

        assert response.status_code == 404

        response = uclient.get("/api/v3/pages/content-page-1/")
        content = response.json()

        assert response.status_code == 200

        assert content == {
            "slug": "content-page-1",
            "detail_url": "http://localhost/api/v3/pages/content-page-1/",
            "locale": "en",
            "title": "Content Page 1",
            "subtitle": "",
            "messages": {"text": []},
            "tags": [],
            "triggers": [],
            "has_children": False,
            "related_pages": [],
        }

    def test_detail_view_only_publish_no_drafts(self, uclient):
        """
        If we lookup a page that has only been published straight at creation time,
        with no further revisions, it still works on the detail page if we
        add 'return_drafts=true'
        """
        default_page = self.create_content_page(title="default-page")
        page_1 = self.create_content_page(default_page, title="Content Page 1")

        response = uclient.get(f"/api/v3/pages/{page_1.slug}/?return_drafts=true")
        content = response.json()

        assert response.status_code == 200

        assert content == {
            "slug": "content-page-1",
            "detail_url": "http://localhost/api/v3/pages/content-page-1/?return_drafts=true",
            "locale": "en",
            "title": "Content Page 1",
            "subtitle": "",
            "messages": {"text": []},
            "tags": [],
            "triggers": [],
            "has_children": False,
            "related_pages": [],
        }

    def test_detail_view_by_draft_slug(self, uclient):
        """
        Looking up a page by slug, with return_drafts=false, only works on published slugs. Draft slugs are ignored.
        """
        original_slug = "content-page-1"
        draft_slug = "content-page-1-with-draft-slug-change"

        root_page = self.create_content_page(title="default-page")
        page_1 = self.create_content_page(root_page, title="Content Page 1")
        # page_2 = self.create_content_page(default_page, title="Content Page 2")

        page_1.slug = draft_slug
        page_1.save_revision()

        # Looking up with the original published slug should work with return_drafts not specified
        response = uclient.get(f"/api/v3/pages/{original_slug}/")
        content = response.json()
        assert response.status_code == 200

        # Looking up with the changed draft slug should work with return_drafts=true
        response = uclient.get(f"/api/v3/pages/{draft_slug}/?return_drafts=true")
        content = response.json()
        assert response.status_code == 200

        # Looking up with the original slug should fail with return_drafts=true,
        # as a newer draft with a different slug exists
        response = uclient.get(f"/api/v3/pages/{original_slug}/?return_drafts=true")
        content = response.json()
        assert response.status_code == 404

    def test_detail_view_by_id(self, uclient):
        """
        We can use the page id in detail view URL
        """
        # it should return the validation error for content page that doesn't exist
        page1 = self.create_content_page(title="Content Page 1")

        response = uclient.get(f"/api/v3/pages/{page1.id}/")
        content = response.json()

        assert response.status_code == 200

        assert content == {
            "slug": "content-page-1",
            "detail_url": "http://localhost/api/v3/pages/content-page-1/",
            "locale": "en",
            "title": "Content Page 1",
            "subtitle": "",
            "messages": {"text": []},
            "tags": [],
            "triggers": [],
            "has_children": False,
            "related_pages": [],
        }

    def test_page_list_unpublished_after_published(self, uclient):
        """
        If we have a published page that has had new draft revisions after the published one,
        the unpublished details will be returned if return_drafts is set to true
        """
        channel = "whatsapp"
        page = self.create_content_page(
            publish=True, title="Content Page 1", body_type=channel
        )

        page.whatsapp_body[0].value[
            "message"
        ] = "Message changed in unpublished revision"
        page.save_revision()

        url = f"/api/v3/pages/?slug=content-page-1&channel={channel}&return_drafts=True"
        # it should return specific page that is in draft
        content = uclient.get(url).json()
        # the page is not live but messenger content is returned
        body = content["results"][0]["messages"][0]["text"]
        assert body == "Message changed in unpublished revision"

    def test_page_list_match_draft_slugs(self, uclient):
        """
        If we have a published page that has had new draft revisions with a change in slug after the published one,
        the page will be found on the new slug if return_drafts is set to true
        """
        channel = "whatsapp"
        draft_slug = "unpublished-slug-change"
        root_page = self.create_content_page(title="default-page")
        page_1 = self.create_content_page(
            root_page, publish=True, title="Content Page 1", body_type=channel
        )

        page_1.slug = draft_slug
        page_1.save_revision()

        url = f"/api/v3/pages/?channel={channel}&slug={draft_slug}&return_drafts=True"
        content = uclient.get(url).json()
        body = content["results"][0]["messages"][0]["text"]
        assert content["count"] == 1

    def test_list_view_slug_search(self, uclient):
        """
        Querying the list view with a slug parameter, returns case insensitive partial matches
        """
        page = self.create_content_page(title="default-page")
        self.create_content_page(page, title="Content Page 1")
        self.create_content_page(page, title="Content Page 2")
        self.create_content_page(page, title="Unrelated Page 2")

        slug_to_search = "content-page-"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 2

        slug_to_search = "content-page-1"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 1

        slug_to_search = "page"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 4

        slug_to_search = "page-"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 3

    def test_list_view_multiple_filters(self, uclient):
        """
        Querying the list view with a multiple filter parameters,
        returns the correct items where all parameters match
        """

        # Add English pages
        root_en_page = self.create_content_page(title="Root English Page")
        root_en_page.locale = Locale.objects.get(language_code="en")
        root_en_page.save_revision().publish()

        content_page_1 = self.create_content_page(
            root_en_page,
            title="English Content Page 1 with tag1 and a longer title than the slug",
            tags=["tag1"],
        )
        content_page_1.slug = "english-content-page-1-with-tag1"
        content_page_1.save_revision().publish()

        content_page_2 = self.create_content_page(
            root_en_page,
            title="English Content Page 2 with tag1",
            tags=["tag1"],
            body_type="whatsapp",
            publish=True,
        )
        content_page_3 = self.create_content_page(
            root_en_page,
            title="English Content Page 3",
            body_type="whatsapp",
            publish=False,
        )
        self.create_content_page(root_en_page, title="English Content Page 4")

        # Add Portuguese pages
        root_pt_page = self.create_content_page(title="Root Portuguese Page")
        root_pt_page.locale = Locale.objects.get(language_code="pt")
        root_pt_page.save_revision().publish()

        self.create_content_page(root_pt_page, title="Portuguese Page 5")
        self.create_content_page(root_pt_page, title="Portuguese Page 6", publish=False)

        # Count ALL English pages
        url = f"/api/v3/pages/?return_drafts=true&locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 5

        # Count LIVE English pages
        url = f"/api/v3/pages/?locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 4

        # Count ALL Portuguese pages
        url = f"/api/v3/pages/?return_drafts=true&locale=pt"
        content = uclient.get(url).json()
        assert content["count"] == 3

        # Count LIVE Portuguese pages
        url = f"/api/v3/pages/?locale=pt"
        content = uclient.get(url).json()
        assert content["count"] == 2

        # Search by slug (partial match) AND locale
        slug_to_search = "content-page-"
        url = f"/api/v3/pages/?slug={slug_to_search}&locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 3

        # Search by title (partial match) AND locale
        title_to_search = "longer"
        url = f"/api/v3/pages/?title={title_to_search}&locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 1

        # Search for Slug AND title AND locale
        slug_to_search = "content-page-"
        title_to_search = "with"

        url = f"/api/v3/pages/?slug={slug_to_search}&title={title_to_search}&locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 2

        # Search for Slug AND title AND Tag AND locale
        slug_to_search = "content-page-"
        title_to_search = "content page"
        tag_to_search = "tag1"

        url = f"/api/v3/pages/?slug={slug_to_search}&tag={tag_to_search}&title={title_to_search}&locale=en"
        content = uclient.get(url).json()
        assert content["count"] == 2

    def test_list_view_slug_search(self, uclient):
        """
        Filtering a list by slug returns the correct results based
        on whether return_drafts is true or not
        """
        root_page = self.create_content_page(title="Default page 5")
        root_page.locale = Locale.objects.get(language_code="en")
        root_page.save_revision().publish()

        page_6 = self.create_content_page(root_page, title="Content Page 6")
        page_6.slug = "unpublished-slug-change-6"
        page_6.save_revision()

        page_7 = self.create_content_page(root_page, title="Content Page 7")
        page_7.title = "Unpublished Title Change 7"
        page_7.save_revision()

        self.create_content_page(root_page, title="Content Page 8")
        self.create_content_page(root_page, title="Content Page 9")

        slug_to_search = "unpublished-slug-change"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 0

        slug_to_search = "unpublished-slug-change"
        url = f"/api/v3/pages/?slug={slug_to_search}&return_drafts=true"
        content = uclient.get(url).json()
        assert content["count"] == 1

        slug_to_search = "content-page"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 4

        slug_to_search = "content-page"
        url = f"/api/v3/pages/?slug={slug_to_search}&return_drafts=true"
        content = uclient.get(url).json()
        assert content["count"] == 3

        slug_to_search = "content-page-6"
        url = f"/api/v3/pages/?slug={slug_to_search}"
        content = uclient.get(url).json()
        assert content["count"] == 1

        slug_to_search = "content-page-6"
        url = f"/api/v3/pages/?slug={slug_to_search}&return_drafts=true"
        content = uclient.get(url).json()
        assert content["count"] == 0

    def test_list_view_title_search(self, uclient):
        """
        Querying the list view with a title parameter, returns case insensitive partial matches
        """
        page = self.create_content_page(title="default-page")
        self.create_content_page(page, title="Content Page 1")
        self.create_content_page(page, title="Content Page 2")
        self.create_content_page(page, title="Unrelated Page 2")

        title_to_search = "Content page"
        url = f"/api/v3/pages/?title={title_to_search}&return_drafts=True"
        content = uclient.get(url).json()
        assert content["count"] == 2

        title_to_search = "unrelated"
        url = f"/api/v3/pages/?title={title_to_search}&return_drafts=True"
        content = uclient.get(url).json()
        assert content["count"] == 1

        title_to_search = "page"
        url = f"/api/v3/pages/?title={title_to_search}&return_drafts=True"
        content = uclient.get(url).json()
        assert content["count"] == 4

        title_to_search = "default"
        url = f"/api/v3/pages/?title={title_to_search}&return_drafts=True"
        content = uclient.get(url).json()
        assert content["count"] == 1

    def test_wa_image(self, uclient):
        """
        Test that API returns image ID for whatsapp
        """

        mk_test_img()
        image_id_expected = Image.objects.first().id
        msg_body = "*Default whatsapp Content* 🏥"
        title = "default page"

        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = [WABody(title, [WABlk(msg_body, image=image_id_expected)])]

        page = PageBuilder.build_cp(
            parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
        )

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel=whatsapp")

        content = response.json()

        image_id = content["messages"][0]["image"]

        assert image_id == image_id_expected

    def test_wa_media(self, uclient: Any) -> None:
        """
        Test that API returns media ID for whatsapp
        """
        mk_test_media()
        media_id_expected = Media.objects.first().id
        msg_body = "*Default whatsapp Content* 🏥"
        title = "default page"
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = [WABody(title, [WABlk(msg_body, media=media_id_expected)])]

        page = PageBuilder.build_cp(
            parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
        )
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        media_id = content["body"]["text"]["value"]["media"]
        assert media_id == page.whatsapp_body._raw_data[0]["value"]["media"]

    def test_format_related_pages(self, uclient):
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            ],
        )
        health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[MBody("health info", [MBlk("*Health information* M")])],
            tags=["tag2", "tag3"],
        )
        self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help-slug",
            title="Self Help Title",
            bodies=[WABody("self help wa title", [WABlk("*Self-help programs* WA")])],
        )

        PageBuilder.link_related(health_info, [self_help])
        PageBuilder.link_related(self_help, [health_info, ha_menu])

        response = uclient.get(f"/api/v3/pages/{health_info.id}/?channel=whatsapp")

        content = response.json()

        assert content["related_pages"] == [
            {"slug": "self-help-slug", "title": "self help wa title"}
        ]

    def test_format_related_page_with_blank_channel_title(self, uclient):
        """
        If a channel is requested, and the related page does not have a channel
        specific title set, return the related page's Page title
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        ha_menu = PageBuilder.build_cp(
            parent=main_menu,
            slug="ha-menu",
            title="HealthAlert menu",
            bodies=[
                WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
                MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            ],
        )
        health_info = PageBuilder.build_cp(
            parent=ha_menu,
            slug="health-info",
            title="health info",
            bodies=[MBody("health info", [MBlk("*Health information* M")])],
            tags=["tag2", "tag3"],
        )
        self_help = PageBuilder.build_cp(
            parent=ha_menu,
            slug="self-help-slug",
            title="Self Help Page Title",
            # No channel specific title provided
            bodies=[WABody("", [WABlk("*Self-help programs* WA")])],
        )

        PageBuilder.link_related(health_info, [self_help])
        PageBuilder.link_related(self_help, [health_info, ha_menu])

        response = uclient.get(f"/api/v3/pages/{health_info.id}/?channel=whatsapp")

        content = response.json()

        assert content["related_pages"] == [
            {"slug": "self-help-slug", "title": "Self Help Page Title"}
        ]

    @pytest.mark.parametrize("channel", ALL_CHANNELS)
    def test_channel_title(self, uclient, channel):
        """
        If a title is supplied for the channel, use that, otherwise fall back to page title
        """
        page = self.create_content_page(tags=["self_help"], body_type=channel)
        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={channel }")
        content = response.json()

        assert content["slug"] == page.slug
        assert content["locale"] == "en"
        assert (
            content["detail_url"]
            == f"http://localhost/api/v3/pages/{page.slug}/?channel={channel }"
        )

        assert content["title"] == f"default page for {channel}"
