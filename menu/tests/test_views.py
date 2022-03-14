from django.test import TestCase, Client

from home.models import ContentPage, HomePage
from home.tests.utils import create_page


class MainMenuTestCase(TestCase):
    def test_main_menu(self):
        """
        Should return all pages with the mainmenu tag + their children
        """
        menu = create_page(title="Main Menu", tags=["mainmenu"])
        child1 = create_page(title="Sub menu 1", parent=menu)
        child2 = create_page(title="Sub menu 2", parent=menu)

        dummy = create_page(title="Dummy", tags=["dummy"])
        create_page(title="Dummy sub menu 1", parent=dummy)

        response = self.client.get("/mainmenu/?tags=mainmenu")

        result = response.json()

        menu = ["", "*Main Menu*", "*1* - Sub menu 1", "*2* - Sub menu 2"]
        ids = [str(child1.id), str(child2.id)]
        titles = [child1.title, child2.title]

        self.assertEqual(result["menu"], "\n".join(menu))
        self.assertEqual(result["ids"], ",".join(ids))
        self.assertEqual(result["titles"], ",".join(titles))
        self.assertEqual(result["count"], 2)

    def test_main_menu_mqr_bcm(self):
        """
        Should return all pages with the mainmenu tag + their children but only
        where they have a tag that starts with bcm
        """
        menu = create_page(title="Main Menu", tags=["mainmenu", "bcm_week_pre16"])
        child1 = create_page(title="Sub menu 1", parent=menu, tags=["bcm_week_pre16"])
        child2 = create_page(title="Sub menu 2", parent=menu, tags=["bcm_week_pre16"])
        create_page(title="Sub menu 3", parent=menu)

        dummy = create_page(title="Dummy", tags=["mainmenu"])
        create_page(title="Dummy sub menu 1", parent=dummy)

        response = self.client.get("/mainmenu/?tags=mainmenu&bcm=True")

        result = response.json()

        menu = ["", "*Main Menu*", "*1* - Sub menu 1", "*2* - Sub menu 2"]
        ids = [str(child1.id), str(child2.id)]
        titles = [child1.title, child2.title]

        self.assertEqual(result["menu"], "\n".join(menu))
        self.assertEqual(result["ids"], ",".join(ids))
        self.assertEqual(result["titles"], ",".join(titles))
        self.assertEqual(result["count"], 2)
