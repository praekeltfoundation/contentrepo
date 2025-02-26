import csv
import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path
from queue import Queue
from typing import Any

import pytest
from django.core import serializers  # type: ignore
from wagtail.models import Locale  # type: ignore

from home.assessment_import_export import import_assessment
from home.content_import_export import import_content
from home.import_assessments import ImportAssessmentException
from home.import_helpers import ImportException
from home.models import (
    Assessment,
    ContentPage,
    HomePage,
)

from .page_builder import (
    MBlk,
    MBody,
    PageBuilder,
    WABlk,
    WABody,
)

IMP_EXP_DATA_BASE = Path("home/tests/import-export-data")

ExpDict = dict[str, Any]
ExpDicts = list[ExpDict]
ExpDictsPair = tuple[ExpDicts, ExpDicts]


def csv2dicts(csv_bytes: bytes) -> ExpDicts:
    return list(csv.DictReader(StringIO(csv_bytes.decode())))


DbDict = dict[str, Any]
DbDicts = list[DbDict]


def _models2dicts(model_instances: Any) -> DbDicts:
    return json.loads(serializers.serialize("json", model_instances))


def get_assessment_json() -> DbDicts:
    # assessment_objs = Assessment.objects.all()
    # assessments = {p["pk"]: p["fields"] for p in _models2dicts(assessment_objs)}
    assessments = [*_models2dicts(Assessment.objects.all())]
    return assessments
    # return [p | {"fields": {**pages[p["pk"]], **p["fields"]}} for p in content_pages]


def per_page(filter_func: Callable[[DbDict], DbDict]) -> Callable[[DbDicts], DbDicts]:
    @wraps(filter_func)
    def fp(pages: DbDicts) -> DbDicts:
        return [filter_func(page) for page in pages]

    return fp


def _is_json_field(field_name: str) -> bool:
    return field_name in {"questions"}


@per_page
def decode_json_fields(page: DbDict) -> DbDict:
    fields = {
        k: json.loads(v) if _is_json_field(k) else v for k, v in page["fields"].items()
    }
    return page | {"fields": fields}


def _remove_fields(pages: DbDicts, field_names: set[str]) -> DbDicts:
    for p in pages:
        p["fields"] = {k: v for k, v in p["fields"].items() if k not in field_names}
    return pages


def _update_field(
    pages: DbDicts, field_name: str, update_fn: Callable[[Any], Any]
) -> DbDicts:
    for p in pages:
        fields = p["fields"]
        p["fields"] = {**fields, field_name: update_fn(fields[field_name])}
    return pages


PAGE_TIMESTAMP_FIELDS = {
    "first_published_at",
    "last_published_at",
}


def remove_timestamps(assessments: DbDicts) -> DbDicts:
    return _remove_fields(assessments, PAGE_TIMESTAMP_FIELDS)


def normalise_revisions(assessments: DbDicts) -> DbDicts:
    min_latest = min(p["fields"]["latest_revision"] for p in assessments)
    min_live = min(p["fields"]["live_revision"] for p in assessments)
    assessments = _update_field(
        assessments, "latest_revision", lambda v: v - min_latest
    )
    assessments = _update_field(assessments, "live_revision", lambda v: v - min_live)
    return assessments


def normalise_pks(assessments: DbDicts) -> DbDicts:
    min_pk = min(p["pk"] for p in assessments)
    for assessment in assessments:
        assessment["pk"] -= min_pk
    return assessments


