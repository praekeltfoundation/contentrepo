from datetime import datetime, timedelta
import json
from unittest.mock import patch
from urllib.parse import urlencode

from django.urls import reverse
import pytest
from bs4 import BeautifulSoup
from pytest_django import asserts
from rest_framework import status
from rest_framework.test import APIClient
from wagtail.models import Locale

from home.models import ContentPageRating, HomePage, PageView
from home.serializers import ContentPageRatingSerializer, PageViewSerializer
from home.views import PageViewFilterSet, PageViewReportView

from .page_builder import (
    MBlk,
    MBody,
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

PLATFORMS_EXCL_WHATSAPP = ["Viber", "Messenger", "USSD", "SMS"]
ALL_PLATFORMS_EXCL_WEB = PLATFORMS_EXCL_WHATSAPP + ["Whatsapp"]
ALL_PLATFORMS = ALL_PLATFORMS_EXCL_WEB + ["Web"]


@pytest.fixture()
def api_client(django_user_model):
    creds = {"username": "test", "password": "test"}
    user = django_user_model.objects.create_user(**creds)
    client = APIClient()
    client.force_authenticate(user)
    return client


def find_options(soup, element_id):
    return [
        option.text.strip()
        for option in soup.find("select", id=f"id_{element_id}").find_all("option")
    ]


def test_homepage_redirect(api_client):
    """
    We redirect to admin from the base url, as admin is the homepage of the CMS.
    """
    response = api_client.get("/")
    assert response.url == "/admin/"


@pytest.mark.django_db
class TestPageRatings:
    def create_content_page(self):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        bodies = [WABody("default page", [WABlk("default body")])]

        content_page = PageBuilder.build_cp(
            parent=main_menu, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

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
        latest_rating = ContentPageRating.objects.last()

        assert response.json() == {
            "id": latest_rating.id,
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
        TODO: validation error states that revision is required, but we dont need revision as per the previous test
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

    def test_get_ratings_based_on_timestamp(self, api_client):
        """
        The list endpoint returns the second rating filtered out by the timestamp of the first rating
        Note: this is the only option for filtering ContentPageRatings, see ContentPageRatingFilter
        """
        page = self.create_content_page()
        rating_first = page.ratings.create(
            revision=page.get_latest_revision(), helpful=False, comment="first"
        )
        rating_second = page.ratings.create(
            revision=page.get_latest_revision(), helpful=False, comment="second"
        )

        # fetch all ratings newer than rating_first
        response = api_client.get(
            "/api/v2/custom/ratings/",
            {"timestamp_gt": rating_first.timestamp.isoformat()},
        )

        results = response.json()["results"]

        assert len(results) == 1

        assert ContentPageRatingSerializer(instance=rating_second).data in results
        assert ContentPageRatingSerializer(instance=rating_first).data not in results

        results[0].pop("timestamp")
        assert results[0] == {
            "id": rating_second.id,
            "comment": "second",
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
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        bodies = [WABody("default page", [WABlk("default body")])]

        content_page = PageBuilder.build_cp(
            parent=main_menu, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_get_views_based_on_timestamp(self, api_client):
        """
        The list endpoint returns the second page view that is created by filtering on the timestamp of the first
        Note: this is the only option for filtering ContentPageViews, see PageViewFilter
        """
        page = self.create_content_page()
        pageview_first = page.views.create(revision=page.get_latest_revision())
        pageview_second = page.views.create(revision=page.get_latest_revision())

        response = api_client.get(
            f"/api/v2/custom/pageviews/?{urlencode({'timestamp_gt': pageview_first.timestamp.isoformat()})}"
        )

        results = response.json()["results"]

        assert len(results) == 1

        assert PageViewSerializer(instance=pageview_second).data in results
        assert PageViewSerializer(instance=pageview_first).data not in results

        results[0].pop("timestamp")
        assert results[0] == {
            "id": pageview_second.id,
            "page": page.id,
            "revision": page.get_latest_revision().id,
            "data": {},
            "platform": "web",
            "message": None,
        }


@pytest.mark.django_db
class TestEditPageView:
    def create_content_page(self, body_type=None):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = home_page.get_children().filter(slug="main-menu").first()
        if not main_menu:
            main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        parent = main_menu

        bodies = []
        title = "Default title"
        msg_body = "Default body"
        var_body = "Default var body"

        if body_type == "Whatsapp":
            variation_messages = [VarMsg(var_body, gender="female")]
            bodies.append(
                WABody(
                    title,
                    [
                        WABlk(
                            msg_body,
                            variation_messages=variation_messages,
                        )
                    ],
                )
            )
        if body_type == "Messenger":
            bodies.append(MBody(title, [MBlk(msg_body)]))
        if body_type == "SMS":
            bodies.append(SBody(title, [SBlk(msg_body)]))
        if body_type == "USSD":
            bodies.append(UBody(title, [UBlk(msg_body)]))
        if body_type == "Viber":
            bodies.append(VBody(title, [VBlk(msg_body)]))

        content_page = PageBuilder.build_cp(
            parent=parent, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_can_edit_page_that_exists(self, admin_client):
        """
        The edit page can be accessed on a page that exists
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        assert response.status_code == status.HTTP_200_OK

    def test_page_cannot_be_edited(self, admin_client):
        """
        The edit page cannot be accessed on a page that does not exist
        """
        response = admin_client.get("/admin/pages/10000/edit/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_contains_options_for_submission(self, admin_client):
        """
        The edit page has the option to Publish, Unpublish, Submit to Moderators approval or Save draft
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")

        drop_down = soup.find(
            "div", class_="dropdown dropup dropdown-button match-width"
        )

        buttons = [button.text.strip() for button in drop_down.find_all("button")]
        unpublish_button = [button.text.strip() for button in drop_down.find_all("a")]

        assert buttons == ["Save draft", "Publish", "Submit to Moderators approval"]
        assert unpublish_button == ["Unpublish"]

    def test_all_tabs_present(self, admin_client):
        """
        The edit page has all tabs for platforms and other page options
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        sections = soup.find_all("a", class_="w-tabs__tab")

        tabs = [tab.text.replace("()", "").strip() for tab in sections]

        assert tabs == [
            "Web",
            "Whatsapp",
            "SMS",
            "USSD",
            "Messenger",
            "Viber",
            "Promotional",
            "Settings",
        ]

    @pytest.mark.parametrize("platform", ALL_PLATFORMS_EXCL_WEB)
    def test_platform_basic_edit_forms_present(self, admin_client, platform):
        """
        A blank page has the basic elements necessary for the platforms.
        This only accounts for the heading, title, and body, as well as blank text boxes where relevant.
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find(
            "section", class_="w-tabs__panel", id=f"tab-{platform.lower()}"
        )

        heading = section.find(
            "h2", class_="w-panel__heading w-panel__heading--label"
        ).text.strip()
        title = section.find(
            "label", id=f"id_{platform.lower()}_title-label"
        ).text.strip()
        body = section.find("h3", class_="w-field__label").text.strip()

        assert heading == platform
        assert title == f"{platform.capitalize()} title"
        assert body == f"{platform.capitalize()} body"

    def test_platform_basic_edit_forms_present_web(self, admin_client):
        """
        The web platform has different elements from the other platforms,
        unfortunately this means that we need to run a separate test for the elements
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-web")

        heading = section.find(
            "h2", class_="w-panel__heading w-panel__heading--label"
        ).text.strip()
        title = section.find("label", id="id_title-label").text.strip()
        subtitle = section.find("label", id="id_subtitle-label").text.strip()
        body = section.find("h3", class_="w-field__label").text.strip()

        assert heading == "Web"
        assert title == "Title*"
        assert subtitle == "Subtitle"
        assert body == "Body"

    def test_promotional_form_for_search_engines(self, admin_client):
        """
        All expected elements, titles and text boxes,
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
        for_search_engines_section_title = for_search_engines_section.find(
            "h2", id="panel-child-promotional-for_search_engines-heading"
        ).text.strip()

        assert for_search_engines_section_title == "For search engines"

        slug = for_search_engines_section.find("label", id="id_slug-label").text.strip()
        slug_text_box = for_search_engines_section.find(
            "input", type="text", id="id_slug"
        )

        assert slug == "Slug*"
        assert slug_text_box

        title_tag = for_search_engines_section.find(
            "label", id="id_seo_title-label"
        ).text.strip()
        title_tag_box = for_search_engines_section.find(
            "input", type="text", id="id_seo_title"
        )

        assert title_tag == "Title tag"
        assert title_tag_box

        meta_description = for_search_engines_section.find(
            "label", id="id_search_description-label"
        ).text.strip()
        meta_description_box = for_search_engines_section.find(
            "textarea", id="id_search_description"
        )

        assert meta_description == "Meta description"
        assert meta_description_box

    def test_promotional_form_for_site_menus(self, admin_client):
        """
        All expected elements, titles and text boxes,
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
        for_site_menus_section_title = for_site_menus_section.find(
            "h2", id="panel-child-promotional-for_site_menus-heading"
        ).text.strip()
        assert for_site_menus_section_title == "For site menus"

        show_in_menus = for_site_menus_section.find(
            "label", id="id_show_in_menus-label"
        ).text.strip()
        show_in_menus_check_box = for_site_menus_section.find(
            "input", id="id_show_in_menus"
        )
        assert show_in_menus == "Show in menus"
        assert show_in_menus_check_box

    @pytest.mark.parametrize(
        "heading",
        [
            "Tags",
            "Triggers",
            "Quick Replies",
            "Rating",
            "Related pages",
        ],
    )
    def test_promotional_form_other_headings(self, admin_client, heading):
        """
        All titles are present in the promotional section of the HTML form
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-promotional")

        minor_section = section.find(
            "section",
            id=f"panel-child-promotional-{heading.lower().replace(' ','_')}-section",
        )
        minor_section_label = minor_section.find(
            "h2",
            id=f"panel-child-promotional-{heading.lower().replace(' ','_')}-heading",
        ).text.strip()

        assert minor_section_label == heading

    @pytest.mark.parametrize("platform", ALL_PLATFORMS)
    def test_enable_platform_present(self, admin_client, platform):
        """
        All enable checkboxes are present in the settings section of the HTML form
        """
        page = self.create_content_page()
        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-settings")

        enable_platform_label = section.find(
            "label", id=f"id_enable_{platform.lower().replace(' ','_')}-label"
        ).text.strip()
        enable_platform_checkbox = section.find(
            "input",
            type="checkbox",
            id=f"id_enable_{platform.lower().replace(' ','_')}",
        )

        assert enable_platform_label == f"Enable {platform.lower()}"
        assert enable_platform_checkbox

    def test_whatsapp_block_with_variations(self, admin_client):
        page = self.create_content_page(body_type="Whatsapp")

        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find("section", class_="w-tabs__panel", id="tab-whatsapp")

        whatsapp_title = section.find("input", id="id_whatsapp_title")

        assert whatsapp_title.get("value") == "Default title"
        whatsapp_body = section.find("div", id="whatsapp_body")

        whatsapp_block = json.loads(whatsapp_body.get("data-value"))
        variations = whatsapp_block[0]["value"]["variation_messages"][0]["value"]

        assert len(whatsapp_block) == 1
        assert whatsapp_block[0]["value"]["message"] == "Default body"

        assert len(whatsapp_block[0]["value"]["variation_messages"]) == 1
        assert variations["message"] == "Default var body"
        assert variations["variation_restrictions"][0]["value"] == ["female"]

    @pytest.mark.parametrize("platform", PLATFORMS_EXCL_WHATSAPP)
    def test_platform_blocks_content(self, admin_client, platform):
        page = self.create_content_page(body_type=platform)

        response = admin_client.get(f"/admin/pages/{page.id}/edit/")

        soup = BeautifulSoup(response.content, "html.parser")
        section = soup.find(
            "section", class_="w-tabs__panel", id=f"tab-{platform.lower()}"
        )

        title = section.find("input", id=f"id_{platform.lower()}_title")
        assert title.get("value") == "Default title"

        platform_body = section.find("div", id=f"{platform.lower()}_body")

        platform_block = json.loads(platform_body.get("data-value"))
        assert len(platform_block) == 1
        assert platform_block[0]["value"]["message"] == "Default body"


class TestUploadViews:
    # TODO: flesh out more tests for upload views
    def test_import_content_form_loads(self, admin_client):
        """
        The import page can be accessed at the expected url
        """
        response = admin_client.get("/admin/import/")

        assert response.status_code == status.HTTP_200_OK
        asserts.assertContains(response, "Upload Content")

    def test_form_has_all_expected_options(self, admin_client):
        """
        The upload form has all expected options:
            - heading
            - file upload field
            - csv and Excel file as file type options in a drop down
            - Yes and No as purge options in a drop down
            - All current locale and each locale as an option for the languages
        """
        response = admin_client.get("/admin/import/")
        soup = BeautifulSoup(response.content, "html.parser")

        heading = soup.find("h1").text.strip()
        assert heading == "Upload Content"

        form = soup.find("form")
        file_upload = form.find("input", type="file", id="id_file")
        assert file_upload

        assert find_options(form, "file_type") == ["CSV file", "Excel File"]
        # TODO: consistency in the labeling, either both "file" or both "File"

        assert find_options(soup, "purge") == ["No", "Yes"]

        all_locales = [locale.language_name for locale in Locale.objects.all()]
        assert find_options(form, "locale") == ["Import all languages"] + all_locales


class TestOrderedContentSetViews:
    def test_response_success(self, admin_client):
        response = admin_client.get("/admin/snippets/home/orderedcontentset/")
        assert response.status_code == status.HTTP_200_OK

    def test_buttons_present_in_view(self, admin_client):
        """
        The buttons are present in the view of the ordered content set.
        """
        response = admin_client.get("/admin/snippets/home/orderedcontentset/")
        soup = BeautifulSoup(response.content, "html.parser")

        add_ordred_content_set = soup.find(
            "a", href="/admin/snippets/home/orderedcontentset/add/"
        )
        assert add_ordred_content_set
        assert (
            add_ordred_content_set.text.replace("\n", "") == "Add Ordered Content Set"
        )

        download_xls = soup.find(
            "a", href="/admin/snippets/home/orderedcontentset/?export=xlsx"
        )
        assert download_xls
        assert download_xls.text.replace("\n", "") == "Download XLSX"

        download_csv = soup.find(
            "a", href="/admin/snippets/home/orderedcontentset/?export=csv"
        )
        assert download_csv
        assert download_csv.text.replace("\n", "") == "Download CSV"

        import_button = soup.find("a", href="/admin/import_orderedcontentset/")
        assert import_button
        assert import_button.text.replace("\n", "") == "Import"

    def test_add_form_content_loads(self, admin_client):
        """
        The buttons are present in the view of the ordered content set.
        """
        response = admin_client.get("/admin/snippets/home/orderedcontentset/add/")
        soup = BeautifulSoup(response.content, "html.parser")

        assert soup.find("h1").text.strip() == "New Ordered Content Set"

        form = soup.find("form")
        assert [heading.text.strip() for heading in form.find_all("h2")] == [
            "Name*",
            "Profile fields",
            "Pages",
        ]

        name_field = form.find("input", type="text")
        assert name_field

    def test_ordered_content_categories(self, admin_client):
        """
        Profile fields and pages should have the correct options available
        """
        response = admin_client.get("/admin/snippets/home/orderedcontentset/add/")
        soup = BeautifulSoup(response.content, "html.parser")
        profile_fields = str(soup.find("div", {"id": "panel-profile_fields-content"}))

        assert "Gender" in profile_fields
        assert "Age" in profile_fields
        assert "Relationship" in profile_fields

        page_fields = str(soup.find("div", {"id": "panel-pages-content"}))

        assert "Time" in page_fields
        assert "Unit" in page_fields
        assert "Contact field" in page_fields


class TestOrderedContentImportView:
    def test_import_ordered_content(self, admin_client):
        """
        The import page can be accessed at the expected url
        """
        response = admin_client.get("/admin/import_orderedcontentset/")

        assert response.status_code == status.HTTP_200_OK
        asserts.assertContains(response, "Upload Ordered Content Sets")

    def test_ordered_form_has_all_expected_options(self, admin_client):
        """
        The upload form has all expected options:
            - heading
            - file upload field
            - csv and Excel file as file type options in a drop down
            - Yes and No as purge options in a drop down
            - All current locale and each locale as an option for the languages
        """
        response = admin_client.get("/admin/import_orderedcontentset/")
        soup = BeautifulSoup(response.content, "html.parser")

        heading = soup.find("h1").text.strip()
        assert heading == "Upload Ordered Content Sets"

        form = soup.find("form")
        file_upload = form.find("input", type="file", id="id_file")
        assert file_upload

        assert find_options(form, "file_type") == ["CSV file", "Excel File"]

        assert find_options(soup, "purge") == ["No", "Yes"]

@pytest.mark.django_db
class TestPageViewReportView:
    def create_content_page(self):
        """
        Helper function to create pages needed for each test.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")

        bodies = [WABody("default page", [WABlk("default body")])]

        content_page = PageBuilder.build_cp(
            parent=main_menu, slug="default-page", title="default page", bodies=bodies
        )
        return content_page

    def test_get_queryset(self):
        """
        Check if get_queryset returns all PageView objects
        """
        content_page = self.create_content_page()
  
        content_page.views.create(revision=content_page.get_latest_revision())
        content_page.views.create(revision=content_page.get_latest_revision())

        view = PageViewReportView()
        queryset = view.get_queryset()

        assert queryset.count() == PageView.objects.count()


    def test_get_context_data(self):
        content_page = self.create_content_page()
  
        content_page.views.create(revision=content_page.get_latest_revision())
        content_page.views.create(revision=content_page.get_latest_revision())
    
        view = PageViewReportView()

        with patch.object(view, 'get_queryset') as mock_get_queryset:
            mock_get_queryset.return_value = PageView.objects.all()
            view.object_list = list(mock_get_queryset.return_value)

            with patch.object(view, 'get_views_data') as mock_get_views_data:
                mock_get_views_data.return_value = {"data": [], "labels": []}
                context = view.get_context_data()

                self.assertIn("object_list", context)
                self.assertIn("page_view_data", context)

    def test_template_rendering(self,admin_client):
        """
        Check if the correct template is used and context data is rendered properly
        """
        url = reverse('page_view_report')
        response = admin_client.get(url)
        asserts.assertTemplateUsed(response, 'reports/page_view_report.html')
        asserts.assertContains(response, 'Page views')



    # def test_timestamp_filter(self):
    #     date = datetime.now()
    #     date2 = date - timedelta(days=90)

    #     content_page = self.create_content_page()

    #     PageView.objects.create(timestamp=date, page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")
    #     PageView.objects.create(timestamp=date2, page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")
    #     PageView.objects.create(timestamp=date2, page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="sms")


    #     year = date.year
    #     month = date.month

    #     date_from = datetime(year, month, 1)
    #     date_to = datetime(year, month, 30)
    #     filter_data = {'timestamp': [date_from, date_to]}
    #     filter_set = PageViewFilterSet(filter_data, queryset=PageView.objects.all())
    #     filtered_queryset = filter_set.qs
        
    #     assert filtered_queryset.count() == 2

    def test_platform_filter(self):
        content_page = self.create_content_page()

        PageView.objects.create(timestamp="2023-01-01", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="web")
        PageView.objects.create(timestamp="2024-01-01", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")
        PageView.objects.create(timestamp="2024-01-15", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")

        filterset = {'platform': 'web'}
        filter_set = PageViewFilterSet(filterset, queryset=PageView.objects.all())
        filtered_queryset = filter_set.qs

        assert filtered_queryset.count() == 1

    def test_page_filter(self):
        content_page = self.create_content_page()

        PageView.objects.create(timestamp="2023-01-01", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="web")
        PageView.objects.create(timestamp="2024-01-01", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")
        PageView.objects.create(timestamp="2024-01-15", page_id=content_page.id, revision_id=content_page.get_latest_revision().id, platform="whatsapp")

        filterset_data = {'page': content_page.id}
        filter_set = PageViewFilterSet(filterset_data, queryset=PageView.objects.all())
        filtered_queryset = filter_set.qs

        assert filtered_queryset.count() == 3
