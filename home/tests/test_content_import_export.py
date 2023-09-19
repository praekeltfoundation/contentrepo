import csv
import json
import queue
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core import serializers
from django.test import TestCase
from wagtail.models import Locale, Page
from wagtail.models.sites import Site

from home.content_import_export import import_content
from home.models import ContentPage, ContentPageIndex, HomePage, SiteSettings

from .page_builder import MBlk, MBody, PageBuilder, WABlk, WABody


def filter_both(filter_func):
    @wraps(filter_func)
    def ff(src, dst):
        return filter_func(src), filter_func(dst)

    return ff


@filter_both
def add_new_fields(entry):
    # FIXME: This should probably be in a separate test for importing old exports.
    return {"whatsapp_template_name": "", **entry}


def remove_translation_tag_from_tags(src, dst):
    # FIXME: Do we actually need translation_tag to be added to tags?
    if not src["translation_tag"]:
        return src, dst
    dtags = [tag for tag in dst["tags"].split(", ") if tag != src["translation_tag"]]
    return src, {**dst, "tags": ", ".join(dtags)}


@filter_both
def ignore_certain_fields(entry):
    # FIXME: Do we need page.id to be imported? At the moment nothing in the
    #        import reads that.
    # FIXME: We should probably set contentpage.translation_key on import
    #        instead of messing about with tags.
    # FIXME: Implement import/export for doc_link, image_link, media_link.
    # FIXME: Implement import/export for next_prompt.
    ignored_fields = {
        "page_id",
        "translation_tag",
        "doc_link",
        "image_link",
        "media_link",
        "next_prompt",
    }
    return {k: v for k, v in entry.items() if k not in ignored_fields}


@filter_both
def strip_leading_whitespace(entry):
    # FIXME: Do we expect imported content to have leading spaces removed?
    bodies = {k: v.lstrip(" ") for k, v in entry.items() if k.endswith("_body")}
    return {**entry, **bodies}


FILTER_FUNCS = [
    add_new_fields,
    remove_translation_tag_from_tags,
    ignore_certain_fields,
    strip_leading_whitespace,
]


def filter_exports(src_entries, dst_entries):
    for src, dst in zip(src_entries, dst_entries, strict=True):
        for ff in FILTER_FUNCS:
            src, dst = ff(src, dst)
        yield src, dst


def csv2dicts(csv_bytes):
    return list(csv.DictReader(StringIO(csv_bytes.decode())))


def csvs2dicts(src_bytes, dst_bytes):
    return zip(*filter_exports(csv2dicts(src_bytes), csv2dicts(dst_bytes)), strict=True)


def _models2dicts(model_instances):
    return json.loads(serializers.serialize("json", model_instances))


def _get_page_json():
    page_objs = Page.objects.type(ContentPage, ContentPageIndex).all()
    pages = {p["pk"]: p["fields"] for p in _models2dicts(page_objs)}
    content_pages = [
        *_models2dicts(ContentPage.objects.all()),
        *_models2dicts(ContentPageIndex.objects.all()),
    ]
    return [p | {"fields": {**pages[p["pk"]], **p["fields"]}} for p in content_pages]


def normalise_pks(pages):
    min_pk = min(p["pk"] for p in pages)
    return [p | {"pk": p["pk"] - min_pk} for p in pages]


def _update_field(pages, field_name, update_fn):
    for p in pages:
        fields = p["fields"]
        yield p | {"fields": {**fields, field_name: update_fn(fields[field_name])}}


def normalise_revisions(pages):
    min_latest = min(p["fields"]["latest_revision"] for p in pages)
    min_live = min(p["fields"]["live_revision"] for p in pages)
    pages = _update_field(pages, "latest_revision", lambda v: v - min_latest)
    pages = _update_field(pages, "live_revision", lambda v: v - min_live)
    return pages


def _remove_fields(pages, field_names):
    for p in pages:
        fields = {k: v for k, v in p["fields"].items() if k not in field_names}
        yield p | {"fields": fields}