def _normalise_answer_ids(
    assessment: DbDict, a_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for i, a in enumerate(a_list):
        a["id"] = f"fake:{assessment['pk']}:answer_item:{i}"
        a["value"]["id"] = f"fake:{assessment['pk']}:answer:{i}"
    return a_list


def _normalise_question_ids(
    assessment: DbDict, q_list: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    for i, q in enumerate(q_list):
        assert "id" in q
        q["id"] = f"fake:{assessment['pk']}:question:{i}"
        _normalise_answer_ids(assessment, q["value"]["answers"])
    return q_list


@per_page
def normalise_nested_ids(assessment: DbDict) -> DbDict:
    _normalise_question_ids(assessment, assessment["fields"]["questions"])
    return assessment


ASSESSMENT_FILTER_FUNCS = [
    normalise_revisions,
    normalise_pks,
    normalise_nested_ids,
    remove_timestamps,
]


def create_content_page(title: str, slug: str, locale_code: str = "en") -> ContentPage:
    locale = Locale.objects.get(language_code=locale_code)
    home_page = HomePage.objects.get(slug="home")
    page = ContentPage(
        title=title,
        slug=slug,
        locale=locale,
    )
    home_page.add_child(instance=page)
    page.save_revision().publish()
    return page


def create_locale_if_not_exists(locale_code: str) -> None:
    if not Locale.objects.filter(language_code=locale_code).exists():
        Locale.objects.create(language_code=locale_code)


@dataclass
class ImportExport:
    admin_client: Any
    format: str

    def export_assessment(self) -> bytes:
        """
        Export all assessments in the configured format.
        """
        url = f"/admin/snippets/home/assessment/?export={self.format}"
        content = self.admin_client.get(url).content
        if self.format == "csv":
            print("-v-CONTENT-v-")
            print(content.decode())
            print("-^-CONTENT-^-")
        return content

    def import_assessment(self, content_bytes: bytes, **kw: Any) -> None:
        """
        Import given content in the configured format with the configured importer.
        """
        import_assessment(BytesIO(content_bytes), self.format.upper(), Queue(), **kw)

    def read_bytes(self, path_str: str, path_base: Path = IMP_EXP_DATA_BASE) -> bytes:
        return (path_base / path_str).read_bytes()

    def import_file(
        self, path_str: str, path_base: Path = IMP_EXP_DATA_BASE, **kw: Any
    ) -> bytes:
        """
        Import given content file in the configured format with the configured importer.
        """
        content = self.read_bytes(path_str, path_base)
        self.import_assessment(content, **kw)
        return content

    def import_content_file(
        self, path_str: str, path_base: Path = IMP_EXP_DATA_BASE, **kw: Any
    ) -> bytes:
        """
        Import given content file in the configured format with the configured importer.
        """
        content = self.read_bytes(path_str, path_base)
        self.import_content(content, **kw)
        return content

    def import_content(self, content_bytes: bytes, **kw: Any) -> None:
        """
        Import given content in the configured format with the configured importer.
        """
        import_content(BytesIO(content_bytes), self.format.upper(), Queue(), **kw)

    def export_reimport(self) -> None:
        """
        Export all content, then immediately reimport it.
        """
        self.import_assessment(self.export_assessment(), purge=True)

    def csvs2dicts(self, src_bytes: bytes, dst_bytes: bytes) -> ExpDictsPair:
        src = csv2dicts(src_bytes)
        dst = csv2dicts(dst_bytes)
        return src, dst

    def get_assessment_json(self) -> DbDicts:
        """
        Serialize all Assessment instances and normalize things that vary across
        import/export.
        """
        assessments = decode_json_fields(get_assessment_json())
        for ff in ASSESSMENT_FILTER_FUNCS:
            assessments = ff(assessments)
        return sorted(assessments, key=lambda p: p["pk"])


@pytest.fixture(params=["csv", "xlsx"])
def impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, request.param)


@pytest.fixture()
def csv_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "csv")


@pytest.fixture()
def xlsx_impexp(request: Any, admin_client: Any) -> ImportExport:
    return ImportExport(admin_client, "xlsx")


@pytest.fixture()
def result_content_pages() -> None:
    home_page = HomePage.objects.first()
    main_menu = PageBuilder.build_cpi(home_page, "main-menu", "Main Menu")
    PageBuilder.build_cp(
        parent=main_menu,
        slug="high-inflection",
        title="High Inflection",
        bodies=[
            WABody("High Inflection", [WABlk("*High Inflection Page")]),
            MBody("High inflection", [MBlk("High Inflection Page")]),
        ],
    )
    PageBuilder.build_cp(
        parent=main_menu,
        slug="medium-score",
        title="Medium Score",
        bodies=[
            WABody("Medium Score", [WABlk("*Medium Inflection Page")]),
            MBody("Medium Score", [MBlk("Medium Inflection Page")]),
        ],
    )

    PageBuilder.build_cp(
        parent=main_menu,
        slug="low-score",
        title="Low Score",
        bodies=[
            WABody("Low Score", [WABlk("*Low Inflection Page")]),
            MBody("Low Score", [MBlk("Low Inflection Page")]),
        ],
    )

    PageBuilder.build_cp(
        parent=main_menu,
        slug="skip-score",
        title="Skip Score",
        bodies=[
            WABody("Skip Score", [WABlk("*Skip Result Page")]),
            MBody("Skip Score", [MBlk("Skip Result Page")]),
        ],
    )


