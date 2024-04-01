from urllib.parse import urlencode

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from home.models import ContentPageRating, HomePage
from home.serializers import ContentPageRatingSerializer, PageViewSerializer

from .page_builder import (
    PageBuilder,
    WABlk,
    WABody,
)


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
