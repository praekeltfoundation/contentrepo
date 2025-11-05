from collections.abc import Iterable
from typing import Any
from uuid import UUID

import pytest
from wagtail.models import Locale, Page  # type: ignore

from home.models import ContentPage, ContentPageIndex, HomePage, WhatsAppTemplate
from home.tests.utils import unwagtail

from .helpers import set_profile_field_options
from .page_builder import (
    MBlk,
    MBody,
    NextBtn,
    PageBtn,
    PageBuilder,
    VarMsg,
    VBlk,
    VBody,
    WABlk,
    WABody,
    WATpl,
)


def tagslugs(taglikes: Iterable[dict[str, str]]) -> list[str]:
    """
    Extract slug fields from tag-like dicts.
    """
    return sorted(t["slug"] for t in taglikes)


def page_for(page: Page) -> Page:
    """
    Fetch a Page instance for whatever kind of page we get.
    """
    return Page.objects.get(pk=page.pk)


@pytest.mark.django_db
def test_build_simple_pages() -> None:
    """
    PageBuilder.build_cpi followed by PageBuilder.build_cp correctly builds and
    publishes a ContentPageIndex with a child ContentPage.
    """
    home_page = HomePage.objects.first()

    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    ha_menu = PageBuilder.build_cp(
        parent=main_menu,
        slug="ha-menu",
        title="HealthAlert menu",
        bodies=[
            WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
            MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
            VBody("HealthAlert menu", [VBlk("Welcome to HealthAlert V")]),
        ],
    )

    assert isinstance(main_menu, ContentPageIndex)
    assert main_menu.depth == 3
    assert main_menu.draft_title == "Main Menu"
    assert main_menu.has_unpublished_changes is False
    assert main_menu.include_in_homepage is False
    assert main_menu.live is True
    assert main_menu.live_revision == main_menu.latest_revision
    assert main_menu.locale == Locale.objects.get(language_code="en")
    assert main_menu.numchild == 1
    assert main_menu.slug == "main-menu"
    assert main_menu.title == "Main Menu"
    assert isinstance(main_menu.translation_key, UUID)
    assert main_menu.url_path == "/home/main-menu/"

    assert isinstance(ha_menu, ContentPage)
    assert unwagtail(ha_menu.body) == []
    assert ha_menu.depth == 4
    assert ha_menu.draft_title == "HealthAlert menu"
    assert ha_menu.enable_messenger is True
    assert ha_menu.enable_viber is True
    assert ha_menu.enable_web is False
    assert ha_menu.enable_whatsapp is True
    assert ha_menu.has_unpublished_changes is False
    assert ha_menu.include_in_footer is False
    assert ha_menu.has_whatsapp_template is False
    assert ha_menu.live is True
    assert ha_menu.live_revision == ha_menu.latest_revision
    assert ha_menu.locale == Locale.objects.get(language_code="en")
    assert unwagtail(ha_menu.messenger_body) == [
        ("messenger_block", {"image": None, "message": "Welcome to HealthAlert M"}),
    ]
    assert ha_menu.messenger_title == "HealthAlert menu"
    assert ha_menu.numchild == 0
    assert unwagtail(ha_menu.related_pages) == []
    assert ha_menu.search_description == ""
    assert ha_menu.seo_title == ""
    assert ha_menu.show_in_menus is False
    assert ha_menu.slug == "ha-menu"
    assert ha_menu.subtitle == ""
    assert list(ha_menu.tags.values()) == []
    assert ha_menu.title == "HealthAlert menu"
    assert isinstance(ha_menu.translation_key, UUID)
    assert ha_menu.url_path == "/home/main-menu/ha-menu/"
    assert unwagtail(ha_menu.viber_body) == [
        ("viber_message", {"image": None, "message": "Welcome to HealthAlert V"}),
    ]
    assert ha_menu.viber_title == "HealthAlert menu"
    assert unwagtail(ha_menu.whatsapp_body) == [
        (
            "Whatsapp_Message",
            {
                "document": None,
                "image": None,
                "list_title": "",
                "list_items": [],
                "media": None,
                "message": "*Welcome to HealthAlert* WA",
                "buttons": [],
                "variation_messages": [],
                "footer": "",
            },
        ),
    ]
    assert ha_menu.whatsapp_title == "HealthAlert menu"

    assert main_menu.translation_key != ha_menu.translation_key


