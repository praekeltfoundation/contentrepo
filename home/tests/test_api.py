import json
import queue
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import File  # type: ignore
from django.core.files.images import ImageFile  # type: ignore
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed
from wagtail.documents.models import Document  # type: ignore
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Workflow, WorkflowContentType
from wagtailmedia.models import Media  # type: ignore

from home.content_import_export import import_content
from home.models import (
    ContentPage,
    HomePage,
    OrderedContentSet,
    PageView,
)

from .page_builder import (
    MBlk,
    MBody,
    NextBtn,
    PageBuilder,
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
        assert response.content == b""

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
        with django_assert_num_queries(8):
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
        list_items=None,
        next_prompt=None,
        footer=None,
        whatsapp_template_category=None,
        whatsapp_template_name=None,
        variation_messages=None,
        example_values=None,
    ):
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        buttons : [NextBtn | PageBtn]
            List of buttons to add to the content page.
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
        example_values : [str]
            example values for whatsapp templates
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
                            list_items=list_items or [],
                            next_prompt=next_prompt or "",
                            footer=footer or "",
                            variation_messages=variation_messages or [],
                            example_values=example_values or [],
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
        Next page buttons in WhatsApp messages are present in the message body.
        """
        page = self.create_content_page(buttons=[NextBtn("Tell me more")])

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true&message=1")
        content = response.json()
        [button] = content["body"]["text"]["value"]["buttons"]
        button.pop("id")
        assert button == {"type": "next_message", "value": {"title": "Tell me more"}}

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

    def test_whatsapp_template_variables(self, uclient):
        """
        Variables in WhatsApp templates are present in the message body.
        """
        page = self.create_content_page(
            example_values=["test value 1"],
        )

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        [example_values_content] = content["body"]["text"]["value"]["example_values"]
        example_values_content.pop("id")

        assert example_values_content == {"type": "item", "value": "test value 1"}

    def test_list_items(self, uclient):
        """
        test that list items are present in the whatsapp message
        """
        page = self.create_content_page(list_items=["list item 1", "list item 2"])

        response = uclient.get(f"/api/v2/pages/{page.id}/?whatsapp=true")
        content = response.json()

        [item_1, item_2] = content["body"]["text"]["value"]["list_items"]
        item_1.pop("id")
        item_2.pop("id")

        assert item_1 == {"type": "item", "value": "list item 1"}
        assert item_2 == {"type": "item", "value": "list item 2"}

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
            "list_items": [],
            "next_prompt": "",
            "example_values": [],
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
        self.ordered_content_set = OrderedContentSet(name="Test set")
        self.ordered_content_set.pages.append(("pages", {"contentpage": self.page1}))
        self.ordered_content_set.profile_fields.append(("gender", "female"))
        self.ordered_content_set.save()
        self.ordered_content_set.save_revision().publish()

        self.ordered_content_set_timed = OrderedContentSet(name="Test set timed")
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

        ordered_content_set_instance = OrderedContentSet()
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
