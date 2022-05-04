from django.test import TestCase

from home.tests.utils import create_page


class MainMenuTestCase(TestCase):
    def test_main_menu(self):
        """
        Should return all pages with the mainmenu tag + their children
        """
        menu = create_page(title="Main Menu", tags=["mainmenu"])
        child1 = create_page(title="Sub menu 1", parent=menu)
        child2 = create_page(title="Sub menu 2", parent=menu)
        child3 = create_page(title="Sub menu 3", parent=menu)
        child3.unpublish()

        dummy = create_page(title="Dummy", tags=["dummy"])
        create_page(title="Dummy sub menu 1", parent=dummy)

        menu2 = create_page(title="Main Menu 2", tags=["mainmenu"])
        menu2.unpublish()

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


class SubMenuTestCase(TestCase):
    def test_submenu(self):
        """
        Should return all child pages of the parent id supplied
        """
        submenu = create_page(title="Sub Menu")
        child1 = create_page(title="Sub menu 1", parent=submenu)
        child2 = create_page(title="Sub menu 2", parent=submenu)
        child3 = create_page(title="Sub menu 3", parent=submenu)
        child3.unpublish()

        dummy = create_page(title="Dummy")
        create_page(title="Dummy sub menu 1", parent=dummy)

        response = self.client.get(f"/submenu/?parent={submenu.id}")

        result = response.json()

        menu = ["*1* - Sub menu 1", "*2* - Sub menu 2"]
        ids = [str(child1.id), str(child2.id)]
        titles = [child1.title, child2.title]

        self.assertEqual(result["menu"], "\n".join(menu))
        self.assertEqual(result["ids"], ",".join(ids))
        self.assertEqual(result["titles"], ",".join(titles))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["blurb"], "Test WhatsApp Message 1")

    def test_submenu_mqr_bcm(self):
        """
        Should return all child pages of the parent id supplied but only where
        they have a tag that starts with bcm
        """
        submenu = create_page(title="Sub Menu")
        child1 = create_page(
            title="Sub menu 1", parent=submenu, tags=["bcm_week_pre16"]
        )
        create_page(title="Sub menu 2", parent=submenu)
        child3 = create_page(
            title="Sub menu 3", parent=submenu, tags=["bcm_week_pre16"]
        )

        response = self.client.get(f"/submenu/?parent={submenu.id}&bcm=True")

        result = response.json()

        menu = ["*1* - Sub menu 1", "*2* - Sub menu 3"]
        ids = [str(child1.id), str(child3.id)]
        titles = [child1.title, child3.title]

        self.assertEqual(result["menu"], "\n".join(menu))
        self.assertEqual(result["ids"], ",".join(ids))
        self.assertEqual(result["titles"], ",".join(titles))
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["blurb"], "Test WhatsApp Message 1")