@pytest.mark.django_db
def test_build_web_content() -> None:
    """
    PageBuilder.build_cp correctly builds a ContentPageIndex with a web
    content.
    """
    home_page = HomePage.objects.first()

    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    ha_menu = PageBuilder.build_cp(
        parent=main_menu,
        slug="ha-menu",
        title="HealthAlert menu",
        bodies=[],
        web_body=["Paragraph 1.", "Paragraph 2."],
    )

    assert isinstance(main_menu, ContentPageIndex)
    assert main_menu.depth == 3
    assert main_menu.numchild == 1
    assert main_menu.slug == "main-menu"

    assert isinstance(ha_menu, ContentPage)
    assert unwagtail(ha_menu.body) == [
        ("paragraph", "Paragraph 1."),
        ("paragraph", "Paragraph 2."),
    ]
    assert ha_menu.depth == 4
    assert ha_menu.draft_title == "HealthAlert menu"
    assert ha_menu.enable_messenger is False
    assert ha_menu.enable_viber is False
    assert ha_menu.enable_web is True
    assert ha_menu.enable_whatsapp is False
    assert ha_menu.has_unpublished_changes is False
    assert ha_menu.include_in_footer is False
    assert ha_menu.live is True
    assert ha_menu.live_revision == ha_menu.latest_revision
    assert ha_menu.locale == Locale.objects.get(language_code="en")
    assert unwagtail(ha_menu.messenger_body) == []
    assert ha_menu.messenger_title == ""
    assert ha_menu.numchild == 0
    assert unwagtail(ha_menu.related_pages) == []
    assert ha_menu.search_description == ""
    assert ha_menu.seo_title == ""
    assert ha_menu.show_in_menus is False
    assert ha_menu.slug == "ha-menu"
    assert ha_menu.subtitle == ""
    assert list(ha_menu.tags.values()) == []
    assert ha_menu.title == "HealthAlert menu"
    assert isinstance(ha_menu.translation_key, UUID)
    assert ha_menu.url_path == "/home/main-menu/ha-menu/"
    assert unwagtail(ha_menu.viber_body) == []
    assert ha_menu.viber_title == ""
    assert unwagtail(ha_menu.whatsapp_body) == []
    assert ha_menu.whatsapp_title == ""


@pytest.mark.django_db
def test_build_variations() -> None:
    """
    PageBuilder.build_cp correctly builds a ContentPage with variation
    messages. (This also tests multiple WhatsApp messages and buttons
    """
    set_profile_field_options()
    home_page = HomePage.objects.first()
    imp_exp = PageBuilder.build_cpi(home_page, "import-export", "Import Export")

    cp_imp_exp_wablks = [
        WABlk(
            "Message 1",
            buttons=[NextBtn("Next message")],
            variation_messages=[
                VarMsg("Single male", gender="male", relationship="single"),
                VarMsg("Comp male", gender="male", relationship="complicated"),
            ],
        ),
        WABlk(
            "Message 2, variable placeholders as well {{0}}",
            buttons=[PageBtn("Import Export", page=imp_exp)],
            variation_messages=[VarMsg("Teen", age="15-18")],
        ),
        WABlk(
            "Message 3 with no variation",
            buttons=[NextBtn("end")],
        ),
    ]
    cp_imp_exp = PageBuilder.build_cp(
        parent=imp_exp,
        slug="cp-import-export",
        title="CP-Import/export",
        bodies=[WABody("WA import export data", cp_imp_exp_wablks)],
    )

    v_single_male = [("gender", "male"), ("relationship", "single")]
    v_complicated_male = [("gender", "male"), ("relationship", "complicated")]
    wa_msgs: list[dict[str, Any]] = [
        {
            "message": "Message 1",
            "buttons": [("next_message", {"title": "Next message"})],
            "variation_messages": [
                {"message": "Single male", "variation_restrictions": v_single_male},
                {"message": "Comp male", "variation_restrictions": v_complicated_male},
            ],
            "footer": "",
        },
        {
            "message": "Message 2, variable placeholders as well {{0}}",
            "buttons": [
                ("go_to_page", {"title": "Import Export", "page": page_for(imp_exp)}),
            ],
            "variation_messages": [
                {"message": "Teen", "variation_restrictions": [("age", "15-18")]}
            ],
            "footer": "",
        },
        {
            "message": "Message 3 with no variation",
            "buttons": [("next_message", {"title": "end"})],
            "variation_messages": [],
            "footer": "",
        },
    ]

    assert isinstance(cp_imp_exp, ContentPage)
    assert unwagtail(cp_imp_exp.body) == []
    assert cp_imp_exp.depth == 4
    assert cp_imp_exp.draft_title == "CP-Import/export"
    assert cp_imp_exp.enable_messenger is False
    assert cp_imp_exp.enable_viber is False
    assert cp_imp_exp.enable_web is False
    assert cp_imp_exp.enable_whatsapp is True
    assert cp_imp_exp.has_unpublished_changes is False
    assert cp_imp_exp.include_in_footer is False
    assert cp_imp_exp.has_whatsapp_template is False
    assert cp_imp_exp.live is True
    assert cp_imp_exp.live_revision == cp_imp_exp.latest_revision
    assert cp_imp_exp.locale == Locale.objects.get(language_code="en")
    assert unwagtail(cp_imp_exp.messenger_body) == []
    assert cp_imp_exp.messenger_title == ""
    assert cp_imp_exp.numchild == 0
    assert unwagtail(cp_imp_exp.related_pages) == []
    assert cp_imp_exp.search_description == ""
    assert cp_imp_exp.seo_title == ""
    assert cp_imp_exp.show_in_menus is False
    assert cp_imp_exp.slug == "cp-import-export"
    assert cp_imp_exp.subtitle == ""
    assert cp_imp_exp.title == "CP-Import/export"
    assert isinstance(cp_imp_exp.translation_key, UUID)
    assert cp_imp_exp.url_path == "/home/import-export/cp-import-export/"
    assert unwagtail(cp_imp_exp.viber_body) == []
    assert cp_imp_exp.viber_title == ""
    assert unwagtail(cp_imp_exp.whatsapp_body) == [
        (
            "Whatsapp_Message",
            {
                "document": None,
                "image": None,
                "list_title": "",
                "list_items": [],
                "media": None,
            }
            | msg,
        )
        for msg in wa_msgs
    ]
    assert cp_imp_exp.whatsapp_title == "WA import export data"


