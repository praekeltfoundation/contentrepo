from django.test import TestCase
from wagtail.models import Page

from home.wagtail_hooks import create_unique_slug


class UniqueSlugHookTest(TestCase):
    def test_duplicate_slug(self):
        """
        If the slug exists, append a number so that it's a new slug
        """
        home = Page.objects.first()
        home.add_child(instance=Page(title="duplicate", slug="duplicate"))
        home.add_child(instance=Page(title="duplicate", slug="duplicate-2"))
        slug = create_unique_slug("duplicate")
        self.assertEqual(slug, "duplicate-3")
