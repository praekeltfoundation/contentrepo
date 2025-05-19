import json
from pathlib import Path

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


# @pytest.fixture()
# def admin_client(client, django_user_model):
#     """
#     Access admin interface
#     """
#     creds = {"username": "test", "password": "test"}
#     django_user_model.objects.create_superuser(**creds)
#     client.login(**creds)
#     return client


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


# @pytest.mark.django_db
# class TestWhatsAppMessagesAPIV3:
#     """
#     Test the WhatsApp specific functionality of ContentPage like buttons templates and
#     variations
#     """

#     def create_content_page(
#         self,
#         buttons=None,
#         list_title=None,
#         list_items=None,
#         next_prompt=None,
#         footer=None,
#         whatsapp_template_category=None,
#         whatsapp_template_name=None,
#         variation_messages=None,
#     ):
#         """
#         Helper function to create pages needed for each test.

#         Parameters
#         ----------
#         buttons : [NextBtn | PageBtn]
#             List of buttons to add to the content page.
#         list_title : str
#             Title of the list to add to the content page.
#         list_items : [str]
#             List of list items to add to the content page.
#         next_prompt : str
#             Next prompt string to add to the content page.
#         footer : str
#             Footer string to add to the content page.
#         whatsapp_template_category : str
#             Category of the WhatsApp template.
#         whatsapp_template_name : str
#             Name of the WhatsApp template
#         variation_messages : [VarMsg]
#             Variation messages added to the WhatsApp content block
#         """
#         title = "default page"
#         home_page = HomePage.objects.first()
#         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

#         content_page = PageBuilder.build_cp(
#             parent=main_menu,
#             slug=title.replace(" ", "-"),
#             title=title,
#             bodies=[
#                 WABody(
#                     title,
#                     [
#                         WABlk(
#                             "Test WhatsApp Message 1",
#                             buttons=buttons or [],
#                             list_title=list_title or "",
#                             list_items=list_items or [],
#                             next_prompt=next_prompt or "",
#                             footer=footer or "",
#                             variation_messages=variation_messages or [],
#                         )
#                     ],
#                 )
#             ],
#             whatsapp_template_category=whatsapp_template_category,
#             whatsapp_template_name=whatsapp_template_name,
#         )
#         return content_page

#     def test_whatsapp_detail_view_with_button(self, uclient):
#         """
#         Buttons in WhatsApp messages are present in the message body.
#         """
#         home_page = HomePage.objects.first()
#         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
#         target_page = PageBuilder.build_cp(
#             parent=main_menu, slug="target-page", title="Target page", bodies=[]
#         )
#         form = Assessment.objects.create(
#             title="Test form", slug="test-form", locale=target_page.locale
#         )

#         page = PageBuilder.build_cp(
#             parent=main_menu,
#             slug="page",
#             title="Page",
#             bodies=[
#                 WABody(
#                     "Page",
#                     [
#                         WABlk(
#                             "Button message",
#                             buttons=[
#                                 NextBtn("Tell me more"),
#                                 PageBtn("Go elsewhere", page=target_page),
#                                 FormBtn("Start form", form=form),
#                             ],
#                         )
#                     ],
#                 )
#             ],
#         )
#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         [next_button, page_button, form_button] = content["body"]["text"]["value"][
#             "buttons"
#         ]
#         next_button.pop("id")
#         assert next_button == {
#             "type": "next_message",
#             "value": {"title": "Tell me more"},
#         }
#         page_button.pop("id")
#         assert page_button == {
#             "type": "go_to_page",
#             "value": {"title": "Go elsewhere", "page": target_page.id},
#         }
#         form_button.pop("id")
#         assert form_button == {
#             "type": "go_to_form",
#             "value": {"title": "Start form", "form": form.id},
#         }

#     def test_whatsapp_template_fields(self, uclient):
#         """
#         Should have the WhatsApp specific fields included in the body; if it's a
#         template, what's the template name, the text body of the message.
#         """
#         page = self.create_content_page(
#             whatsapp_template_category=ContentPage.WhatsAppTemplateCategory.MARKETING,
#             whatsapp_template_name="test_template",
#         )

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp")
#         body = response.json()["body"]

#         assert body["is_whatsapp_template"]
#         assert body["whatsapp_template_name"] == "test_template"
#         assert body["text"]["value"]["message"] == "Test WhatsApp Message 1"
#         assert body["whatsapp_template_category"] == "MARKETING"