@pytest.mark.django_db
def test_link_related_pages() -> None:
    """
    After building some ContentPages, PageBuilder.link_related correctly adds
    related_pages entries. (This also tests tags.)
    """
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    ha_menu = PageBuilder.build_cp(
        parent=main_menu,
        slug="ha-menu",
        title="HealthAlert menu",
        bodies=[
            WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
            MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
        ],
        tags=["tag1", "tag2"],
    )
    health_info = PageBuilder.build_cp(
        parent=ha_menu,
        slug="health-info",
        title="health info",
        bodies=[MBody("health info", [MBlk("*Health information* M")])],
        tags=["tag2", "tag3"],
    )
    self_help = PageBuilder.build_cp(
        parent=ha_menu,
        slug="self-help",
        title="self-help",
        bodies=[WABody("self-help", [WABlk("*Self-help programs* WA")])],
        tags=["tag4"],
    )

    assert isinstance(ha_menu, ContentPage)
    assert ha_menu.depth == 4
    assert tagslugs(ha_menu.tags.values()) == ["tag1", "tag2"]

    assert isinstance(health_info, ContentPage)
    assert health_info.depth == 5
    assert tagslugs(health_info.tags.values()) == ["tag2", "tag3"]

    assert isinstance(self_help, ContentPage)
    assert self_help.depth == 5
    assert tagslugs(self_help.tags.values()) == ["tag4"]

    assert unwagtail(ha_menu.related_pages) == []
    assert unwagtail(health_info.related_pages) == []
    assert unwagtail(self_help.related_pages) == []

    PageBuilder.link_related(health_info, [self_help])
    PageBuilder.link_related(self_help, [health_info, ha_menu])

    ha_menu.refresh_from_db()
    health_info.refresh_from_db()
    self_help.refresh_from_db()

    assert unwagtail(ha_menu.related_pages) == []
    assert unwagtail(health_info.related_pages) == [
        ("related_page", page_for(self_help))
    ]
    assert unwagtail(self_help.related_pages) == [
        ("related_page", page_for(health_info)),
        ("related_page", page_for(ha_menu)),
    ]


@pytest.mark.django_db
def test_triggers_and_quick_replies() -> None:
    """
    PageBuilder.build_cp correctly builds a ContentPage with triggers and quick
    replies.
    """
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    ha_menu = PageBuilder.build_cp(
        parent=main_menu,
        slug="ha-menu",
        title="HealthAlert menu",
        bodies=[
            WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")]),
            MBody("HealthAlert menu", [MBlk("Welcome to HealthAlert M")]),
        ],
        triggers=["trigger1", "trigger2"],
    )
    health_info = PageBuilder.build_cp(
        parent=ha_menu,
        slug="health-info",
        title="health info",
        bodies=[MBody("health info", [MBlk("*Health information* M")])],
        triggers=["trigger2", "trigger3"],
        quick_replies=["button1", "button2"],
    )
    self_help = PageBuilder.build_cp(
        parent=ha_menu,
        slug="self-help",
        title="self-help",
        bodies=[WABody("self-help", [WABlk("*Self-help programs* WA")])],
        quick_replies=["button3", "button2"],
    )

    assert isinstance(ha_menu, ContentPage)
    assert ha_menu.depth == 4
    assert tagslugs(ha_menu.triggers.values()) == ["trigger1", "trigger2"]
    assert tagslugs(ha_menu.quick_replies.values()) == []

    assert isinstance(health_info, ContentPage)
    assert health_info.depth == 5
    assert tagslugs(health_info.triggers.values()) == ["trigger2", "trigger3"]
    assert tagslugs(health_info.quick_replies.values()) == ["button1", "button2"]

    assert isinstance(self_help, ContentPage)
    assert self_help.depth == 5
    assert tagslugs(self_help.triggers.values()) == []
    assert tagslugs(self_help.quick_replies.values()) == ["button2", "button3"]