PAGE_TIMESTAMP_FIELDS = {
    "first_published_at",
    "last_published_at",
    "latest_revision_created_at",
}


def remove_timestamps(pages):
    return _remove_fields(pages, PAGE_TIMESTAMP_FIELDS)


def _normalise_body_field_ids(page, body_name, body_str):
    body_list = json.loads(body_str)

    for i, body in enumerate(body_list):
        assert "id" in body
        body["id"] = f"fake:{page['pk']}:{body_name}:{i}"

    return json.dumps(body_list)


def _normalise_body_ids(page):
    fields = {
        k: _normalise_body_field_ids(page, k, v) if k.endswith("body") else v
        for k, v in page["fields"].items()
    }
    return page | {"fields": fields}


def normalise_body_ids(pages):
    # FIXME: Does it matter if these change?
    return [_normalise_body_ids(p) for p in pages]


def remove_translation_key(pages):
    # FIXME: translation_key should be preserved across imports.
    return _remove_fields(pages, {"translation_key"})


def _null_to_emptystr(page):
    fields = {**page["fields"]}
    for k in ["subtitle", "whatsapp_title", "messenger_title", "viber_title"]:
        if k in fields and fields[k] is None:
            fields[k] = ""
    if "whatsapp_body" in fields:
        body_list = json.loads(fields["whatsapp_body"])
        for body in body_list:
            if not body["value"]["next_prompt"]:
                body["value"]["next_prompt"] = ""
        fields["whatsapp_body"] = json.dumps(body_list)
    return page | {"fields": fields}


def null_to_emptystr(pages):
    # FIXME: Confirm that there's no meaningful difference here, potentially
    #        make these fields non-nullable.
    return [_null_to_emptystr(p) for p in pages]


PAGE_FILTER_FUNCS = [
    normalise_pks,
    normalise_revisions,
    remove_timestamps,
    normalise_body_ids,
    remove_translation_key,
    null_to_emptystr,
]


def get_page_json():
    """
    Serialize all ContentPage and ContentPageIndex instances and normalize
    things that vary across import/export.
    """
    pages = _get_page_json()
    for ff in PAGE_FILTER_FUNCS:
        pages = ff(pages)
    return sorted(pages, key=lambda p: p["pk"])


class ImportExportBaseTestCase(TestCase):
    def setUp(self):
        self.user_credentials = {"username": "test", "password": "test"}
        self.user = get_user_model().objects.create_superuser(**self.user_credentials)
        self.client.login(**self.user_credentials)

    def set_profile_field_options(self, profile_field_options):
        site = Site.objects.get(is_default_site=True)
        site_settings = SiteSettings.for_site(site)
        site_settings.profile_field_options.extend(profile_field_options)
        site_settings.save()

    def import_csv(self, csv_path, **kw):
        csv_path = Path(csv_path)
        with csv_path.open(mode="rb") as f:
            import_content(f, "CSV", queue.Queue(), **kw)
        return csv_path.read_bytes()