#     def test_whatsapp_detail_view_with_variations(self, uclient):
#         """
#         Variation blocks in WhatsApp messages are present in the message body.
#         """
#         page = self.create_content_page(
#             variation_messages=[
#                 VarMsg("Test Title - female variation", gender="female")
#             ],
#         )

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true&message=1")
#         content = response.json()

#         var_content = content["body"]["text"]["value"]["variation_messages"]
#         assert len(var_content) == 1
#         assert var_content[0]["profile_field"] == "gender"
#         assert var_content[0]["value"] == "female"
#         assert var_content[0]["message"] == "Test Title - female variation"

#     def test_list_items_no_title(self, uclient):
#         """
#         test that list items are present in the whatsapp message with no title given
#         """
#         page = self.create_content_page(
#             list_items=[NextListItem("list item 1"), NextListItem("list item 2")]
#         )

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         [item_1, item_2] = content["body"]["text"]["value"]["list_items"]
#         item_1.pop("id")
#         item_2.pop("id")

#         assert content["body"]["text"]["value"]["list_title"] == ""
#         assert item_1 == {"type": "item", "value": "list item 1"}
#         assert item_2 == {"type": "item", "value": "list item 2"}

#     def test_list_items(self, uclient):
#         """
#         test that list items are present in the whatsapp message
#         """
#         home_page = HomePage.objects.first()
#         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
#         target_page = PageBuilder.build_cp(
#             parent=main_menu, slug="target-page", title="Target page", bodies=[]
#         )
#         form = Assessment.objects.create(
#             title="Test form", slug="test-form", locale=target_page.locale
#         )

#         page = PageBuilder.build_cp(
#             parent=main_menu,
#             slug="page",
#             title="Page",
#             bodies=[
#                 WABody(
#                     "list body",
#                     [
#                         WABlk(
#                             "List message",
#                             list_items=[
#                                 NextListItem("list item 1"),
#                                 PageListItem("list item 2", page=target_page),
#                                 FormListItem("list item 3", form=form),
#                             ],
#                         )
#                     ],
#                 )
#             ],
#         )

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items"]
#         item_1.pop("id")
#         item_2.pop("id")
#         item_3.pop("id")

#         assert item_1 == {"type": "item", "value": "list item 1"}
#         assert item_2 == {"type": "item", "value": "list item 2"}
#         assert item_3 == {"type": "item", "value": "list item 3"}

#         [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items_v2"]
#         item_1.pop("id")
#         item_2.pop("id")
#         item_3.pop("id")

#         assert item_1 == {"type": "next_message", "value": {"title": "list item 1"}}
#         assert item_2 == {
#             "type": "go_to_page",
#             "value": {"title": "list item 2", "page": target_page.id},
#         }
#         assert item_3 == {
#             "type": "go_to_form",
#             "value": {"title": "list item 3", "form": form.id},
#         }

#     def test_next_prompt(self, uclient):
#         """
#         test that next prompt is present in the whatsapp message
#         """
#         page = self.create_content_page(next_prompt="next prompt 1")

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         next_prompt = content["body"]["text"]["value"]["next_prompt"]

#         assert next_prompt == "next prompt 1"

#     def test_footer(self, uclient):
#         """
#         test that footer is present in the whatsapp message
#         """
#         page = self.create_content_page(footer="footer 1")

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         footer = content["body"]["text"]["value"]["footer"]

#         assert footer == "footer 1"

#     def test_empty_whatsapp(self, uclient):
#         """
#         All values except the message should be blank when nothing else is set on a whatsapp message
#         """
#         page = self.create_content_page()

#         response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
#         content = response.json()

#         whatsapp_value = content["body"]["text"]["value"]

#         assert whatsapp_value == {
#             "image": None,
#             "media": None,
#             "footer": "",
#             "buttons": [],
#             "message": "Test WhatsApp Message 1",
#             "document": None,
#             "example_values": [],
#             "list_title": "",
#             "list_items": [],
#             "next_prompt": "",
#             "variation_messages": [],
#         }


