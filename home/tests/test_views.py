from urllib.parse import urlencode

import pytest
from bs4 import BeautifulSoup
from pytest_django import asserts
from rest_framework import status
from rest_framework.test import APIClient
from wagtail.models import Locale

from home.models import ContentPageRating, HomePage
from home.serializers import ContentPageRatingSerializer, PageViewSerializer

from .page_builder import (
    PageBuilder,
    WABlk,
    WABody,
)

ALL_PLATFORMS_EXCL_WEB = ["Viber", "Messenger", "USSD", "SMS", "Whatsapp"]
ALL_PLATFORMS = ALL_PLATFORMS_EXCL_WEB + ["Web"]
OTHER_HEADINGS_IN_PROMOTIONAL = [
    "Tags",
    "Triggers",
    "Quick Replies",
    "Rating",
    "Related pages",
]

# TODO:
# - edit pages with content in them tests (tests for platform blocks)


@pytest.fixture()
def api_client(django_user_model):
    creds = {"username": "test", "password": "test"}
    user = django_user_model.objects.create_user(**creds)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.django_db
class TestPageRatings:
    def create_content_page(self):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = []

        bodies.append(WABody("default page", [WABlk("default body")]))

        content_page = PageBuilder.build_cp(
            parent=parent, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_homepage_redirect(self, api_client):
        """
        Check that we redirect to admin from the base url, as admin is the homepage of the CMS.
        """
        response = api_client.get("/")
        assert response.url == "/admin/"

    def test_page_rating_success(self, api_client):
        """
        Confirm that page ratings are created successfully when a comment is posted via the API
        """
        page = self.create_content_page()

        response = api_client.post(
            "/api/v2/custom/ratings/",
            {
                "page": page.id,
                "helpful": False,
                "comment": "lekker comment",
                "data": {"contact_uuid": "123"},
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        response_data = response.json()
        response_data.pop("timestamp")
        rating = ContentPageRating.objects.last()

        assert response.json() == {
            "id": rating.id,
            "helpful": False,
            "comment": "lekker comment",
            "data": {"contact_uuid": "123"},
            "page": page.id,
            "revision": page.get_latest_revision().id,
        }

    def test_page_rating_required_fields(self, api_client):
        """
        Ensure that the helpful, page and revision fields are required
        and rating is not created when these fields are missing
        """
        response = api_client.post("/api/v2/custom/ratings/", {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "helpful": ["This field is required."],
            "page": ["This field is required."],
            "revision": ["This field is required."],
        }

    def test_page_rating_invalid_page(self, api_client):
        """
        Ensure that a rating cannot be made for a page that does not exist
        """
        response = api_client.post(
            "/api/v2/custom/ratings/", {"page": 123}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "page": ["Page matching query does not exist."],
        }

    def test_get_list(self, api_client):
        """
        The list endpoint returns all ratings that match the query filter
        """
        page = self.create_content_page()

        rating_old = page.ratings.create(
            revision=page.get_latest_revision(), helpful=True
        )
        rating_new = page.ratings.create(
            revision=page.get_latest_revision(), helpful=False
        )
        page.ratings.create(revision=page.get_latest_revision(), helpful=True)

        response = api_client.get(
            f"/api/v2/custom/ratings/?{urlencode({'timestamp_gt': rating_old.timestamp.isoformat()})}"
        )

        assert (
            response.json()["results"][0]
            == ContentPageRatingSerializer(instance=rating_new).data
        )

        [r, _] = response.json()["results"]
        r.pop("timestamp")
        assert r == {
            "id": rating_new.id,
            "comment": "",
            "page": page.id,
            "revision": page.get_latest_revision().id,
            "helpful": False,
            "data": {},
        }


@pytest.mark.django_db
class TestPageViews:
    def create_content_page(self):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = []

        bodies.append(WABody("default page", [WABlk("default body")]))

        content_page = PageBuilder.build_cp(
            parent=parent, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_get_list(self, api_client):
        """
        The list endpoint returns all page views that match the query filter
        """
        page = self.create_content_page()
        pageview_old = page.views.create(revision=page.get_latest_revision())
        pageview_new = page.views.create(revision=page.get_latest_revision())
        page.views.create(revision=page.get_latest_revision())

        response = api_client.get(
            f"/api/v2/custom/pageviews/?{urlencode({'timestamp_gt': pageview_old.timestamp.isoformat()})}"
        )

        assert (
            response.json()["results"][0]
            == PageViewSerializer(instance=pageview_new).data
        )

        [r, _] = response.json()["results"]
        r.pop("timestamp")
        assert r == {
            "id": pageview_new.id,
            "page": page.id,
            "revision": page.get_latest_revision().id,
            "data": {},
            "platform": "web",
            "message": None,
        }


@pytest.mark.django_db
class TestEditPageView:
    def create_content_page(self):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = []

        bodies.append(WABody("default page", [WABlk("default body")]))

        content_page = PageBuilder.build_cp(
            parent=parent, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_response_success(self, admin_client):
        """
        Check that the edit page can be accessed on a page that exists
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        assert response.status_code == status.HTTP_200_OK

    def test_contains_options_for_submission(self, admin_client):
        """
        Check that the edit page has the option to Publish, Unpublish, Submit to Moderators approval or Save draft
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")

        drop_down = soup.find(
            "div", class_="dropdown dropup dropdown-button match-width"
        )

        buttons = [
            button.text.replace("\n", "") for button in drop_down.find_all("button")
        ]
        unpublish_button = [
            button.text.replace("\n", "") for button in drop_down.find_all("a")
        ]

        assert buttons == ["Save draft", "Publish", "Submit to Moderators approval"]
        assert unpublish_button == ["Unpublish"]

    def test_all_tabs_present(self, admin_client):
        """
        Check that the edit page has all tabs for platforms and other page options
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        sections = soup.find_all("section", class_="w-tabs__panel")

        tabs = [
            tab.find(
                "h2", class_="w-panel__heading w-panel__heading--label"
            ).text.replace("\n", "")
            for tab in sections
        ]

        assert tabs == [
            "Web",
            "Whatsapp",
            "SMS",
            "USSD",
            "Messenger",
            "Viber",
            "For search engines",
            "API settings",
        ]

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WEB)
    def test_platform_edit_forms_present(self, admin_client, platform):
        """
        Check that a blank page has the basic elements necessary for the platforms.
        This only accounts for the heading, title, and body, as well as blank text boxes where relavent.
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find(
            "section", class_="w-tabs__panel", id=f"tab-{platform.lower()}"
        )

        heading = (
            section.find("h2", class_="w-panel__heading w-panel__heading--label")
            .text.replace("/n", "")
            .strip()
        )
        title = (
            section.find("label", id=f"id_{platform.lower()}_title-label")
            .text.replace("/n", "")
            .strip()
        )
        body = (
            section.find("h3", class_="w-field__label").text.replace("/n", "").strip()
        )

        assert heading == platform
        assert title == f"{platform.capitalize()} title"
        assert body == f"{platform.capitalize()} body"

    def test_platform_edit_forms_present_web(self, admin_client):
        """
        The web platform has different elements from the other platforms,
        unfortunately this means that we need to run a separate test for the elements
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-web")

        heading = (
            section.find("h2", class_="w-panel__heading w-panel__heading--label")
            .text.replace("/n", "")
            .strip()
        )
        title = (
            section.find("label", id="id_title-label").text.replace("/n", "").strip()
        )
        subtitle = (
            section.find("label", id="id_subtitle-label").text.replace("/n", "").strip()
        )
        body = (
            section.find("h3", class_="w-field__label").text.replace("/n", "").strip()
        )

        assert heading == "Web"
        assert title == "Title*"
        assert subtitle == "Subtitle"
        assert body == "Body"

    def test_promotional_form_for_search_engines(self, admin_client):
        """
        Check that all expected elements, titles and text boxes,
        are present in the HTML form section for "for search engines"
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-promotional")

        # For search engines
        for_search_engines_section = section.find(
            "section", id="panel-child-promotional-for_search_engines-section"
        )
        for_search_engines_section_title = (
            for_search_engines_section.find(
                "h2", id="panel-child-promotional-for_search_engines-heading"
            )
            .text.replace("/n", "")
            .strip()
        )

        assert for_search_engines_section_title == "For search engines"

        slug = (
            for_search_engines_section.find("label", id="id_slug-label")
            .text.replace("/n", "")
            .strip()
        )
        slug_text_box = for_search_engines_section.find(
            "input", type="text", id="id_slug"
        )

        assert slug == "Slug*"
        assert slug_text_box

        title_tag = (
            for_search_engines_section.find("label", id="id_seo_title-label")
            .text.replace("/n", "")
            .strip()
        )
        title_tag_box = for_search_engines_section.find(
            "input", type="text", id="id_seo_title"
        )

        assert title_tag == "Title tag"
        assert title_tag_box

        meta_description = (
            for_search_engines_section.find("label", id="id_search_description-label")
            .text.replace("/n", "")
            .strip()
        )
        meta_description_box = for_search_engines_section.find(
            "textarea", id="id_search_description"
        )

        assert meta_description == "Meta description"
        assert meta_description_box

    def test_promotional_form_for_site_menus(self, admin_client):
        """
        Check that all expected elements, titles and text boxes,
        are present in the HTML form section for the "For site menu"
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-promotional")

        # For site menus
        for_site_menus_section = section.find(
            "section", id="panel-child-promotional-for_site_menus-section"
        )
        for_site_menus_section_title = (
            for_site_menus_section.find(
                "h2", id="panel-child-promotional-for_site_menus-heading"
            )
            .text.replace("/n", "")
            .strip()
        )
        assert for_site_menus_section_title == "For site menus"

        show_in_menus = (
            for_site_menus_section.find("label", id="id_show_in_menus-label")
            .text.replace("/n", "")
            .strip()
        )
        show_in_menus_check_box = for_site_menus_section.find(
            "input", id="id_show_in_menus"
        )
        assert show_in_menus == "Show in menus"
        assert show_in_menus_check_box

    @pytest.mark.parametrize("heading", OTHER_HEADINGS_IN_PROMOTIONAL)
    def test_promotional_form_other_headings(self, admin_client, heading):
        """
        Check that all titles are present in the promotional section of the HTML form
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-promotional")

        minor_section = section.find(
            "section",
            id=f"panel-child-promotional-{heading.lower().replace(' ','_')}-section",
        )
        minor_section_label = (
            minor_section.find(
                "h2",
                id=f"panel-child-promotional-{heading.lower().replace(' ','_')}-heading",
            )
            .text.replace("/n", "")
            .strip()
        )

        assert minor_section_label == heading

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_enable_platform_present(self, admin_client, platform):
        """
        Check that all enable checkboxes are present in the settings section of the HTML form
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-settings")

        enable_platform_lable = (
            section.find(
                "label", id=f"id_enable_{platform.lower().replace(' ','_')}-label"
            )
            .text.replace("/n", "")
            .strip()
        )
        enable_platform_checkbox = section.find(
            "input",
            type="checkbox",
            id=f"id_enable_{platform.lower().replace(' ','_')}",
        )

        assert enable_platform_lable == f"Enable {platform.lower()}"
        assert enable_platform_checkbox

    def test_page_cannot_be_edited(self, admin_client):
        """
        Check that the edit page cannot be accessed on a page that exists
        """
        response = admin_client.get("/admin/pages/10000/edit/")

        # TODO: a page ID that doesn't exist returns a 302, should this not return a 404?
        assert response.status_code != status.HTTP_200_OK


@pytest.mark.django_db
class TestUploadViews:
    # TODO: flesh out more tests for upload views
    def test_import_content_form_loads_correctly(self, admin_client):
        """
        Check that the import page can be accessed at the expected url
        """
        response = admin_client.get("/admin/import/")

        assert response.status_code == status.HTTP_200_OK
        asserts.assertContains(response, "Upload Content")

    def test_form_correct(self, admin_client):
        """
        Test that the upload form has all expected options
        """
        response = admin_client.get("/admin/import/")
        soup = BeautifulSoup(response.content, "html.parser")

        heading = soup.find("h1").text.replace("\n", "").strip()
        assert heading == "Upload Content"

        file_upload = soup.find("input", type="file", id="id_file")
        assert file_upload

        file_types = [
            file_type.text.replace("\n", "").strip()
            for file_type in soup.find("select", id="id_file_type").find_all("option")
        ]
        assert file_types == ["CSV file", "Excel File"]
        # TODO: consistency in the labeling, either both "file" or both "File"

        purge_options = [
            purge_option.text.replace("\n", "").strip()
            for purge_option in soup.find("select", id="id_purge").find_all("option")
        ]
        assert purge_options == ["No", "Yes"]

        locale_import = [
            locale_option.text.replace("\n", "").strip()
            for locale_option in soup.find("select", id="id_locale").find_all("option")
        ]

        all_locales = [locale.language_name for locale in Locale.objects.all()]
        assert locale_import == ["Import all languages"] + all_locales
