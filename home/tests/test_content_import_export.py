import csv
import queue
from functools import wraps
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from wagtail.models.sites import Site

from home.models import SiteSettings
from home.utils import import_content


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
    # FIXME: Add related page to import source.
    ignored_fields = {
        "page_id",
        "translation_tag",
        "doc_link",
        "image_link",
        "media_link",
        "next_prompt",
        "related_pages",
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


class ImportExportTestCase(TestCase):
    def setUp(self):
        self.user_credentials = {"username": "test", "password": "test"}
        self.user = get_user_model().objects.create_superuser(**self.user_credentials)
        self.client.login(**self.user_credentials)

    def set_profile_field_options(self, profile_field_options):
        site = Site.objects.get(is_default_site=True)
        site_settings = SiteSettings.for_site(site)
        site_settings.profile_field_options.extend(profile_field_options)
        site_settings.save()

    def import_csv(self, csv_path):
        with csv_path.open(mode="rb") as f:
            import_content(f, "CSV", queue.Queue())
        return csv_path.read_bytes()

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
        """
        csv_bytes = self.import_csv(Path("home/tests/content2.csv"))
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        content = resp.content
        src, dst = csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_roundtrip_csv_less_simple(self):
        """
        Importing a less simple CSV file and then exporting it produces a
        duplicate of the original file.

        (This uses exported_content_20230905.csv.)

        FIXME:
         * This should probably be in a separate test for importing old exports.
         * Do we actually need translation_tag to be added to tags?
         * Do we need page.id to be imported? At the moment nothing in the
           import reads that.
         * We should probably set contentpage.translation_key on import instead
           of messing about with tags.
         * Do we expect imported content to have leading spaces removed?
         * Implement import/export for doc_link, image_link, media_link.
         * Implement import/export for next_prompt.
         * Add related page to import source.
        """
        self.set_profile_field_options([("gender", ["male", "female", "empty"])])
        csv_bytes = self.import_csv(Path("home/tests/exported_content_20230905.csv"))
        resp = self.client.get("/admin/home/contentpage/?export=csv")
        content = resp.content
        src, dst = csvs2dicts(csv_bytes, content)
        assert dst == src
