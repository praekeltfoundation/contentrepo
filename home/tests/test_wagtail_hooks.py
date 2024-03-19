import pytest
from django.test import TestCase

from home.models import ContentPage, HomePage, OrderedContentSet
from home.wagtail_hooks import ContentPageAdmin

from .page_builder import PageBtn, PageBuilder, WABlk, WABody


# use this to access the admin interface
@pytest.fixture()
def admin_client(client, django_user_model):
    creds = {"username": "test", "password": "test"}
    django_user_model.objects.create_superuser(**creds)
    client.login(**creds)
    return client


class ContentPageAdminTests(TestCase):
    def test_body_text_truncation(self):
        """
        Body text for web, whatsapp, messenger, and viber, should be truncated in this
        list view
        """
        page = ContentPage(
            body=[("paragraph", "test " * 100)],
        )
        page.whatsapp_body.append(("Whatsapp_Message", {"message": "test " * 100}))
        page.messenger_body.append(("messenger_block", {"message": "test " * 100}))
        page.viber_body.append(("viber_message", {"message": "test " * 100}))
        admin = ContentPageAdmin()

        self.assertEqual(len(admin.web_body(page)), 200)
        self.assertEqual(len(admin.wa_body(page)), 200)
        self.assertEqual(len(admin.mess_body(page)), 200)
        self.assertEqual(len(admin.vib_body(page)), 200)
        # Web body is different to the rest because of the html
        self.assertEqual(admin.web_body(page)[-6:], "test …")
        self.assertEqual(admin.wa_body(page)[-5:], "test…")
        self.assertEqual(admin.mess_body(page)[-5:], "test…")
        self.assertEqual(admin.vib_body(page)[-5:], "test…")


@pytest.mark.django_db
class TestBeforeDeletePageHook:
    def create_content_page(self, title="default page", wa_buttons=None):
        """
        Helper function to create pages needed for each test.

        Parameters
        ----------
        title : str
            Title of the content page.
        wa_buttons: list[PageBtn]
            List of buttons to add to the WhatsApp block
        """
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        bodies = [WABody(title, [WABlk("Test Body", buttons=wa_buttons or [])])]

        content_page = PageBuilder.build_cp(
            parent=main_menu,
            slug=title.replace(" ", "-"),
            title=title,
            bodies=bodies,
            quick_replies=[],
            triggers=[],
        )
        return content_page

    def test_before_delete_page_no_links(self, admin_client):
        """
        If there are no links to the page being deleted there should be no warning
        messages.
        """
        page = self.create_content_page()
        url = f"/admin/pages/{page.id}/delete/"
        response = admin_client.get(url)
        messages = list(response.context["messages"])
        assert len(messages) == 0

    def test_before_delete_page_with_links(self, admin_client):
        """
        If there are links to the page being deleted there should be a warning message
        with urls to all links.
        """
        page = self.create_content_page()
        page_with_links = self.create_content_page(
            "Page2", wa_buttons=[PageBtn("Test", page=page)]
        )
        page_with_links = PageBuilder.link_related(page_with_links, [page])
        edit_url = f"/admin/pages/{page_with_links.id}/edit/"

        ocs = OrderedContentSet(name="Test set")
        ocs.pages.append(("pages", {"contentpage": page}))
        ocs.save()
        ocs.save_revision().publish()
        ocs_edit_url = f"/admin/snippets/home/orderedcontentset/edit/{ocs.id}/"

        url = f"/admin/pages/{page.id}/delete/"
        response = admin_client.get(url, follow=True)

        messages = list(response.context["messages"])

        msg = [
            "You can't delete this page while it is linked.",
            "",
            "Content Pages:",
            f'<a href="{edit_url}#tab-whatsapp">Page2 - WhatsApp: Go to button</a>',
            f'<a href="{edit_url}#tab-promotional">Page2 - Related Page</a>',
            "",
            "Ordered Content Sets:",
            f'<a href="{ocs_edit_url}">Test set</a>',
        ]

        assert len(messages) == 1
        assert str(messages[0]) == "<br>".join(msg)
