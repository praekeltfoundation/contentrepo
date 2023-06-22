from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from home.models import ContentPageRating
from home.serializers import ContentPageRatingSerializer, PageViewSerializer

from .utils import create_page


class PageRatingTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("contentpagerating-list")

    def test_homepage_redirect(self):
        response = self.client.get("/")
        self.assertEquals("/admin/", response.url)

    def test_page_rating_success(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        page = create_page()

        response = self.client.post(
            self.url,
            {
                "page": page.id,
                "helpful": False,
                "comment": "lekker comment",
                "data": {"contact_uuid": "123"},
            },
            format="json",
        )

        self.assertEquals(response.status_code, status.HTTP_201_CREATED)

        response_data = response.json()
        response_data.pop("timestamp")
        rating = ContentPageRating.objects.last()
        self.assertEquals(
            response.json(),
            {
                "id": rating.id,
                "helpful": False,
                "comment": "lekker comment",
                "data": {"contact_uuid": "123"},
                "page": page.id,
                "revision": page.get_latest_revision().id,
            },
        )

    def test_page_rating_required_fields(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.post(self.url, {}, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.json(),
            {
                "helpful": ["This field is required."],
                "page": ["This field is required."],
                "revision": ["This field is required."],
            },
        )

    def test_page_rating_invalid_page(self):
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        response = self.client.post(self.url, {"page": 123}, format="json")

        self.assertEquals(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEquals(
            response.json(),
            {
                "page": ["Page matching query does not exist."],
            },
        )

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        page = create_page()

        rating_old = page.ratings.create(
            **{"revision": page.get_latest_revision(), "helpful": True}
        )
        rating_new = page.ratings.create(
            **{"revision": page.get_latest_revision(), "helpful": False}
        )
        page.ratings.create(**{"revision": page.get_latest_revision(), "helpful": True})
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': rating_old.timestamp.isoformat()})}"
        )
        self.assertEqual(
            response.json()["results"][0],
            ContentPageRatingSerializer(instance=rating_new).data,
        )
        [r, _] = response.json()["results"]
        r.pop("timestamp")
        self.assertEqual(
            r,
            {
                "id": rating_new.id,
                "comment": "",
                "page": page.id,
                "revision": page.get_latest_revision().id,
                "helpful": False,
                "data": {},
            },
        )


class PageViewsTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("pageview-list")

    def test_get_list(self):
        """
        Should return the data, filtered by the querystring
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)

        page = create_page()

        pageview_old = page.views.create(
            **{
                "revision": page.get_latest_revision(),
            }
        )
        pageview_new = page.views.create(
            **{
                "revision": page.get_latest_revision(),
            }
        )
        page.views.create(
            **{
                "revision": page.get_latest_revision(),
            }
        )
        response = self.client.get(
            f"{self.url}?"
            f"{urlencode({'timestamp_gt': pageview_old.timestamp.isoformat()})}"
        )
        self.assertEqual(
            response.json()["results"][0],
            PageViewSerializer(instance=pageview_new).data,
        )
        [r, _] = response.json()["results"]
        r.pop("timestamp")
        self.assertEqual(
            r,
            {
                "id": pageview_new.id,
                "page": page.id,
                "revision": page.get_latest_revision().id,
                "data": {},
                "platform": "web",
                "message": None,
            },
        )