@pytest.mark.django_db
def test_whatsapp_template() -> None:
    """
    PageBuilder.build_cp correctly builds a ContentPage that is a Whatsapp
    template.
    """
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    ha_menu = PageBuilder.build_cp(
        parent=main_menu,
        slug="ha-menu",
        title="HealthAlert menu",
        bodies=[WABody("HealthAlert menu", [WABlk("*Welcome to HealthAlert* WA")])],
    )

    template = WhatsAppTemplate.objects.create(
        category="MARKETING",
        slug="template-health-info",
        message="Test WhatsApp Template Message 1",
        locale=Locale.objects.first(),
    )
    template = WATpl(
        template=template,
        message="Test WhatsApp Template Message 1",
    )
    health_info = PageBuilder.build_cp(
        parent=ha_menu,
        slug="health-info",
        title="health info",
        bodies=[WABody("health info", [template])],
    )

    assert isinstance(ha_menu, ContentPage)
    assert ha_menu.depth == 4
    assert ha_menu.has_whatsapp_template is False

    assert isinstance(health_info, ContentPage)
    assert health_info.depth == 5
    assert health_info.has_whatsapp_template is True
    template_id = health_info.whatsapp_body.raw_data[0]["value"]
    template = WhatsAppTemplate.objects.get(id=template_id)
    assert template.slug == "template-health-info"
    assert template.category == "MARKETING"


@pytest.mark.django_db
def test_translated_pages() -> None:
    """
    PageBuilder.build_cpi and PageBuilder.build_cp correctly build translated
    pages.
    """
    # Create a new homepage for Portuguese.
    pt, _created = Locale.objects.get_or_create(language_code="pt")
    HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

    # English pages
    home_en = HomePage.objects.get(locale__language_code="en")
    imp_exp = PageBuilder.build_cpi(
        parent=home_en, slug="import-export", title="Import Export"
    )
    non_templ_wablks = [
        WABlk("this is a non template message"),
        WABlk("this message has a doc"),
        WABlk("this message comes with audio"),
    ]
    non_tmpl = PageBuilder.build_cp(
        parent=imp_exp,
        slug="non-template",
        title="Non template messages",
        bodies=[WABody("non template OCS", non_templ_wablks)],
    )

    # Portuguese pages
    home_pt = HomePage.objects.get(locale__language_code="pt")
    imp_exp_pt = PageBuilder.build_cpi(
        parent=home_pt,
        slug="import-export-pt",
        title="Import Export (pt)",
        translated_from=imp_exp,
    )
    non_templ_wablks_pt = [
        WABlk("this is a non template message (pt)"),
        WABlk("this message has a doc (pt)"),
        WABlk("this message comes with audio (pt)"),
    ]
    non_tmpl_pt = PageBuilder.build_cp(
        parent=imp_exp_pt,
        slug="non-template-pt",
        title="Non template messages",
        bodies=[WABody("non template OCS", non_templ_wablks_pt)],
        translated_from=non_tmpl,
    )

    assert isinstance(imp_exp, ContentPageIndex)
    assert imp_exp.depth == 3
    assert imp_exp.locale == Locale.objects.get(language_code="en")
    assert isinstance(imp_exp.translation_key, UUID)

    assert isinstance(non_tmpl, ContentPage)
    assert non_tmpl.depth == 4
    assert non_tmpl.locale == Locale.objects.get(language_code="en")
    assert isinstance(non_tmpl.translation_key, UUID)

    assert isinstance(imp_exp_pt, ContentPageIndex)
    assert imp_exp_pt.depth == 2  # FIXME: Should this be 3?
    assert imp_exp_pt.locale == Locale.objects.get(language_code="pt")
    assert isinstance(imp_exp_pt.translation_key, UUID)

    assert isinstance(non_tmpl_pt, ContentPage)
    assert non_tmpl_pt.depth == 3  # FIXME: Should this be 4?
    assert non_tmpl_pt.locale == Locale.objects.get(language_code="pt")
    assert isinstance(non_tmpl_pt.translation_key, UUID)

    assert imp_exp.translation_key != non_tmpl.translation_key
    assert imp_exp.translation_key == imp_exp_pt.translation_key
    assert non_tmpl.translation_key == non_tmpl_pt.translation_key
