from io import StringIO

from django.core.management import call_command  # type: ignore
from django.test import TestCase  # type: ignore
from wagtail.models import Page  # type: ignore

from home.models import HomePage, OrderedContentSet

from .page_builder import (
    NextBtn,
    PageBtn,
    PageBuilder,
    WABlk,
    WABody,
)


class TestBrokenLinks(TestCase):
    def setUp(self) -> None:
        """
        Create a page with no related pages, the `related_page`
        """
        home_page = HomePage.objects.first()
        self.main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        self.ha_menu = PageBuilder.build_cpi(
            self.main_menu, "ha-menu", "HealthAlert menu"
        )
        self.health_info = PageBuilder.build_cp(
            parent=self.ha_menu,
            slug="health-info",
            title="health info",
            bodies=[WABody("health info", [WABlk("*Health information*")])],
        )

    def test_content_page_with_related_pages(self) -> None:
        """ """
        output = StringIO()

        self_help = PageBuilder.build_cp(
            parent=self.ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[WABody("self-help", [WABlk("*Self-help programs*")])],
        )
        index = PageBuilder.build_cpi(self.health_info, "iddex-page", "Index Page")

        self_help_rp = Page.objects.get(pk=self_help.id)
        index_rp = Page.objects.get(pk=index.id)
        PageBuilder.link_related(self.health_info, [self_help, index])

        call_command("broken_links_clean_up", stdout=output)
        assert len(self.health_info.related_pages) == 2
        assert len([rp.value for rp in self.health_info.related_pages]) == 2
        assert [rp.value for rp in self.health_info.related_pages] == [
            self_help_rp,
            index_rp,
        ]
        assert output.getvalue().strip() == "Successfully retrieve broken links"

    def test_content_page_with_deleted_related_page(self) -> None:
        """
        If related_page is deleted we still get two objects but one will be null the one that is deleted
        """
        output = StringIO()

        self_help = PageBuilder.build_cp(
            parent=self.ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[WABody("self-help", [WABlk("*Self-help programs*")])],
        )
        index = PageBuilder.build_cpi(self.health_info, "iddex-page", "Index Page")

        self_help_rp = Page.objects.get(pk=self_help.id)
        PageBuilder.link_related(self.health_info, [self_help, index])

        index.delete()
        related_pages = [rp.value for rp in self.health_info.related_pages]
        call_command("broken_links_clean_up", stdout=output)

        assert len(self.health_info.related_pages) == 2
        assert related_pages[1] is None
        assert related_pages == [self_help_rp, None]
        assert (
            output.getvalue().split("\n")[0].strip()
            == f"Content Page: {self.health_info.id} with non existing related page"
        )
        assert output.getvalue() == (
            f"Content Page: {self.health_info.id} with non existing related page \nSuccessfully retrieve broken links\n"
        )

    def test_content_page_with_a_go_to_button(self) -> None:
        """
        If page linked to button to go to page is deleted we still get two objects
        """
        output = StringIO()

        index = PageBuilder.build_cpi(self.health_info, "iddex-page", "Index Page")

        self_help = PageBuilder.build_cp(
            parent=self.ha_menu,
            slug="self-help",
            title="self-help",
            bodies=[
                WABody(
                    "self-help",
                    [
                        WABlk(
                            "*Self-help programs*",
                            buttons=[
                                NextBtn("Next message button"),
                                PageBtn("Import Export", page=index),
                            ],
                        )
                    ],
                )
            ],
        )

        orig_self_help_btn = self_help.whatsapp_body._raw_data[0]["value"].get(
            "buttons"
        )
        assert len(orig_self_help_btn) == 2

        index.delete()
        del_self_help_btn = self_help.whatsapp_body._raw_data[0]["value"].get("buttons")

        call_command("broken_links_clean_up", stdout=output)

        assert len(orig_self_help_btn) == 2
        assert (
            orig_self_help_btn[0]["value"]["title"]
            == del_self_help_btn[0]["value"]["title"]
        )
        assert (
            orig_self_help_btn[1]["value"]["page"]
            == del_self_help_btn[1]["value"]["page"]
        )
        assert (
            output.getvalue().strip()
            == f"Content Page: {self_help.id} with non existing button page: {index.id}\nSuccessfully retrieve broken links"
        )

    def test_ordered_content_sets(self) -> None:
        """
        Test ordered content sets
        """
        output = StringIO()

        ocs = OrderedContentSet(name="Test Title")
        ocs.save()
        ocs.save_revision().publish()

        call_command("broken_links_clean_up", stdout=output)

        assert output.getvalue().strip() == "Successfully retrieve broken links"

    def test_ordered_content_sets_with_deleted_page(self) -> None:
        """
        Test ordered content sets with deleted page linked to it
        """
        output = StringIO()

        index = PageBuilder.build_cpi(self.health_info, "iddex-page", "Index Page")
        test_page = PageBuilder.build_cp(
            parent=self.main_menu, slug="page1", title="Page1", bodies=[]
        )
        ocs = OrderedContentSet(name="Test Title")

        ocs.pages.append(("pages", {"contentpage": test_page}))
        ocs.pages.append(("pages", {"contentpage": index}))
        ocs.save()
        ocs.save_revision().publish()

        # Delete index page that is linked to ordered content page
        index.delete()

        call_command("broken_links_clean_up", stdout=output)

        assert (
            output.getvalue().strip()
            == f"Ordered Content: {ocs.id} with non existing page\nSuccessfully retrieve broken links"
        )