class ImportExportRoundtripTestCase(ImportExportBaseTestCase):
    def test_roundtrip_csv_simple(self):
        """
        Importing a simple CSV file and then exporting it produces a duplicate
        of the original file.

        (This uses content2.csv from test_api.py.)

        FIXME:
         * This should probably be in a separate test for importing old exports.
         * Do we actually need translation_tag to be added to tags?
         * Do we need page.id to be imported? At the moment nothing in the
           import reads that.
         * We should probably set contentpage.translation_key on import instead
           of messing about with tags.
         * Do we expect imported content to have leading spaces removed?
         * Should we set enable_web and friends based on body, title, or an
           enable field that we'll need to add to the export?
        """
        csv_bytes = self.import_csv("home/tests/content2.csv")
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        src, dst = csvs2dicts(csv_bytes, resp.content)
        assert dst == src

    def test_roundtrip_csv_less_simple(self):
        """
        Importing a less simple CSV file and then exporting it produces a
        duplicate of the original file.

        (This uses exported_content_20230911-variations-linked-page.csv.)

        FIXME:
         * Implement import/export for doc_link, image_link, media_link.
         * Implement import/export for next_prompt.
        """
        self.set_profile_field_options([("gender", ["male", "female", "empty"])])
        csv_bytes = self.import_csv(
            "home/tests/exported_content_20230911-variations-linked-page.csv"
        )
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        content = resp.content
        src, dst = csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_roundtrip_csv_translations(self):
        """
        Importing a CSV file containing translations and then exporting it
        produces a duplicate of the original file.

        (This uses exported_content_20230906-translations.csv and the two
        language-specific subsets thereof.)

        FIXME:
         * We shouldn't need to import different languages separately.
         * Slugs need to either be unique per site/deployment or the importer
           needs to handle them only being unique per locale.
        """

        # Create a new homepage for Portuguese.
        pt = Locale.objects.create(language_code="pt")
        HomePage.add_root(locale=pt, title="Home (pt)", slug="home-pt")

        self.set_profile_field_options([("gender", ["male", "female", "empty"])])
        self.import_csv("home/tests/translations-en.csv")
        self.import_csv("home/tests/translations-pt.csv", locale="pt", purge=False)
        csv_bytes = Path(
            "home/tests/exported_content_20230906-translations.csv"
        ).read_bytes()
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        src, dst = csvs2dicts(csv_bytes, resp.content)
        assert dst == src

    def test_import_error(self):
        """
        Importing an invalid CSV file leaves the db as-is.

        (This uses content2.csv from test_api.py and broken.csv.)
        """
        # Start with some existing content.
        csv_bytes = self.import_csv("home/tests/content2.csv")

        # This CSV doesn't have any of the fields we expect.
        with pytest.raises((KeyError, TypeError)):
            self.import_csv("home/tests/broken.csv")

        # The export should match the existing content.
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        src, dst = csvs2dicts(csv_bytes, resp.content)
        assert dst == src


class ExportImportRoundtripTestCase(ImportExportBaseTestCase):
    def reimport_csv(self, csv_bytes, **kw):
        import_content(BytesIO(csv_bytes), "CSV", queue.Queue(), **kw)

    def test_roundtrip_db_simple_csv(self):
        """
        Exporting to CSV and then importing leaves the db in the same state it
        was before, except for page_ids, timestamps, and body item ids.

        FIXME:
         * Fix viber import.
         * Copy translation_tag to translation_key for ContentPageIndex as well.
         * Determine whether we need to maintain StreamField block ids. (I
           think we don't.)
         * Confirm that there's no meaningful difference between null and ""
           for the nullable fields that the importer sets to "", potentially
           make these fields non-nullable.
        """
        home_page = HomePage.objects.first()
        main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
        mm_ftu_title = "main menu first time user"
        mm_ftu = PageBuilder.build_cp(
            parent=main_menu,
            slug="main-menu-first-time-user",
            title=mm_ftu_title,
            bodies=[
                WABody(mm_ftu_title, [WABlk("*Welcome to HealthAlert* WA")]),
                MBody(mm_ftu_title, [MBlk("Welcome to HealthAlert M")]),
            ],
        )
        _health_info = PageBuilder.build_cp(
            parent=mm_ftu,
            slug="health-info",
            title="health info",
            bodies=[
                WABody("health info", [WABlk("*Health information* WA")]),
                MBody("health info", [MBlk("*Health information* M")]),
            ],
        )
        _self_help = PageBuilder.build_cp(
            parent=mm_ftu,
            slug="self-help",
            title="self-help",
            bodies=[
                WABody("self-help", [WABlk("*Self-help programs* WA")]),
                MBody("self-help", [MBlk("*Self-help programs* M")]),
                # VBody("self-help", [VBlk("*Self-help programs* V")]),
            ],
        )

        orig = get_page_json()

        resp = self.client.get("/admin/home/contentpage/?export=csv")
        self.reimport_csv(resp.content)

        imported = get_page_json()
        assert imported == orig
