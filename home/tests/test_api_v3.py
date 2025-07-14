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
ALL_PLATFORMS_EXCL_WHATSAPP = ["viber", "messenger", "ussd", "sms"]
ALL_PLATFORMS = ALL_PLATFORMS_EXCL_WHATSAPP + ["whatsapp"]


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
    @classmethod
    def create_whatsapp_template(
        self,
        slug="default-slug",
        message="Default message",
        category="UTILITY",
        locale="en",
        publish=False,
    ) -> WhatsAppTemplate:
        locale = Locale.objects.get(language_code="en")
        template = WhatsAppTemplate(
            slug=slug, message=message, category=category, locale=locale
        )
        template.save()
        rev = template.save_revision()
        if publish:
            rev.publish()
        template.refresh_from_db()
        return template

    def test_template_list(self, uclient):
        """
        If we create a template we can find it in the listing view
        """
        self.create_whatsapp_template(
            slug="test-template-1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
        )

        # it should return 1 page for correct tag, excluding unpublished pages with the
        # same tag
        response = uclient.get("/api/v3/whatsapptemplates/?return_drafts=True")
        content = json.loads(response.content)
        assert content["count"] == 1

    def test_login_required(self, client):
        """
        Users that aren't logged in shouldn't be allowed to access the API
        """
        response = client.get("/api/v3/whatsapptemplates/")
        assert response.status_code == 401

    def test_whatsapp_draft(self, uclient):
        """
        Unpublished templates are returned if the qa param is set.
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
        # the page is not live but whatsapp content is returned
        content = response.json()
        assert content["message"] == "*Default unpublished template 1* 🏥"


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
                        f"{body_type} not a valid platform, valid options include, whatsapp, messenger, sms, ussd, viber or None"
                    )

        content_page = PageBuilder.build_cp(
            parent=parent,
            slug=title.replace(" ", "-"),
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

        # If QA flag is sent then it should return pages with tags in the draft
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

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    def test_message_draft(self, uclient, platform):
        """
        Unpublished <platform> pages are returned if the qa param is set.
        """
        page = self.create_content_page(publish=False, body_type=platform)

        url = f"/api/v3/pages/{page.id}/?channel={platform}&return_drafts=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()
        # the page is not live but messenger content is returned
        assert not page.live
        body = content["messages"]["text"]
        assert body == f"*Default {platform} Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_platform_disabled(self, uclient, platform):
        """
        It should not return the body if enable_<platform>=false
        """
        page = self.create_content_page(body_type=platform)

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={platform}")
        assert response.content != b""

        setattr(page, f"enable_{platform}", False)
        page.save_revision().publish()

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={platform}")
        content = response.json()

        # The page is return successfully, but the list of messages is empty
        assert response.status_code == 200
        assert content["messages"] == {"text": []}

    def test_detail_view_unknown_platform(self, uclient):
        """
        It should not return the body for a requested channel that does not exist
        """
        # TODO JT:
        platform = "unknown"
        page = self.create_content_page()

        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={platform}")

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
        # TODO: Keep an eye on this change from 16 to 10.
        with django_assert_num_queries(10):
            uclient.get("/api/v3/pages/")

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_detail_view_content(self, uclient, platform):
        """
        Fetching the detail view of a page returns the page content.
        """
        page = self.create_content_page(tags=["self_help"], body_type=platform)
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

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_channel_title(self, uclient, platform):
        """
        If a title is supplied for the channel, use that, otherwise fall back to page title
        """
        page = self.create_content_page(tags=["self_help"], body_type=platform)
        response = uclient.get(f"/api/v3/pages/{page.id}/?channel={platform }")
        content = response.json()

        assert content["slug"] == page.slug
        assert content["locale"] == "en"
        assert (
            content["detail_url"]
            == f"http://localhost/api/v3/pages/{page.slug}/?channel={platform }"
        )

        assert content["title"] == f"default page for {platform}"
