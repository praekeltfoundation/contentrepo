import json
import queue
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError  # type: ignore
from django.core.files.base import File  # type: ignore
from django.core.files.images import ImageFile  # type: ignore
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed
from taggit.models import Tag  # type: ignore
from wagtail import blocks
from wagtail.documents.models import Document  # type: ignore
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale, Workflow, WorkflowContentType
from wagtail.models.sites import Site  # type: ignore
from wagtailmedia.models import Media  # type: ignore

from home.content_import_export import import_content
from home.models import (
    AgeQuestionBlock,
    AnswerBlock,
    Assessment,
    CategoricalQuestionBlock,
    ContentPage,
    FreeTextQuestionBlock,
    HomePage,
    IntegerQuestionBlock,
    MultiselectQuestionBlock,
    OrderedContentSet,
    PageView,
    YearofBirthQuestionBlock,
)

from .page_builder import (
    FormBtn,
    FormListItem,
    MBlk,
    MBody,
    NextBtn,
    NextListItem,
    PageBtn,
    PageBuilder,
    PageListItem,
    SBlk,
    SBody,
    UBlk,
    UBody,
    VarMsg,
    VBlk,
    VBody,
    WABlk,
    WABody,
)
from .utils import create_page

TEST_STATIC_PATH = Path("home/tests/test_static")
ALL_PLATFORMS_EXCL_WHATSAPP = ["viber", "messenger", "ussd", "sms"]
ALL_PLATFORMS = ALL_PLATFORMS_EXCL_WHATSAPP + ["whatsapp"]


