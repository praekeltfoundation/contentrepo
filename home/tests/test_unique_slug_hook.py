from django.core.exceptions import ValidationError
from django.test import TestCase
from wagtail.models import Page

from home.models import ContentPage, HomePage


class UniqueSlugHookTest(TestCase):
    def test_duplicate_slug(self):
        """
        If the slug exists, append a number so that it's a new slug
        """
        home = HomePage.objects.first()
        home.add_child(instance=ContentPage(title="duplicate", slug="duplicate"))
        home.add_child(instance=ContentPage(title="duplicate", slug="duplicate-2"))
        slug = ContentPage().get_unique_slug("duplicate", Page)
        self.assertEqual(slug, "duplicate-3")

    def test_duplicate_slug_on_creation(self):
        """
        If there's no slug specified, a unique one should be generated
        """
        home = HomePage.objects.first()
        page1 = home.add_child(instance=ContentPage(title="duplicate"))
        page2 = home.add_child(instance=ContentPage(title="duplicate"))
        self.assertEqual(page1.slug, "duplicate")
        self.assertEqual(page2.slug, "duplicate-2")

    def test_duplicate_slug_error(self):
        """
        If a slug already exists, an error should be raised
        """
        home = HomePage.objects.first()
        home.add_child(instance=ContentPage(title="duplicate", slug="duplicate"))
        with self.assertRaises(ValidationError) as e:
            home.add_child(instance=ContentPage(title="duplicate", slug="duplicate"))
        self.assertIn("slug", e.exception.error_dict)
