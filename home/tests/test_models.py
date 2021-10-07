from django.test import TestCase

from .utils import create_page, create_page_rating

class ContentPageTests(TestCase):
    def test_page_and_revision_rating(self):
        page = create_page()

        self.assertIsNone(page.page_rating)
        self.assertIsNone(page.latest_revision_rating)

        create_page_rating(page)
        create_page_rating(page, False)
        create_page_rating(page)

        self.assertEquals(page.page_rating, 66)
        self.assertEquals(page.latest_revision_rating, 66)

        page.save_revision()
        create_page_rating(page)
        self.assertEquals(page.latest_revision_rating, 100)