@pytest.fixture()
def admin_client(client, django_user_model):
    """
    Access admin interface
    """
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_superuser(**creds)
    client.login(**creds)
    return client


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
class TestContentPageAPI:
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
                    bodies.append(WABody(title, [WABlk(msg_body)]))
                case "messenger":
                    bodies.append(MBody(title, [MBlk(msg_body)]))
                case "sms":
                    bodies.append(SBody(title, [SBlk(msg_body)]))
                case "ussd":
                    bodies.append(UBody(title, [UBlk(msg_body)]))
                case "viber":
                    bodies.append(VBody(title, [VBlk(msg_body)]))
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
        self.create_content_page(
            page, title="Unpublished Page", tags=["Menu"], publish=False
        )

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

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v2/pages/?tag=")
        content = json.loads(response.content)
        assert content["count"] == 3

    def test_platform_filtering(self, uclient):
        """
        If a platform filter is provided, only pages with content for that
        platform are returned.
        """
        self.create_content_page(web_body=["Colour"], body_type=None)
        self.create_content_page(title="Health Info")
        self.create_content_page(title="Self Help", body_type="messenger")
        self.create_content_page(title="Self Help SMS", body_type="sms")
        self.create_content_page(title="Self Help USSD", body_type="ussd")

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

    def test_whatsapp_draft(self, uclient):
        """
        Unpublished whatsapp pages are returned if the qa param is set.
        """
        page = self.create_content_page(publish=False)

        url = f"/api/v2/pages/{page.id}/?whatsapp=True&qa=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but whatsapp content is returned
        assert not page.live
        body = content["body"]["text"]["value"]["message"]
        assert body == "*Default whatsapp Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    def test_message_draft(self, uclient, platform):
        """
        Unpublished <platform> pages are returned if the qa param is set.
        """
        page = self.create_content_page(publish=False, body_type=platform)

        url = f"/api/v2/pages/{page.id}/?{platform}=True&qa=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but messenger content is returned
        assert not page.live
        body = content["body"]["text"]["message"]
        assert body == f"*Default {platform} Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_platform_disabled(self, uclient, platform):
        """
        It should not return the body if enable_<platform>=false
        """
        page = self.create_content_page(body_type=platform)

        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=True")
        assert response.content != b""

        setattr(page, f"enable_{platform}", False)
        page.save_revision().publish()

        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=True")
        assert response.status_code == 404

    def test_message_number_specified_whatsapp(self, uclient):
        """
        It should only return the 11th paragraph if 11th message is requested
        Please see class doc string for why this is a separate test
        """
        page = self.create_content_page(body_count=15)

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True&message=11")
        content = json.loads(response.content)

        assert content["body"]["message"] == 11
        assert content["body"]["next_message"] == 12
        assert content["body"]["previous_message"] == 10
        body = content["body"]["text"]["value"]["message"]
        assert body == "*Default whatsapp Content 11* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    def test_message_number_specified(self, uclient, platform):
        """
        It should only return the 11th paragraph if 11th message is requested
        """
        page = self.create_content_page(body_count=15, body_type=platform)

        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=True&message=11")
        content = json.loads(response.content)

        assert content["body"]["message"] == 11
        assert content["body"]["next_message"] == 12
        assert content["body"]["previous_message"] == 10
        body = content["body"]["text"]["message"]
        assert body == f"*Default {platform} Content 11* 🏥"

    def test_no_message_number_specified_whatsapp(self, uclient):
        """
        It should only return the first paragraph if no specific message is requested
        Please see class doc string for why this is a separate test
        """
        page = self.create_content_page()
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=True")
        content = response.json()

        assert content["body"]["message"] == 1
        assert content["body"]["previous_message"] is None
        assert content["body"]["total_messages"] == 1
        # Page revision only for whatsapp blocks
        assert content["body"]["revision"] == page.get_latest_revision().id
        body = content["body"]["text"]["value"]["message"]
        assert body == "*Default whatsapp Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    def test_no_message_number_specified(self, uclient, platform):
        """
        It should only return the first paragraph if no specific message is requested
        """
        page = self.create_content_page(body_type=platform)
        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=True")
        content = response.json()

        assert content["body"]["message"] == 1
        assert content["body"]["previous_message"] is None
        assert content["body"]["total_messages"] == 1
        body = content["body"]["text"]["message"]
        assert body == f"*Default {platform} Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_message_number_requested_out_of_range(self, uclient, platform):
        """
        It should return an appropriate error if requested message index is out of range
        """
        page = self.create_content_page(body_type=platform)
        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=True&message=3")

        assert response.status_code == 400
        assert response.json() == ["The requested message does not exist"]

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_message_number_requested_invalid(self, uclient, platform):
        """
        It should return an appropriate error if requested message is not a positive
        integer value
        """
        page = self.create_content_page(body_type=platform)
        response = uclient.get(
            f"/api/v2/pages/{page.id}/?{platform}=True&message=notint"
        )

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
        with django_assert_num_queries(16):
            uclient.get("/api/v2/pages/")

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_detail_view_content(self, uclient, platform):
        """
        Fetching the detail view of a page returns the page content.
        """
        page = self.create_content_page(tags=["self_help"], body_type=platform)
        response = uclient.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"
        assert meta["detail_url"] == f"http://localhost/api/v2/pages/{page.id}/"

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

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_detail_view_meta(self, uclient, platform):
        """
        Fetching the detail view of a page returns the page metadata.
        """
        page = self.create_content_page(tags=["self_help"], body_type=platform)
        response = uclient.get(f"/api/v2/pages/{page.id}/")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        parent = page.get_parent()

        assert meta == {
            "type": "home.ContentPage",
            "detail_url": f"http://localhost/api/v2/pages/{page.id}/",
            "html_url": page.get_full_url(),
            "slug": page.slug,
            "show_in_menus": "false",
            "seo_title": page.seo_title,
            "search_description": page.search_description,
            "first_published_at": page.first_published_at.strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "alias_of": page.alias_of,
            "parent": {
                "id": parent.id,
                "meta": {
                    "type": "home.ContentPageIndex",
                    "html_url": parent.get_full_url(),
                },
                "title": parent.title,
            },
            "locale": "en",
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
        assert meta["detail_url"] == f"http://localhost/api/v2/pages/{page.id}/"

        assert content["has_children"] is True

    def test_detail_view_whatsapp_message(self, uclient):
        """
        Fetching a detail page and selecting the WhatsApp content returns the
        first WhatsApp message in the body.
        Please see class doc string for why this is a separate test
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
        assert meta["detail_url"] == f"http://localhost/api/v2/pages/{page.id}/"

        assert content["id"] == page.id
        assert content["title"] == "default page"

        # There's a lot of body, so only check selected fields.
        body = content.pop("body")
        assert body["message"] == 1
        assert body["next_message"] is None
        assert body["previous_message"] is None
        assert body["total_messages"] == 1
        assert body["text"]["type"] == "Whatsapp_Message"
        assert body["text"]["value"]["message"] == "*Default whatsapp Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_detail_view_platform_enabled_no_message(self, uclient, platform):
        """
        Fetching a detail page and selecting the <platform> content returns a
        400 when <platform> is enabled but there are no <platform> messages in
        the body.
        """
        page = self.create_content_page(body_type=platform, body_count=0)
        setattr(page, f"enable_{platform}", True)
        page.save()

        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=true")
        content = response.json()

        assert response.status_code == 400
        assert content == ["The requested message does not exist"]

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    def test_detail_view_platform_message(self, uclient, platform):
        """
        Fetching a detail page and selecting the <platform> content returns the
        first <platform> message in the body.
        """
        page = self.create_content_page(body_type=platform)
        response = uclient.get(f"/api/v2/pages/{page.id}/?{platform}=true")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"
        assert meta["detail_url"] == f"http://localhost/api/v2/pages/{page.id}/"

        assert content["id"] == page.id
        assert content["title"] == "default page"

        # There's a lot of body, so only check selected fields.
        body = content.pop("body")
        assert body["message"] == 1
        assert body["next_message"] is None
        assert body["previous_message"] is None
        assert body["total_messages"] == 1
        assert body["text"]["message"] == f"*Default {platform} Content 1* 🏥"
        with pytest.raises(KeyError):
            body["text"]["type"]

    def test_detail_view_no_content_page(self, uclient):
        """
        We get a validation error if we request a page that doesn't exist.
        """
        # it should return the validation error for content page that doesn't exist
        response = uclient.get("/api/v2/pages/1/")
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

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        image_id = content["body"]["text"]["value"]["image"]

        assert image_id == image_id_expected

    def test_messenger_image(self, uclient):
        """
        Test that API returns image ID for messenger
        """
        mk_test_img()
        image_id_expected = Image.objects.first().id
        msg_body = "*Default messenger Content* 🏥"
        title = "default page"
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = [MBody(title, [MBlk(msg_body, image=image_id_expected)])]

        page = PageBuilder.build_cp(
            parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
        )
        response = uclient.get(f"/api/v2/pages/{page.id}/?messenger=true")
        content = response.json()

        image_id = content["body"]["text"]["image"]
        assert image_id == image_id_expected

    def test_viber_image(self, uclient):
        """
        Test that API returns image ID for viber
        """
        mk_test_img()
        image_id_expected = Image.objects.first().id
        msg_body = "*Default viber Content* 🏥"
        title = "default page"
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = [VBody(title, [VBlk(msg_body, image=image_id_expected)])]

        page = PageBuilder.build_cp(
            parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
        )
        response = uclient.get(f"/api/v2/pages/{page.id}/?viber=true")
        content = response.json()

        image_id = content["body"]["text"]["image"]
        assert image_id == page.viber_body._raw_data[0]["value"]["image"]

    def test_wa_media(self, uclient):
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

    def test_wa_doc(self, uclient):
        """
        Test that API returns doc ID for whatsapp
        """
        mk_test_doc()
        doc_id_expected = Document.objects.first().id
        msg_body = "*Default whatsapp Content* 🏥"
        title = "default page"
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = [WABody(title, [WABlk(msg_body, document=doc_id_expected)])]

        page = PageBuilder.build_cp(
            parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
        )
        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        doc_id = content["body"]["text"]["value"]["document"]
        assert doc_id == page.whatsapp_body._raw_data[0]["value"]["document"]


@pytest.mark.django_db
class TestWhatsAppMessages:
    """
    Test the WhatsApp specific functionality of ContentPage like buttons templates and
    variations
    """

    def create_content_page(
        self,
        buttons=None,
        list_title=None,
        list_items=None,
        next_prompt=None,
        footer=None,
        whatsapp_template_category=None,
        whatsapp_template_name=None,
        variation_messages=None,
    ):
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        buttons : [NextBtn | PageBtn]
            List of buttons to add to the content page.
        list_title : str
            Title of the list to add to the content page.
        list_items : [str]
            List of list items to add to the content page.
        next_prompt : str
            Next prompt string to add to the content page.
        footer : str
            Footer string to add to the content page.
        whatsapp_template_category : str
            Category of the WhatsApp template.
        whatsapp_template_name : str
            Name of the WhatsApp template
        variation_messages : [VarMsg]
            Variation messages added to the WhatsApp content block
        """
        title = "default page"
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        content_page = PageBuilder.build_cp(
            parent=main_menu,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=[
                WABody(
                    title,
                    [
                        WABlk(
                            "Test WhatsApp Message 1",
                            buttons=buttons or [],
                            list_title=list_title or "",
                            list_items=list_items or [],
                            next_prompt=next_prompt or "",
                            footer=footer or "",
                            variation_messages=variation_messages or [],
                        )
                    ],
                )
            ],
            whatsapp_template_category=whatsapp_template_category,
            whatsapp_template_name=whatsapp_template_name,
        )
        return content_page

    def test_whatsapp_detail_view_with_button(self, uclient):
        """
        Buttons in WhatsApp messages are present in the message body.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        target_page = PageBuilder.build_cp(
            parent=main_menu, slug="target-page", title="Target page", bodies=[]
        )
        form = Assessment.objects.create(
            title="Test form", slug="test-form", locale=target_page.locale
        )

        page = PageBuilder.build_cp(
            parent=main_menu,
            slug="page",
            title="Page",
            bodies=[
                WABody(
                    "Page",
                    [
                        WABlk(
                            "Button message",
                            buttons=[
                                NextBtn("Tell me more"),
                                PageBtn("Go elsewhere", page=target_page),
                                FormBtn("Start form", form=form),
                            ],
                        )
                    ],
                )
            ],
        )

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()
        [next_button, page_button, form_button] = content["body"]["text"]["value"][
            "buttons"
        ]
        next_button.pop("id")
        assert next_button == {
            "type": "next_message",
            "value": {"title": "Tell me more"},
        }
        page_button.pop("id")
        assert page_button == {
            "type": "go_to_page",
            "value": {"title": "Go elsewhere", "page": target_page.id},
        }
        form_button.pop("id")
        assert form_button == {
            "type": "go_to_form",
            "value": {"title": "Start form", "form": form.id},
        }

    def test_whatsapp_template_fields(self, uclient):
        """
        Should have the WhatsApp specific fields included in the body; if it's a
        template, what's the template name, the text body of the message.
        """
        page = self.create_content_page(
            whatsapp_template_category=ContentPage.WhatsAppTemplateCategory.MARKETING,
            whatsapp_template_name="test_template",
        )

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp")
        body = response.json()["body"]

        assert body["is_whatsapp_template"]
        assert body["whatsapp_template_name"] == "test_template"
        assert body["text"]["value"]["message"] == "Test WhatsApp Message 1"
        assert body["whatsapp_template_category"] == "MARKETING"

    def test_whatsapp_detail_view_with_variations(self, uclient):
        """
        Variation blocks in WhatsApp messages are present in the message body.
        """
        page = self.create_content_page(
            variation_messages=[
                VarMsg("Test Title - female variation", gender="female")
            ],
        )

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

    def test_list_items_no_title(self, uclient):
        """
        test that list items are present in the whatsapp message with no title given
        """
        page = self.create_content_page(
            list_items=[NextListItem("list item 1"), NextListItem("list item 2")]
        )

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        [item_1, item_2] = content["body"]["text"]["value"]["list_items"]
        item_1.pop("id")
        item_2.pop("id")

        assert content["body"]["text"]["value"]["list_title"] == ""
        assert item_1 == {"type": "item", "value": "list item 1"}
        assert item_2 == {"type": "item", "value": "list item 2"}

    def test_list_items(self, uclient):
        """
        test that list items are present in the whatsapp message
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        target_page = PageBuilder.build_cp(
            parent=main_menu, slug="target-page", title="Target page", bodies=[]
        )
        form = Assessment.objects.create(
            title="Test form", slug="test-form", locale=target_page.locale
        )

        page = PageBuilder.build_cp(
            parent=main_menu,
            slug="page",
            title="Page",
            bodies=[
                WABody(
                    "list body",
                    [
                        WABlk(
                            "List message",
                            list_items=[
                                NextListItem("list item 1"),
                                PageListItem("list item 2", page=target_page),
                                FormListItem("list item 3", form=form),
                            ],
                        )
                    ],
                )
            ],
        )

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items"]
        item_1.pop("id")
        item_2.pop("id")
        item_3.pop("id")

        assert item_1 == {"type": "item", "value": "list item 1"}
        assert item_2 == {"type": "item", "value": "list item 2"}
        assert item_3 == {"type": "item", "value": "list item 3"}

        [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items_v2"]
        item_1.pop("id")
        item_2.pop("id")
        item_3.pop("id")

        assert item_1 == {"type": "next_message", "value": {"title": "list item 1"}}
        assert item_2 == {
            "type": "go_to_page",
            "value": {"title": "list item 2", "page": target_page.id},
        }
        assert item_3 == {
            "type": "go_to_form",
            "value": {"title": "list item 3", "form": form.id},
        }

    def test_next_prompt(self, uclient):
        """
        test that next prompt is present in the whatsapp message
        """
        page = self.create_content_page(next_prompt="next prompt 1")

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        next_prompt = content["body"]["text"]["value"]["next_prompt"]

        assert next_prompt == "next prompt 1"

    def test_footer(self, uclient):
        """
        test that footer is present in the whatsapp message
        """
        page = self.create_content_page(footer="footer 1")

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        footer = content["body"]["text"]["value"]["footer"]

        assert footer == "footer 1"

    def test_empty_whatsapp(self, uclient):
        """
        All values except the message should be blank when nothing else is set on a whatsapp message
        """
        page = self.create_content_page()

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        whatsapp_value = content["body"]["text"]["value"]

        assert whatsapp_value == {
            "image": None,
            "media": None,
            "footer": "",
            "buttons": [],
            "message": "Test WhatsApp Message 1",
            "document": None,
            "list_title": "",
            "list_items": [],
            "next_prompt": "",
            "variation_messages": [],
        }


@pytest.mark.django_db
class TestOrderedContentSetAPI:
    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that all the tests in this class will use.
        """
        path = Path("home/tests/import-export-data/content2.csv")
        with path.open(mode="rb") as f:
            import_content(f, "CSV", queue.Queue())
        self.page1 = ContentPage.objects.first()
        site = Site.objects.get(is_default_site=True)
        self.default_locale = site.root_page.locale
        self.ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-1", locale=self.default_locale
        )
        self.ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        self.ordered_content_set.profile_fields.append(("gender", "female"))
        self.ordered_content_set.save()
        self.ordered_content_set.save_revision().publish()

        self.ordered_content_set_timed = OrderedContentSet(
            name="Test set timed",
            slug="ordered-set-timed-1",
            locale=self.default_locale,
        )
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
        self.ordered_content_set_timed.save_revision().publish()

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
        assert content["results"][0]["slug"] == self.ordered_content_set.slug
        assert (
            content["results"][0]["locale"]
            == self.ordered_content_set.locale.language_code
        )
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
        assert content["slug"] == self.ordered_content_set.slug
        assert content["locale"] == self.ordered_content_set.locale.language_code
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

    def test_orderedcontent_endpoint_with_drafts(self, uclient):
        """
        Unpublished ordered content sets are returned if the qa param is set.
        """
        self.ordered_content_set.unpublish()
        url = "/api/v2/orderedcontent/?qa=True"
        # it should return a list of ordered content sets with the unpublished one included
        response = uclient.get(url)
        content = json.loads(response.content)

        # the content set is not live but content is returned
        assert not self.ordered_content_set.live
        assert content["count"] == 2
        assert content["results"][0]["name"] == self.ordered_content_set.name
        assert content["results"][0]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

    def test_orderedcontent_endpoint_filter_on_slug(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        url = "/api/v2/orderedcontent/?slug=ordered-set-1"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

        assert content["results"][0]["name"] == self.ordered_content_set.name
        assert content["results"][0]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

    def test_orderedcntent_endpoint_filter_on_locale(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=pt
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?locale=pt"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_male_on_gender_profile_field(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        url = "/api/v2/orderedcontent/?gender=male"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_female_on_gender_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=female"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 2

    def test_orderedcontent_endpoint_filter_female_on_gender_profile_field_qa_flag_set(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()
        self.ordered_content_set.unpublish()

        url = "/api/v2/orderedcontent/?qa=true&gender=female"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 2

    def test_orderedcontent_endpoint_filter_on_age_profile_field(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?age=18 - 25"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_age_profile_field(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?age=7 - 8"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_on_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?relationship=single"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?relationship=in a relationship"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_gender_age_profile_field(self, uclient):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=male&age=18 - 25"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_gender_age_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=male&age=4 - 5"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_gender_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=male&relationship=single"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_gender_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=male&relationship=in a relationship"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_age_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?age=18 - 25&relationship=single"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_age_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("age", "4 - 5"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?age=4 - 5&relationship=in a relationship"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_filter_gender_age_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("age", "18 - 25"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=male&age=18 - 25&relationship=single"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 1

    def test_orderedcontent_endpoint_filter_incorrect_gender_age_relationship_profile_field(
        self, uclient
    ):
        """
        The correct ordered content sets are returned if the filter is applied.
        """
        site = Site.objects.get(is_default_site=True)
        ordered_content_set = OrderedContentSet(
            name="Test set", slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        ordered_content_set.profile_fields.append(("gender", "male"))
        ordered_content_set.profile_fields.append(("relationship", "single"))
        ordered_content_set.profile_fields.append(("age", "4 - 5"))
        ordered_content_set.save()
        ordered_content_set.save_revision().publish()

        url = "/api/v2/orderedcontent/?gender=female&age=4 - 5&relationship=in a relationship"
        response = uclient.get(url)
        content = json.loads(response.content)

        assert response.status_code == 200
        assert content["count"] == 0

    def test_orderedcontent_endpoint_without_drafts(self, uclient):
        """
        Unpublished ordered content sets are not returned if the qa param is not set.
        """
        self.ordered_content_set.unpublish()
        url = "/api/v2/orderedcontent/"
        # it should return a list of ordered content sets with the unpublished one excluded
        response = uclient.get(url)
        content = json.loads(response.content)

        # the content set is not live but content is returned
        assert not self.ordered_content_set.live
        assert content["count"] == 1
        assert content["results"][0]["name"] == self.ordered_content_set_timed.name
        assert content["results"][0]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

    def test_orderedcontent_detail_endpoint_with_drafts(self, uclient):
        """
        Unpublished ordered content sets are returned if the qa param is set.
        """
        self.ordered_content_set.unpublish()
        url = f"/api/v2/orderedcontent/{self.ordered_content_set.id}/?qa=True"
        # it should return specific ordered content set that is in draft
        response = uclient.get(url)
        content = json.loads(response.content)

        # the content set is not live but content is returned
        assert not self.ordered_content_set.live
        assert content["name"] == self.ordered_content_set.name
        assert content["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

    def test_orderedcontent_detail_endpoint_without_drafts(self, uclient, settings):
        """
        Unpublished ordered content sets are not returned if the qa param is not set.
        """
        settings.STATIC_ROOT = Path("home/tests/test_static")
        self.ordered_content_set.unpublish()
        url = f"/api/v2/orderedcontent/{self.ordered_content_set.id}"

        response = uclient.get(url, follow=True)

        assert response.status_code == 404

    def test_orderedcontent_new_draft(self, uclient):
        """
        New revisions are returned if the qa param is set
        """
        self.ordered_content_set.pages.append(
            (
                "pages",
                {
                    "contentpage": self.page1,
                    "time": 2,
                    "unit": "Hours",
                    "before_or_after": "After",
                    "contact_field": "something",
                },
            )
        )
        self.ordered_content_set.profile_fields.append(
            ("relationship", "in_a_relationship")
        )

        self.ordered_content_set.save_revision()

        response = uclient.get("/api/v2/orderedcontent/")
        content = json.loads(response.content)

        assert self.ordered_content_set.live

        assert content["count"] == 2
        assert len(content["results"][0]["profile_fields"]) == 1
        assert content["results"][0]["name"] == self.ordered_content_set.name
        assert content["results"][0]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["results"][1]["name"] == self.ordered_content_set_timed.name
        assert content["results"][1]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }

        response = uclient.get("/api/v2/orderedcontent/?qa=True")
        content = json.loads(response.content)
        assert content["count"] == 2
        assert len(content["results"][1]["profile_fields"]) == 2
        assert content["results"][1]["profile_fields"][0] == {
            "profile_field": "gender",
            "value": "female",
        }
        assert content["results"][1]["profile_fields"][1] == {
            "profile_field": "relationship",
            "value": "in_a_relationship",
        }
        assert content["results"][1]["pages"][1] == {
            "id": self.page1.id,
            "title": self.page1.title,
            "time": 2,
            "unit": "Hours",
            "before_or_after": "After",
            "contact_field": "something",
        }

    def test_orderedcontent_moderation(self):
        """
        Get default workflow for ordered content set
        """
        workflow = Workflow.objects.create(name="Test Workflow", active="t")
        content_type = ContentType.objects.get_for_model(OrderedContentSet)

        WorkflowContentType.objects.create(
            content_type_id=content_type.id, workflow_id=workflow.id
        )

        site = Site.objects.get(is_default_site=True)
        ordered_content_set_instance = OrderedContentSet(
            slug="ordered-set-2", locale=site.root_page.locale
        )
        ordered_content_set_default_workflow = (
            ordered_content_set_instance.get_default_workflow()
        )

        assert ordered_content_set_default_workflow == workflow

    def test_get_upload(self, admin_client):
        """
        Should return the data and not throw an exception
        """
        url = reverse("import_orderedcontentset")
        # NB gotta use the admin_client here
        response = admin_client.get(f"{url}", follow=True)
        content_str = response.content.decode("utf-8")
        assert "/admin/snippets/home/orderedcontentset/" in content_str
        assert response.status_code == 200

    def test_valid_document_extension(self):
        """
        Upload an invalid document type
        """
        document = Document.objects.create(
            title="Example Document", file="invalid_file.exe"
        )

        with pytest.raises(ValidationError) as validation_error:
            document.full_clean()

        assert (
            validation_error.value.messages[0]
            == "File extension “exe” is not allowed. Allowed extensions are: doc, docx, xls, xlsx, ppt, pptx, pdf, txt."
        )


@pytest.mark.django_db
class TestAssessmentAPI:
    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that all the tests in this class will use.
        """
        self.assessment = Assessment(title="Test Assessment", slug="test-assessment")
        self.high_result_page = ContentPage(
            title="high result",
            slug="high-result",
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
        self.medium_result_page = ContentPage(
            title="medium result",
            slug="medium-result",
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
        self.low_result_page = ContentPage(
            title="low result",
            slug="low-result",
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
        self.skip_high_result_page = ContentPage(
            title="skip result",
            slug="skip-result",
            enable_whatsapp=True,
            whatsapp_body=[
                {
                    "type": "Whatsapp_Message",
                    "value": {
                        "message": "test message",
                        "buttons": [
                            {
                                "type": "next_message",
                                "value": {"title": "You skipped a question"},
                            }
                        ],
                    },
                }
            ],
        )
        homepage = HomePage.objects.first()
        homepage.add_child(instance=self.high_result_page)
        homepage.add_child(instance=self.medium_result_page)
        homepage.add_child(instance=self.low_result_page)
        homepage.add_child(instance=self.skip_high_result_page)
        self.high_result_page.save_revision().publish()
        self.medium_result_page.save_revision().publish()
        self.low_result_page.save_revision().publish()
        self.skip_high_result_page.save_revision().publish()
        site = Site.objects.get(is_default_site=True)
        tag, _ = Tag.objects.get_or_create(name="tag1")
        self.assessment.tags.add(tag)
        tag, _ = Tag.objects.get_or_create(name="tag2")
        self.assessment.tags.add(tag)
        self.assessment.locale = site.root_page.locale
        self.assessment.high_result_page = self.high_result_page
        self.assessment.high_inflection = 5.0
        self.assessment.medium_result_page = self.medium_result_page
        self.assessment.medium_inflection = 2.0
        self.assessment.low_result_page = self.low_result_page
        self.assessment.skip_threshold = 3.0
        self.assessment.skip_high_result_page = self.skip_high_result_page
        self.assessment.generic_error = "This is a generic error"
        answers_block = blocks.ListBlock(AnswerBlock())
        answers_block_value = answers_block.to_python(
            [
                {
                    "answer": "Crunchie",
                    "score": "5",
                    "semantic_id": "crunchie",
                    "response": "Get that Friday feeling",
                },
                {
                    "answer": "Flake",
                    "score": "3",
                    "semantic_id": "flake",
                    "response": "",
                },
            ]
        )
        categorical_question_block = CategoricalQuestionBlock()
        categorical_question_block_value = categorical_question_block.to_python(
            {
                "question": "What is the best chocolate?",
                "error": "Invalid answer",
                "answers": answers_block_value,
                "semantic_id": "best_chocolate",
            }
        )
        self.assessment.questions.append(
            (
                "categorical_question",
                categorical_question_block_value,
            )
        )
        age_question_block = AgeQuestionBlock()
        age_question_block_value = age_question_block.to_python(
            {
                "question": "How old are you?",
                "error": "Invalid answer",
                "answers": None,
                "semantic_id": "age",
            }
        )
        self.assessment.questions.append(
            (
                "age_question",
                age_question_block_value,
            )
        )
        multiselect_question_block = MultiselectQuestionBlock()
        multiselect_question_block_value = multiselect_question_block.to_python(
            {
                "question": "Which chocolates are yummy?",
                "error": "Invalid answer",
                "answers": answers_block_value,
                "semantic_id": "yummy_chocolates",
            }
        )
        self.assessment.questions.append(
            (
                "multiselect_question",
                multiselect_question_block_value,
            )
        )
        freetext_question_block = FreeTextQuestionBlock()
        freetext_question_block_value = freetext_question_block.to_python(
            {
                "question": "How useful is this information?",
                "answers": None,
                "semantic_id": "usefulness",
            }
        )
        self.assessment.questions.append(
            (
                "freetext_question",
                freetext_question_block_value,
            )
        )
        integer_question_block = IntegerQuestionBlock()
        integer_question_block_value = integer_question_block.to_python(
            {
                "question": "What's your weight in kilograms?",
                "error": "Your weight should be between 40 and 500kg",
                "min": 40,
                "max": 500,
                "answers": None,
                "semantic_id": "weight",
            }
        )
        self.assessment.questions.append(
            (
                "integer_question",
                integer_question_block_value,
            )
        )
        year_of_birth_question_block = YearofBirthQuestionBlock()
        year_of_birth_question_block_value = year_of_birth_question_block.to_python(
            {
                "question": "What's your year of birth?",
                "error": "You entered an invalid year of birth",
                "explainer": "We need to know some things",
                "answers": None,
                "semantic_id": "year_of_birth",
            }
        )
        self.assessment.questions.append(
            (
                "year_of_birth_question",
                year_of_birth_question_block_value,
            )
        )
        self.assessment.save()

    def test_assessment_endpoint_with_page_keyword(self, uclient):
        response = uclient.get("/api/v2/assessment/?page=1")
        content = json.loads(response.content)
        assert content["count"] == 1

    def test_assessment_endpoint(self, uclient):
        response = uclient.get("/api/v2/assessment/")
        content = json.loads(response.content)
        assert content["count"] == 1
        assert content["results"][0]["title"] == self.assessment.title
        assert content["results"][0]["locale"] == self.assessment.locale.language_code
        assert content["results"][0]["slug"] == self.assessment.slug
        assert content["results"][0]["version"] == self.assessment.version
        assert sorted(content["results"][0]["tags"]) == sorted(
            [tag.name for tag in self.assessment.tags.all()]
        )
        assert content["results"][0]["generic_error"] == self.assessment.generic_error

        meta = content["results"][0]["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["results"][0]["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["high_inflection"] == 5.0

        meta = content["results"][0]["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["results"][0]["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["medium_inflection"] == 2.0

        meta = content["results"][0]["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["results"][0]["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

        meta = content["results"][0]["skip_high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.skip_high_result_page.slug
        assert meta["parent"]["id"] == self.skip_high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.skip_high_result_page.id}/"
        )
        assert content["results"][0]["skip_high_result_page"] == {
            "id": self.skip_high_result_page.id,
            "title": self.skip_high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["skip_threshold"] == 3.0

        assert content["results"][0]["questions"][0] == {
            "id": self.assessment.questions[0].id,
            "question_type": "categorical_question",
            "question": "What is the best chocolate?",
            "explainer": None,
            "error": "Invalid answer",
            "min": None,
            "max": None,
            "answers": [
                {
                    "answer": "Crunchie",
                    "score": "5",
                    "semantic_id": "crunchie",
                    "response": "Get that Friday feeling",
                },
                {
                    "answer": "Flake",
                    "score": "3",
                    "semantic_id": "flake",
                    "response": "",
                },
            ],
            "semantic_id": "best_chocolate",
        }
        assert content["results"][0]["questions"][1] == {
            "id": self.assessment.questions[1].id,
            "question_type": "age_question",
            "question": "How old are you?",
            "explainer": None,
            "error": "Invalid answer",
            "min": None,
            "max": None,
            "answers": [],
            "semantic_id": "age",
        }
        assert content["results"][0]["questions"][2] == {
            "id": self.assessment.questions[2].id,
            "question_type": "multiselect_question",
            "question": "Which chocolates are yummy?",
            "explainer": None,
            "error": "Invalid answer",
            "min": None,
            "max": None,
            "answers": [
                {
                    "answer": "Crunchie",
                    "score": "5",
                    "semantic_id": "crunchie",
                    "response": "Get that Friday feeling",
                },
                {
                    "answer": "Flake",
                    "score": "3",
                    "semantic_id": "flake",
                    "response": "",
                },
            ],
            "semantic_id": "yummy_chocolates",
        }
        assert content["results"][0]["questions"][3] == {
            "id": self.assessment.questions[3].id,
            "question_type": "freetext_question",
            "question": "How useful is this information?",
            "explainer": None,
            "error": None,
            "min": None,
            "max": None,
            "answers": [],
            "semantic_id": "usefulness",
        }
        assert content["results"][0]["questions"][4] == {
            "id": self.assessment.questions[4].id,
            "question_type": "integer_question",
            "question": "What's your weight in kilograms?",
            "explainer": None,
            "error": "Your weight should be between 40 and 500kg",
            "min": 40,
            "max": 500,
            "answers": [],
            "semantic_id": "weight",
        }
        assert content["results"][0]["questions"][5] == {
            "id": self.assessment.questions[5].id,
            "question_type": "year_of_birth_question",
            "question": "What's your year of birth?",
            "explainer": "We need to know some things",
            "error": "You entered an invalid year of birth",
            "min": None,
            "max": None,
            "answers": [],
            "semantic_id": "year_of_birth",
        }

    def test_assessment_detail_endpoint(self, uclient):
        response = uclient.get(f"/api/v2/assessment/{self.assessment.id}/")
        content = json.loads(response.content)
        assert content["title"] == self.assessment.title
        assert content["locale"] == self.assessment.locale.language_code
        assert content["slug"] == self.assessment.slug
        assert content["version"] == self.assessment.version
        assert sorted(content["tags"]) == sorted(
            [tag.name for tag in self.assessment.tags.all()]
        )
        assert content["generic_error"] == self.assessment.generic_error

        meta = content["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["high_inflection"] == 5.0

        meta = content["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["medium_inflection"] == 2.0

        meta = content["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

    def test_assessment_endpoint_with_drafts(self, uclient):
        """
        Unpublished assessments are returned if the qa param is set.
        """
        self.assessment.unpublish()
        url = "/api/v2/assessment/?qa=True"
        # it should return a list of assessments with the unpublished one included
        response = uclient.get(url)
        content = json.loads(response.content)

        # the assessment is not live but content is returned
        assert not self.assessment.live
        assert content["count"] == 1
        assert content["results"][0]["title"] == self.assessment.title

        meta = content["results"][0]["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["results"][0]["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["high_inflection"] == 5.0

        meta = content["results"][0]["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["results"][0]["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["medium_inflection"] == 2.0

        meta = content["results"][0]["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["results"][0]["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

    def test_assessment_endpoint_without_drafts(self, uclient):
        """
        Unpublished assessments are not returned if the qa param is not set.
        """
        self.assessment.unpublish()
        url = "/api/v2/assessment/"
        # it should return nothing
        response = uclient.get(url)
        content = json.loads(response.content)

        # the assessment is not live
        assert not self.assessment.live
        assert content["count"] == 0

    def test_assessment_detail_endpoint_with_drafts(self, uclient):
        """
        Unpublished assessments are returned if the qa param is set.
        """
        self.assessment.unpublish()
        url = f"/api/v2/assessment/{self.assessment.id}/?qa=True"
        # it should return specific assessment that is in draft
        response = uclient.get(url)
        content = json.loads(response.content)

        # the assessment is not live but content is returned
        assert not self.assessment.live
        assert content["title"] == self.assessment.title

        meta = content["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["high_inflection"] == 5.0

        meta = content["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["medium_inflection"] == 2.0

        meta = content["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

    def test_assessment_detail_endpoint_without_drafts(self, uclient, settings):
        """
        Unpublished assessments are not returned if the qa param is not set.
        """
        settings.STATIC_ROOT = Path("home/tests/test_static")
        self.assessment.unpublish()
        url = f"/api/v2/assessment/{self.assessment.id}"

        response = uclient.get(url, follow=True)

        assert response.status_code == 404

    def test_assessment_new_draft(self, uclient):
        """
        New revisions are returned if the qa param is set
        """
        high_result_page = ContentPage(
            title="new high result",
            slug="new-high-result",
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
        homepage.add_child(instance=high_result_page)
        high_result_page.save_revision().publish()
        self.assessment.high_result_page = high_result_page
        self.assessment.high_inflection = 15.0
        self.assessment.medium_inflection = 12.0

        self.assessment.save_revision()

        response = uclient.get("/api/v2/assessment/")
        content = json.loads(response.content)

        assert self.assessment.live

        assert content["results"][0]["title"] == self.assessment.title

        meta = content["results"][0]["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["results"][0]["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["high_inflection"] == 5.0

        meta = content["results"][0]["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["results"][0]["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["medium_inflection"] == 2.0

        meta = content["results"][0]["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["results"][0]["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

        response = uclient.get("/api/v2/assessment/?qa=True")
        content = json.loads(response.content)
        assert content["results"][0]["title"] == self.assessment.title

        meta = content["results"][0]["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == high_result_page.slug
        assert meta["parent"]["id"] == high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{high_result_page.id}/"
        )
        assert content["results"][0]["high_result_page"] == {
            "id": high_result_page.id,
            "title": high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["high_inflection"] == 15.0

        meta = content["results"][0]["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["results"][0]["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["medium_inflection"] == 12.0

        meta = content["results"][0]["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["results"][0]["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

    def test_assessment_endpoint_filter_by_tag(self, uclient):
        response = uclient.get("/api/v2/assessment/?tag=tag1")
        content = json.loads(response.content)
        assert content["count"] == 1
        assert content["results"][0]["title"] == self.assessment.title

        meta = content["results"][0]["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["results"][0]["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["high_inflection"] == 5.0

        meta = content["results"][0]["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["results"][0]["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["results"][0]["medium_inflection"] == 2.0

        meta = content["results"][0]["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["results"][0]["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

        response = uclient.get("/api/v2/assessment/?tag=tag3")
        content = json.loads(response.content)
        assert content["count"] == 0

    def test_assessment_detail_endpoint_filter_by_tag(self, uclient):
        response = uclient.get(f"/api/v2/assessment/{self.assessment.id}/?tag=tag1")
        content = json.loads(response.content)
        assert content["title"] == self.assessment.title

        meta = content["high_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.high_result_page.slug
        assert meta["parent"]["id"] == self.high_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.high_result_page.id}/"
        )
        assert content["high_result_page"] == {
            "id": self.high_result_page.id,
            "title": self.high_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["high_inflection"] == 5.0

        meta = content["medium_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.medium_result_page.slug
        assert meta["parent"]["id"] == self.medium_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.medium_result_page.id}/"
        )
        assert content["medium_result_page"] == {
            "id": self.medium_result_page.id,
            "title": self.medium_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }
        assert content["medium_inflection"] == 2.0

        meta = content["low_result_page"].pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == self.low_result_page.slug
        assert meta["parent"]["id"] == self.low_result_page.get_parent().id
        assert meta["locale"] == "en"
        assert (
            meta["detail_url"]
            == f"http://localhost/api/v2/pages/{self.low_result_page.id}/"
        )
        assert content["low_result_page"] == {
            "id": self.low_result_page.id,
            "title": self.low_result_page.title,
            "body": {"text": []},
            "has_children": False,
            "related_pages": [],
            "subtitle": "",
            "quick_replies": [],
            "tags": [],
            "triggers": [],
        }

        response = uclient.get("/api/v2/assessment/?tag=tag3")
        content = json.loads(response.content)
        assert content["count"] == 0


@pytest.mark.django_db
class TestAssessmentLocaleFilterAPI:
    @pytest.fixture(autouse=True)
    def create_test_data(self):
        """
        Create the content that the tests in this class will use.
        """
        self.locale_fr, _ = Locale.objects.get_or_create(language_code="fr")
        self.locale_en, _ = Locale.objects.get_or_create(language_code="en")

        self.assessment_fr = Assessment.objects.create(
            title="French Assessment",
            slug="french-assessment",
            version="1.0",
            locale=self.locale_fr,
            live=True,
        )

        self.assessment_en = Assessment.objects.create(
            title="English Assessment",
            slug="english-assessment",
            version="1.0",
            locale=self.locale_en,
            live=True,
        )

    def test_assessment_locale_filter_fr(self, admin_client):
        """
        Ensure that only French assessment is returned
        """
        response_fr = admin_client.get("/api/v2/assessment/", {"locale": "fr"})

        assert response_fr.status_code == 200
        response_data_fr = response_fr.json()

        assert len(response_data_fr["results"]) == 1
        assert response_data_fr["results"][0]["locale"] == "fr"
        assert response_data_fr["results"][0]["title"] == "French Assessment"

    def test_assessment_locale_filter_en(self, admin_client):
        """
        Ensure that only English assessment is returned
        """
        response_en = admin_client.get("/api/v2/assessment/", {"locale": "en"})
        assert response_en.status_code == 200
        response_data_en = response_en.json()
        assert len(response_data_en["results"]) == 1
        assert response_data_en["results"][0]["locale"] == "en"
        assert response_data_en["results"][0]["title"] == "English Assessment"