@pytest.mark.django_db
class TestWhatsAppTemplateAPIV3:
    @classmethod
    def create_whatsapp_template(
        self,
        name="Default name",
        message="Default message",
        category="UTILITY",
        locale="en",
        publish=False,
    ) -> WhatsAppTemplate:
        locale = Locale.objects.get(language_code="en")
        template = WhatsAppTemplate(
            name=name, message=message, category=category, locale=locale
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
            name="Test Template 1",
            message="This is a test message",
            category="UTILITY",
            locale="en",
        )

        # it should return 1 page for correct tag, excluding unpublished pages with the
        # same tag
        response = uclient.get("/api/v3/whatsapptemplates/?qa=True")
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
            name="Test Template 2",
            message="*Default unpublished template 1* 🏥",
            category="UTILITY",
            locale="en",
            publish=False,
        )

        url = f"/api/v3/whatsapptemplates/{template.id}/?qa=True"
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
        response = uclient.get("/api/v3/pages/?tag=Menu&qa=True")
        content = json.loads(response.content)
        assert content["count"] == 2

        # it should return all pages for no tag, excluding home pages and index pages
        response = uclient.get("/api/v3/pages/?tag=")
        content = json.loads(response.content)
        assert content["count"] == 3

    # TODO: This is currently breaking. Decide whether to fix or leave out of this file
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
        response = uclient.get("/api/v3/pages/?web=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only whatsapp pages if filtered
        response = uclient.get("/api/v3/pages/?whatsapp=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only sms pages if filtered
        response = uclient.get("/api/v3/pages/?sms=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only ussd pages if filtered
        response = uclient.get("/api/v3/pages/?ussd=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only messenger pages if filtered
        response = uclient.get("/api/v3/pages/?messenger=true")
        content = json.loads(response.content)
        assert content["count"] == 1
        # it should return only viber pages if filtered
        response = uclient.get("/api/v3/pages/?viber=true")
        content = json.loads(response.content)
        assert content["count"] == 0
        # it should return all pages for no filter
        response = uclient.get("/api/v3/pages/")
        content = json.loads(response.content)
        # exclude home pages and index pages
        assert content["count"] == 5

    def test_whatsapp_draft(self, uclient):
        """
        Unpublished whatsapp pages are returned if the qa param is set.
        """
        page = self.create_content_page(publish=False)

        url = f"/api/v3/pages/{page.id}/?whatsapp=True&qa=True"
        # it should return specific page that is in draft
        response = uclient.get(url)
        content = response.json()

        # the page is not live but whatsapp content is returned
        assert not page.live
        body = content["messages"][0]["message"]
        assert body == "*Default whatsapp Content 1* 🏥"

    # TODO: This is currently breaking. Fix as part of API refining
    # @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    # def test_message_draft(self, uclient, platform):
    #     """
    #     Unpublished <platform> pages are returned if the qa param is set.
    #     """
    #     page = self.create_content_page(publish=False, body_type=platform)

    #     url = f"/api/v3/pages/{page.id}/?{platform}=True&qa=True"
    #     # it should return specific page that is in draft
    #     response = uclient.get(url)
    #     content = response.json()
    #     print(content["messages"])
    #     # the page is not live but messenger content is returned
    #     assert not page.live
    #     body = content["messages"][0]["message"]
    #     assert body == f"*Default {platform} Content 1* 🏥"

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_platform_disabled(self, uclient, platform):
        """
        It should not return the body if enable_<platform>=false
        """
        page = self.create_content_page(body_type=platform)

        response = uclient.get(f"/api/v3/pages/{page.id}/?{platform}=True")
        assert response.content != b""

        setattr(page, f"enable_{platform}", False)
        page.save_revision().publish()

        response = uclient.get(f"/api/v3/pages/{page.id}/?{platform}=True")
        assert response.status_code == 404

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
            with django_assert_num_queries(16):
                uclient.get("/api/v3/pages/")

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_detail_view_content(self, uclient, platform):
        """
        Fetching the detail view of a page returns the page content.
        """
        page = self.create_content_page(tags=["self_help"], body_type=platform)
        response = uclient.get(f"/api/v3/pages/{page.id}/")
        content = response.json()

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"
        assert meta["detail_url"] == f"http://localhost/api/v3/pages/{page.id}/"

        assert content == {
            "slug": "will-go-here",
            "title": "default page",
            "subtitle": "",
            "messages": None,
            "tags": ["self_help"],
            "triggers": [],
            "quick_replies": [],
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

        # There's a lot of metadata, so only check selected fields.
        meta = content.pop("meta")
        assert meta["type"] == "home.ContentPage"
        assert meta["slug"] == page.slug
        assert meta["parent"]["id"] == page.get_parent().id
        assert meta["locale"] == "en"
        assert meta["detail_url"] == f"http://localhost/api/v3/pages/{page.id}/"

        assert content["has_children"] is True

    # TODO: FIX THIS
    # def test_detail_view_whatsapp_message(self, uclient):
    #     """
    #     Fetching a detail page and selecting the WhatsApp content returns the
    #     first WhatsApp message in the body.
    #     Please see class doc string for why this is a separate test
    #     """
    #     page = self.create_content_page()
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
    #     content = response.json()

    #     # There's a lot of metadata, so only check selected fields.
    #     meta = content.pop("meta")
    #     assert meta["type"] == "home.ContentPage"
    #     assert meta["slug"] == page.slug
    #     assert meta["parent"]["id"] == page.get_parent().id
    #     assert meta["locale"] == "en"
    #     assert meta["detail_url"] == f"http://localhost/api/v3/pages/{page.id}/"

    #     assert content["id"] == page.id
    #     assert content["title"] == "default page"
    #     # There's a lot of body, so only check selected fields.
    #     body = content.pop("messages")
    #     assert body["message"] == 1
    #     assert body["next_message"] is None
    #     assert body["previous_message"] is None
    #     assert body["total_messages"] == 1
    #     assert body["text"]["type"] == "Whatsapp_Message"
    #     assert body["text"]["value"]["message"] == "*Default whatsapp Content 1* 🏥"

    # @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    # def test_detail_view_platform_enabled_no_message(self, uclient, platform):
    #     """
    #     Fetching a detail page and selecting the <platform> content returns a
    #     400 when <platform> is enabled but there are no <platform> messages in
    #     the body.
    #     """
    #     page = self.create_content_page(body_type=platform, body_count=0)
    #     setattr(page, f"enable_{platform}", True)
    #     page.save()

    #     response = uclient.get(f"/api/v3/pages/{page.id}/?{platform}=true")
    #     content = response.json()

    #     assert response.status_code == 400
    #     assert content == ["The requested message does not exist"]

    # @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WHATSAPP)
    # def test_detail_view_platform_message(self, uclient, platform):
    #     """
    #     Fetching a detail page and selecting the <platform> content returns the
    #     first <platform> message in the body.
    #     """
    #     page = self.create_content_page(body_type=platform)
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?{platform}=true")
    #     content = response.json()

    #     # There's a lot of metadata, so only check selected fields.
    #     meta = content.pop("meta")
    #     assert meta["type"] == "home.ContentPage"
    #     assert meta["slug"] == page.slug
    #     assert meta["parent"]["id"] == page.get_parent().id
    #     assert meta["locale"] == "en"
    #     assert meta["detail_url"] == f"http://localhost/api/v3/pages/{page.id}/"

    #     assert content["id"] == page.id
    #     assert content["title"] == "default page"

    #     # There's a lot of body, so only check selected fields.
    #     body = content.pop("body")
    #     assert body["message"] == 1
    #     assert body["next_message"] is None
    #     assert body["previous_message"] is None
    #     assert body["total_messages"] == 1
    #     assert body["text"]["message"] == f"*Default {platform} Content 1* 🏥"
    #     with pytest.raises(KeyError):
    #         body["text"]["type"]

    def test_detail_view_no_content_page(self, uclient):
        """
        We get a validation error if we request a page that doesn't exist.
        """
        # it should return the validation error for content page that doesn't exist
        response = uclient.get("/api/v3/pages/1/")
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

        response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")

        content = response.json()

        image_id = content["messages"][0]["image"]

        assert image_id == image_id_expected

    # def test_messenger_image(self, uclient):
    #     """
    #     Test that API returns image ID for messenger
    #     """
    #     mk_test_img()
    #     image_id_expected = Image.objects.first().id
    #     msg_body = "*Default messenger Content* 🏥"
    #     title = "default page"
    #     home_page = HomePage.objects.first()
    #     main_menu = home_page.get_children().filter(slug="main-menu").first()
    #     if not main_menu:
    #         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    #     parent = main_menu

    #     bodies = [MBody(title, [MBlk(msg_body, image=image_id_expected)])]

    #     page = PageBuilder.build_cp(
    #         parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
    #     )
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?messenger=true")
    #     content = response.json()

    #     image_id = content["messages"][0]["image"]
    #     assert image_id == image_id_expected

    # def test_viber_image(self, uclient):
    #     """
    #     Test that API returns image ID for viber
    #     """
    #     mk_test_img()
    #     image_id_expected = Image.objects.first().id
    #     msg_body = "*Default viber Content* 🏥"
    #     title = "default page"
    #     home_page = HomePage.objects.first()
    #     main_menu = home_page.get_children().filter(slug="main-menu").first()
    #     if not main_menu:
    #         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    #     parent = main_menu

    #     bodies = [VBody(title, [VBlk(msg_body, image=image_id_expected)])]

    #     page = PageBuilder.build_cp(
    #         parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
    #     )
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?viber=true")
    #     content = response.json()

    #     image_id = content["messages"][0]["image"]
    #     assert image_id == page.viber_body._raw_data[0]["value"]["image"]

    # def test_wa_media(self, uclient):
    #     """
    #     Test that API returns media ID for whatsapp
    #     """
    #     mk_test_media()
    #     media_id_expected = Media.objects.first().id
    #     msg_body = "*Default whatsapp Content* 🏥"
    #     title = "default page"
    #     home_page = HomePage.objects.first()
    #     main_menu = home_page.get_children().filter(slug="main-menu").first()
    #     if not main_menu:
    #         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    #     parent = main_menu

    #     bodies = [WABody(title, [WABlk(msg_body, media=media_id_expected)])]

    #     page = PageBuilder.build_cp(
    #         parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
    #     )
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
    #     content = response.json()

    #     media_id = content["messages"][0]["media"]
    #     assert media_id == page.whatsapp_body._raw_data[0]["value"]["media"]

    # def test_wa_doc(self, uclient):
    #     """
    #     Test that API returns doc ID for whatsapp
    #     """
    #     mk_test_doc()
    #     doc_id_expected = Document.objects.first().id
    #     msg_body = "*Default whatsapp Content* 🏥"
    #     title = "default page"
    #     home_page = HomePage.objects.first()
    #     main_menu = home_page.get_children().filter(slug="main-menu").first()
    #     if not main_menu:
    #         main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    #     parent = main_menu

    #     bodies = [WABody(title, [WABlk(msg_body, document=doc_id_expected)])]

    #     page = PageBuilder.build_cp(
    #         parent=parent, slug=title.replace(" ", "-"), title=title, bodies=bodies
    #     )
    #     response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
    #     content = response.json()

    #     doc_id = content["messages"][0]["document"]
    #     assert doc_id == page.whatsapp_body._raw_data[0]["value"]["document"]

    # def test_list_items(self, uclient):
    #     """
    #     test that list items are present in the whatsapp message
    #     """
    #     home_page = HomePage.objects.first()
    #     main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    #     target_page = PageBuilder.build_cp(
    #         parent=main_menu, slug="target-page", title="Target page", bodies=[]
    #     )
    #     form = Assessment.objects.create(
    #         title="Test form", slug="test-form", locale=target_page.locale
    #     )

    #     page = PageBuilder.build_cp(
    #         parent=main_menu,
    #         slug="page",
    #         title="Page",
    #         bodies=[
    #             WABody(
    #                 "list body",
    #                 [
    #                     WABlk(
    #                         "List message",
    #                         list_items=[
    #                             NextListItem("list item 1"),
    #                             PageListItem("list item 2", page=target_page),
    #                             FormListItem("list item 3", form=form),
    #                         ],
    #                     )
    #                 ],
    #             )
    #         ],
    #     )

    #     response = uclient.get(f"/api/v3/pages/{page.id}/?whatsapp=true")
    #     content = response.json()

    #     [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items"]
    #     item_1.pop("id")
    #     item_2.pop("id")
    #     item_3.pop("id")

    #     assert item_1 == {"type": "item", "value": "list item 1"}
    #     assert item_2 == {"type": "item", "value": "list item 2"}
    #     assert item_3 == {"type": "item", "value": "list item 3"}

    #     [item_1, item_2, item_3] = content["body"]["text"]["value"]["list_items_v3"]
    #     item_1.pop("id")
    #     item_2.pop("id")
    #     item_3.pop("id")

    #     assert item_1 == {"type": "next_message", "value": {"title": "list item 1"}}
    #     assert item_2 == {
    #         "type": "go_to_page",
    #         "value": {"title": "list item 2", "page": target_page.id},
    #     }
    #     assert item_3 == {
    #         "type": "go_to_form",
    #         "value": {"title": "list item 3", "form": form.id},
    #     }