@pytest.mark.usefixtures("result_content_pages")
@pytest.mark.django_db()
class TestImportExportRoundtrip:
    """
    Test importing and reexporting assessments produces an export that is
    equilavent to the original imported assessments.

    NOTE: This is not a Django (or even unittest) TestCase. It's just a
        container for related tests.
    """

    def test_simple(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with one assessment and
        one of each question and export it

        (This uses assessment_simple.csv.)
        """
        csv_bytes = csv_impexp.import_file("assessment_simple.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_less_simple_multiple_questions(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with two assessments and
        multiple questions and export it

        (This uses assessment_less_simple.csv.)
        """
        csv_bytes = csv_impexp.import_file("assessment_less_simple.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_multiple_assessments(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with more than one assessment and
        multiple questions and export it

        (This uses multiple_assessments.csv.)
        """
        csv_bytes = csv_impexp.import_file("multiple_assessments.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_bulk_assessments(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file with more than five assessments and
        multiple questions and export it

        (This uses bulk_assessments.csv.)
        """
        csv_bytes = csv_impexp.import_file("bulk_assessments.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_assessments_with_blank_results(self, csv_impexp: ImportExport) -> None:
        """
        Importing a simple CSV file without results pages and inflection points
        (This uses results_assessments.csv.)
        """
        csv_bytes = csv_impexp.import_file("results_assessments.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_comma_separated_answers(self, csv_impexp: ImportExport) -> None:
        """
        CSV file where the answers have commas in them that need to be escaped

        (This uses comma_seperated_answers.csv.)
        """
        csv_bytes = csv_impexp.import_file("comma_separated_answers.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_single_assessment(self, impexp: ImportExport) -> None:
        """
        Exporting then reimporting leaves the database in the same state we started with
        """
        assessment = Assessment.objects.create(
            title="Test",
            slug="test",
            locale=Locale.objects.get(language_code="en"),
            high_result_page=ContentPage.objects.get(slug="high-inflection"),
            high_inflection=3,
            medium_result_page=ContentPage.objects.get(slug="medium-score"),
            medium_inflection=2,
            low_result_page=ContentPage.objects.get(slug="low-score"),
            skip_threshold=2,
            skip_high_result_page=ContentPage.objects.get(slug="skip-score"),
            generic_error="error",
            questions=[
                {
                    "type": "categorical_question",
                    "value": {
                        "question": "test question",
                        "error": "test error",
                        "semantic_id": "unique_id",
                        "explainer": "test explainer",
                        "answers": [
                            {
                                "answer": "test answer",
                                "score": 2.0,
                                "semantic_id": "unique_id",
                                "response": "test response",
                            }
                        ],
                    },
                }
            ],
        )
        assessment.save_revision().publish()
        orig = impexp.get_assessment_json()
        impexp.export_reimport()
        imported = impexp.get_assessment_json()
        assert imported == orig

    def test_snake_case_assessments(self, csv_impexp: ImportExport) -> None:
        """
        Importing a csv with spaces in header names and uppercase text should be converted to snake case
        and pass, provided that the converted text are valid cms headers.
        Here we check that the headers are changed to snake case, the assessment is saved
        and finally we check that the saved assessment has the correct headers.

        (This uses snake_case_assessments.csv.)
        """
        csv_impexp.import_file("snake_case_assessments.csv")
        imported_assessments = Assessment.objects.all()
        assert imported_assessments.exists()
        assessment_model = Assessment
        model_fields = [field.name for field in assessment_model._meta.get_fields()]

        expected_fields = [
            "title",
            "slug",
            "high_inflection",
            "medium_inflection",
            "high_result_page",
            "medium_result_page",
            "low_result_page",
            "skip_high_result_page",
            "skip_threshold",
            "generic_error",
            "questions",
        ]

        for field_name in expected_fields:
            assert (
                field_name in model_fields
            ), f"Field '{field_name}' not found in Assessment model."


@pytest.mark.usefixtures("result_content_pages")
@pytest.mark.django_db()
class TestImportExport:
    """
    Test import and export scenarios that aren't specifically round
    trips.

    """

    def test_missing_related_pages(self, csv_impexp: ImportExport) -> None:
        """
        Related pages are listed as comma separated slugs in imported files. If there
        is a slug listed that we cannot find the page for, then we should show the
        user an error with information about the missing page.

        (This uses assessment_missing_related_page.csv.)
        """

        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessment_missing_related_page.csv")
        assert (
            e.value.message
            == "You are trying to add an assessment, where one of the result pages "
            "references the content page with slug fake-page and locale English which does not exist. "
            "Please create the content page first."
        )

    def test_import_error(self, csv_impexp: ImportExport) -> None:
        """
        Importing an invalid CSV file leaves the db as-is.

        (This uses broken_assessment.csv)
        """
        csv_bytes = csv_impexp.import_file("assessment_simple.csv")
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("broken_assessment.csv")
        assert (
            e.value.message
            == "Missing mandatory headers: title, question, slug, generic_error, locale"
        )
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src

    def test_invalid_locale_code(self, csv_impexp: ImportExport) -> None:
        """
        Importing assessments with invalid locale code should raise an error that results
        in an error message that gets sent back to the user

        (This uses invalid-assessment-locale-name.csv.)
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("invalid-assessment-locale-name.csv")

        assert e.value.row_num == 2
        assert e.value.message == "Language code not found: fakecode"

    def test_import_assessment_xlsx(self, xlsx_impexp: ImportExport) -> None:
        """
        Importing an XLSX file with Assessments should not break
        """
        xlsx_impexp.import_content_file("assessment_results.xlsx", purge=False)
        xlsx_impexp.import_file("assessment.xlsx", purge=False)
        content_pages = Assessment.objects.all()
        assert len(content_pages) > 0

    def test_import_assessment_empty_values_xlsx(
        self, xlsx_impexp: ImportExport
    ) -> None:
        """
        Importing an XLSX  Assessments file where the corresponding cell is empty
        should not break.
        """
        xlsx_impexp.import_content_file("assessment_results.xlsx", purge=False)
        xlsx_impexp.import_file("assessment_empty_values.xlsx", purge=False)
        content_pages = Assessment.objects.all()
        assert len(content_pages) > 0

    def test_invalid_high_inflecton_format(self, xlsx_impexp: ImportExport) -> None:
        """
        Importing an xlsx with a comma in high inflecton value
        should return a helpful error informing the user
        where the issue is.

        (This uses high_inflection_invalid_format.xlsx)
        """

        with pytest.raises(ImportAssessmentException) as e:
            xlsx_impexp.import_content_file("assessment_results.xlsx", purge=False)
            xlsx_impexp.import_file("high_inflection_invalid_format.xlsx")
        assert (
            e.value.message == "Invalid number format for high inflection. "
            "Please use '.' instead of ',' for decimals."
        )
        assert e.value.row_num == 5

    def test_invalid_medium_inflecton_format(self, xlsx_impexp: ImportExport) -> None:
        """
        Importing an xlsx with a comma in medium inflecton value
        should return a helpful error informing the user
        where the issue is.

        (This uses medium_inflection_invalid_format.xlsx)
        """

        with pytest.raises(ImportAssessmentException) as e:
            xlsx_impexp.import_content_file("assessment_results.xlsx", purge=False)
            xlsx_impexp.import_file("medium_inflection_invalid_format.xlsx")
        assert (
            e.value.message == "Invalid number format for medium inflection. "
            "Please use '.' instead of ',' for decimals."
        )
        assert e.value.row_num == 2

    def test_invalid_high_inflecton_csv_format(self, csv_impexp: ImportExport) -> None:
        """
        Importing a csv with a comma in high inflecton value
        should return a helpful error informing the user
        where the issue is.

        (This uses high_inflection_invalid_format.csv)
        """

        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_content_file("assessment_results.csv", purge=False)
            csv_impexp.import_file("high_inflection_invalid_format.csv")
        assert (
            e.value.message == "Invalid number format for high inflection. "
            "Please use '.' instead of ',' for decimals."
        )
        assert e.value.row_num == 2

    def test_extra_columns_csv(self, csv_impexp: ImportExport) -> None:
        """
        Importing a csv with an extra comma so there are more
        column values than headers should return an intuitive error message

        (This uses extra_columns.csv)
        """

        with pytest.raises(ImportException) as e:
            csv_impexp.import_content_file("assessment_results.csv", purge=False)
            csv_impexp.import_file("extra_columns.csv")
        assert e.value.message == [
            "Invalid format. Please check that all row values have headers."
        ]

    def test_extra_columns_xlsx(
        self, xlsx_impexp: ImportExport, csv_impexp: ImportExport
    ) -> None:
        """
        Importing a xlsx with an extra comma so there are more
        column values than headers should return an intuitive error message

        (This uses extra_columns.xlsx)
        """

        with pytest.raises(ImportException) as e:
            csv_impexp.import_content_file("assessment_results.csv", purge=False)
            xlsx_impexp.import_file("extra_columns.xlsx")
        assert e.value.message == [
            "Invalid format. Please check that all row values have headers."
        ]

    def test_mismatched_length_answers(self, csv_impexp: ImportExport) -> None:
        """
        If the amount of answers, scores, and answer semantic ids in a row do not match,
        then it is an invalid import file and an appropriate error message should be
        shown.

        (This uses assessment_answers_mismatched_lengths.csv.)
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessment_answers_mismatched_lengths.csv")
        assert (
            e.value.message
            == "The amount of answers (5), scores (4), answer semantic IDs (5), and "
            "answer responses (5) do not match."
        )
        assert e.value.row_num == 2

    def test_invalid_high_score(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV with invalid data in the high inflection value should
        return an intuitive error message
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("bad_form_score.csv")
        assert (
            e.value.message == "Invalid number format for high inflection. "
            "The score value allows only numbers"
        )
        assert e.value.row_num == 2

    def test_invalid_medium_score(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV with invalid data in the medium inflection value should
        return an intuitive error message
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("bad_medium_score.csv")
        assert (
            e.value.message == "Invalid number format for medium inflection. "
            "The score value allows only numbers"
        )
        assert e.value.row_num == 2

    def test_multiple_missing_headers(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV with multiple missing headers should return an error
        stating all the mandatory headers that are missing
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessments_multiple_missing_headers.csv")
        assert (
            e.value.message == "Missing mandatory headers: title, slug, "
            "generic_error, locale"
        )
        assert e.value.row_num == 1

    def test_missing_title(self, csv_impexp: ImportExport) -> None:
        """
        Importing a CSV with a missing title field should return an error
        that a title is missing
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessments_missing_title.csv")
        assert e.value.message == "Row missing values for required fields: title"
        assert e.value.row_num == 4

    def test_empty_rows(self, csv_impexp: ImportExport) -> None:
        """
        Importing an empty CSV should return an error that the
        import file has no rows.
        """
        with pytest.raises(ImportException) as e:
            csv_impexp.import_file("empty.csv")
        assert e.value.message == [
            "The import file is empty or contains no valid rows."
        ]
        assert e.value.row_num == 1

    def test_multiple_missing_values(self, csv_impexp: ImportExport) -> None:
        """
        Importing an empty CSV should return an error with all the missing
        values in a row
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessments_missing_row_values.csv")
        assert (
            e.value.message
            == "Row missing values for required fields: title, slug, generic_error, locale"
        )
        assert e.value.row_num == 4

    def test_single_missing_header_multiple_missing_rows(
        self, csv_impexp: ImportExport
    ) -> None:
        """
        Importing a CSV with a single missing header and multiple missing rows
        should return an error that a header is missing
        """
        with pytest.raises(ImportAssessmentException) as e:
            csv_impexp.import_file("assessments_single_header_multiple_fields.csv")
        assert e.value.message == "Missing mandatory headers: title"
        assert e.value.row_num == 1


@pytest.mark.usefixtures("result_content_pages")
@pytest.mark.django_db()
class TestImportMultipleLanguages:

    def test_create_content_page(self, csv_impexp: ImportExport) -> None:
        """
        Importing a csv with a results page that has the same slug
        in more than one locale should pass.

        This test uses high-inflection as slug and high-result page in English and French locale
        The English high-inflection is already created by the result_content_pages fixture
        The French high_inflection is created below
        """

        high_inflection_page_en = ContentPage.objects.get(
            slug="high-inflection", locale__language_code="en"
        )

        create_locale_if_not_exists("fr")
        high_inflection_page_fr = create_content_page(
            "High Inflection", "high-inflection", locale_code="fr"
        )

        assert high_inflection_page_en.title == "High Inflection"
        assert high_inflection_page_en.locale.language_code == "en"
        assert high_inflection_page_en.live is True

        assert high_inflection_page_fr.title == "High Inflection"
        assert high_inflection_page_fr.locale.language_code == "fr"
        assert high_inflection_page_fr.live is True

        csv_bytes = csv_impexp.import_file("multiple_language.csv")
        content = csv_impexp.export_assessment()
        src, dst = csv_impexp.csvs2dicts(csv_bytes, content)
        assert dst == src
