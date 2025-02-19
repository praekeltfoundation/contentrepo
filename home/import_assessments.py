import contextlib
import csv
from dataclasses import dataclass, field, fields
from queue import Queue
from typing import Any

from django.core.exceptions import ObjectDoesNotExist, ValidationError  # type: ignore
from taggit.models import Tag  # type: ignore
from treebeard.exceptions import NodeAlreadySaved  # type: ignore
from wagtail.admin.panels import get_edit_handler  # type: ignore
from wagtail.coreutils import get_content_languages  # type: ignore
from wagtail.models import Locale, Page  # type: ignore

from home.import_helpers import (
    ImportException,
    convert_headers_to_snake_case,
    validate_using_form,
)
from home.import_helpers import (
    parse_file as helper_parse_file,
)
from home.models import Assessment, ContentPage, HomePage  # type: ignore

AssessmentId = tuple[str, Locale]
MANDATORY_HEADERS = ["title", "question", "slug", "generic_error", "locale"]


class ImportAssessmentException(Exception):
    """
    Base exception for all import related issues.
    """

    def __init__(self, message: str, row_num: int | None = None):
        self.row_num = row_num
        self.message = message
        super().__init__()


class AssessmentImporter:
    def __init__(
        self,
        file_content: bytes,
        file_type: str,
        progress_queue: Queue[int],
        purge: bool | str = True,
        locale: Locale | str | None = None,
    ):
        if isinstance(locale, str):
            locale = Locale.objects.get(language_code=locale)
        self.file_content = file_content
        self.file_type = file_type
        self.progress_queue = progress_queue
        self.purge = purge in ["True", "yes", True]
        self.locale = locale
        self.locale_map: dict[str, Locale] = {}
        self.shadow_assessments: dict[AssessmentId, ShadowAssessment] = {}

    def locale_from_language_code(self, lang_code_entry: str) -> Locale:
        if lang_code_entry not in self.locale_map:
            codes = []
            lang_name = ""
            for lang_code, lang_dn in get_content_languages().items():
                if lang_code == lang_code_entry or lang_dn == lang_code_entry:
                    lang_name = lang_dn
                    codes.append(lang_code)
            if not codes:
                raise ImportAssessmentException(
                    f"Language code not found: {lang_code_entry}"
                )
            if len(codes) > 1:
                raise ImportAssessmentException(
                    f"Multiple codes for language: {lang_name} -> {codes}"
                )
            self.locale_map[lang_code_entry] = Locale.objects.get(
                language_code=codes[0]
            )
        return self.locale_map[lang_code_entry]

    def perform_import(self) -> None:
        rows = self.parse_file()
        self.set_progress("Loaded file", 5)

        if self.purge:
            self.delete_existing_assessments()
        self.set_progress("Deleted existing assessment", 10)

        self.process_rows(rows)
        self.save_assessments()

    def process_rows(self, rows: list["AssessmentRow"]) -> None:
        for i, row in enumerate(rows, start=2):
            try:
                self.create_shadow_assessment_from_row(row, i)
            except ImportAssessmentException as e:
                e.row_num = i
                raise e

    def save_assessments(self) -> None:
        for i, assessment in enumerate(reversed(self.shadow_assessments.values())):
            parent = self.home_page(assessment.locale)
            assessment.save(parent)
            self.set_progress(
                "Importing assessments", 10 + 70 * i // len(self.shadow_assessments)
            )

    def parse_file(self) -> list["AssessmentRow"]:
        """
        Converts the iterator to a list of rows.
        If there are rows:
            a. Extracts the original headers from the first row.
            b. Converts the original headers to snake_case and creates a mapping from original headers to snake_case headers.
            c. Validates that the snake_case headers contain all mandatory headers.
            d. Transforms each row to use snake_case headers.
        """
        row_iterator = helper_parse_file(self.file_content, self.file_type)
        rows = [row for _, row in row_iterator]

        original_headers = rows[0].keys()
        headers_mapping = convert_headers_to_snake_case(
            list(original_headers), row_num=1
        )

        snake_case_headers = list(headers_mapping.values())
        self.validate_headers(snake_case_headers, row_num=1)
        transformed_rows = [
            {headers_mapping[key]: value for key, value in row.items()} for row in rows
        ]

        return [
            AssessmentRow.from_flat(row, i + 2)
            for i, row in enumerate(transformed_rows)
        ]

    def set_progress(self, message: str, progress: int) -> None:
        self.progress_queue.put_nowait(progress)

    def delete_existing_assessments(self) -> None:
        Assessment.objects.all().delete()

    def home_page(self, locale: Locale) -> HomePage:
        try:
            return HomePage.objects.get(locale=locale)
        except ObjectDoesNotExist:
            raise ImportAssessmentException(
                f"The HomePage for the locale {locale} does not exist. Please add "
                f"it before importing an assessment for {locale}"
            )

    def create_shadow_assessment_from_row(
        self, row: "AssessmentRow", row_num: int
    ) -> None:
        locale = self.locale_from_language_code(row.locale)
        if not (assessment := self.shadow_assessments.get((row.slug, locale))):
            assessment = self.shadow_assessments[(row.slug, locale)] = ShadowAssessment(
                row_num=row_num,
                title=row.title,
                slug=row.slug,
                version=row.version,
                locale=locale,
                high_result_page=row.high_result_page,
                medium_result_page=row.medium_result_page,
                low_result_page=row.low_result_page,
                skip_high_result_page=row.skip_high_result_page,
                high_inflection=(
                    None if row.high_inflection == "" else float(row.high_inflection)
                ),
                medium_inflection=(
                    None
                    if row.medium_inflection == ""
                    else float(row.medium_inflection)
                ),
                skip_threshold=(
                    0.0 if row.skip_threshold == "" else float(row.skip_threshold)
                ),
                generic_error=row.generic_error,
                tags=row.tags,
            )
        if not (
            len(row.answers)
            == len(row.scores)
            == len(row.answer_semantic_ids)
            == len(row.answer_responses)
        ):
            raise ImportAssessmentException(
                message=f"The amount of answers ({len(row.answers)}), scores "
                f"({len(row.scores)}), answer semantic IDs "
                f"({len(row.answer_semantic_ids)}), and answer responses "
                f"({len(row.answer_responses)}) do not match.",
                row_num=row_num,
            )
        answers = [
            ShadowAnswerBlock(
                answer=answer,
                score=score,
                semantic_id=semantic_id,
                response=response,
            )
            for (answer, score, semantic_id, response) in zip(
                row.answers,
                row.scores,
                row.answer_semantic_ids,
                row.answer_responses,
                strict=True,
            )
        ]
        question = ShadowQuestionBlock(
            question=row.question,
            error=row.error,
            min=row.min,
            max=row.max,
            answers=answers,
            type=row.question_type,
            explainer=row.explainer,
            semantic_id=row.question_semantic_id,
        )
        assessment.questions.append(question)

    def validate_headers(self, headers: list[str], row_num: int) -> None:
        missing_headers = [
            header for header in MANDATORY_HEADERS if header not in headers
        ]
        if missing_headers:
            raise ImportAssessmentException(
                message=f"Missing mandatory headers: {', '.join(missing_headers)}",
                row_num=row_num,
            )


# Since wagtail page models are so difficult to create and modify programatically,
# we instead store all the pages as these shadow objects, which we can then at the end
# do a single write to the database from, and encapsulate all that complexity
@dataclass(slots=True)
class ShadowAnswerBlock:
    answer: str
    score: float
    semantic_id: str
    response: str


@dataclass(slots=True)
class ShadowQuestionBlock:
    question: str
    answers: list[ShadowAnswerBlock]
    explainer: str = ""
    error: str = ""
    min: str = ""
    max: str = ""
    type: str = ""
    semantic_id: str = ""


@dataclass(slots=True)
class ShadowAssessment:
    row_num: int
    title: str
    slug: str
    version: str
    locale: Locale
    high_result_page: str
    medium_result_page: str
    low_result_page: str
    high_inflection: float | None
    medium_inflection: float | None
    skip_threshold: float
    skip_high_result_page: str
    generic_error: str
    questions: list[ShadowQuestionBlock] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # FIXME: collect errors across all fields
    def validate_snippet_using_form(self, model: Assessment) -> None:

        edit_handler = get_edit_handler(Assessment)
        validate_using_form(edit_handler, model, self.row_num)

    def save(self, parent: Page) -> None:
        try:
            assessment = Assessment.objects.get(slug=self.slug, locale=self.locale)
        except Assessment.DoesNotExist:
            assessment = Assessment(slug=self.slug, locale=self.locale)

        try:
            self.add_field_values_to_assessment(assessment)
            self.add_tags_to_assessment(assessment)
            self.validate_snippet_using_form(assessment)
            with contextlib.suppress(NodeAlreadySaved):
                parent.add_child(instance=assessment)
            assessment.save_revision().publish()
        except ValidationError as err:
            raise ImportAssessmentException(f"Validation error: {err}", self.row_num)
        except ImportException as e:
            e.row_num = self.row_num
            e.slug = assessment.slug
            e.locale = assessment.locale
            print(f"{e.row_num}: {e.message}")
            raise e

    def add_field_values_to_assessment(self, assessment: Assessment) -> None:
        assessment.slug = self.slug
        assessment.title = self.title
        assessment.version = self.version
        assessment.locale = self.locale
        assessment.high_inflection = self.high_inflection
        assessment.high_result_page_id = (
            None
            if self.high_result_page == ""
            else get_content_page_id_from_slug(self.high_result_page, self.locale)
        )
        assessment.medium_inflection = self.medium_inflection
        assessment.medium_result_page_id = (
            None
            if self.medium_result_page == ""
            else get_content_page_id_from_slug(self.medium_result_page, self.locale)
        )
        assessment.low_result_page_id = (
            None
            if self.low_result_page == ""
            else get_content_page_id_from_slug(self.low_result_page, self.locale)
        )
        assessment.skip_high_result_page_id = (
            None
            if self.skip_high_result_page == ""
            else get_content_page_id_from_slug(self.skip_high_result_page, self.locale)
        )
        assessment.skip_threshold = self.skip_threshold
        assessment.generic_error = self.generic_error
        assessment.questions = self.questions_as_streamfield

    def add_tags_to_assessment(self, assessment: Assessment) -> None:
        assessment.tags.clear()
        for tag_name in self.tags:
            tag, _ = Tag.objects.get_or_create(name=tag_name)
            assessment.tags.add(tag)

    @property
    def questions_as_streamfield(self) -> list[dict[str, Any]]:
        """
        Formats the questions in the wagtail streamfield formatting
        """
        stream_data = []
        for question in self.questions:
            answers = [
                {
                    "answer": answer.answer,
                    "score": answer.score,
                    "semantic_id": answer.semantic_id,
                    "response": answer.response,
                }
                for answer in question.answers
            ]
            stream_data.append(
                {
                    "type": question.type,
                    "value": {
                        "question": question.question,
                        "answers": answers,
                        "explainer": question.explainer,
                        "error": question.error,
                        "min": question.min,
                        "max": question.max,
                        "semantic_id": question.semantic_id,
                    },
                }
            )
        return stream_data


@dataclass(slots=True, frozen=True)
class AssessmentRow:
    """
    Represents a single, deserialised row from an import file
    """

    slug: str
    title: str = ""
    version: str = ""
    tags: list[str] = field(default_factory=list)
    question_type: str = ""
    locale: str = ""
    high_result_page: str = ""
    high_inflection: str = ""
    medium_result_page: str = ""
    medium_inflection: str = ""
    low_result_page: str = ""
    skip_threshold: str = ""
    skip_high_result_page: str = ""
    generic_error: str = ""
    question: str = ""
    explainer: str = ""
    error: str = ""
    min: str = ""
    max: str = ""
    answers: list[str] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    answer_semantic_ids: list[str] = field(default_factory=list)
    question_semantic_id: str = ""
    answer_responses: list[str] = field(default_factory=list)

    @classmethod
    def fields(cls) -> list[str]:
        return [field.name for field in fields(cls)]

    @classmethod
    def check_missing_fields(cls, row: dict[str, str], row_num: int) -> None:
        """
        Checks for missing required fields in the row and raises an exception if any is missing.
        """
        missing_fields = [field for field in MANDATORY_HEADERS if field not in row]
        if missing_fields:
            raise ImportAssessmentException(
                f"The import file is missing required fields: {', '.join(missing_fields)}",
                row_num,
            )

    @classmethod
    def from_flat(cls, row: dict[str, str], row_num: int) -> "AssessmentRow":
        """
        Creates an AssessmentRow instance from a row in the import, deserialising the
        fields.
        """

        high_inflection = row.get("high_inflection")
        medium_inflection = row.get("medium_inflection")
        check_punctuation(high_inflection, medium_inflection, row_num)
        check_score_type(high_inflection, medium_inflection, row_num)

        row = {
            key: value for key, value in row.items() if value and key in cls.fields()
        }

        cls.check_missing_fields(row, row_num)

        answers = deserialise_list(row.pop("answers", ""))
        answer_responses = deserialise_list(row.pop("answer_responses", ""))
        if not answer_responses:
            answer_responses = [""] * len(answers)

        return cls(
            tags=deserialise_list(row.pop("tags", "")),
            answers=answers,
            scores=[float(i) for i in deserialise_list(row.pop("scores", ""))],
            answer_semantic_ids=deserialise_list(row.pop("answer_semantic_ids", "")),
            answer_responses=answer_responses,
            **row,
        )


def get_content_page_id_from_slug(slug: str, locale: Locale) -> int:
    try:
        page = ContentPage.objects.get(slug=slug, locale=locale)
    except ObjectDoesNotExist:
        raise ImportAssessmentException(
            f"You are trying to add an assessment, where one of the result pages "
            f"references the content page with slug {slug} and locale {locale} which does not exist. "
            "Please create the content page first."
        )
    return page.id


def check_punctuation(
    high_inflection: str | None, medium_inflection: str | None, row_num: int
) -> None:
    if high_inflection is not None:
        high_inflection = str(high_inflection)
        punctuaton = "," in high_inflection
        if punctuaton:
            raise ImportAssessmentException(
                "Invalid number format for high inflection. "
                "Please use '.' instead of ',' for decimals.",
                row_num,
            )
    if medium_inflection is not None:
        medium_inflection = str(medium_inflection)
        punctuation = "," in medium_inflection
        if punctuation:
            raise ImportAssessmentException(
                "Invalid number format for medium inflection. "
                "Please use '.' instead of ',' for decimals.",
                row_num,
            )


def check_score_type(
    high_inflection: Any | None, medium_inflection: Any | None, row_num: int
) -> None:
    if high_inflection is not None and high_inflection != "":
        try:
            float(high_inflection)
        except ValueError:
            raise ImportAssessmentException(
                "Invalid number format for high inflection. "
                "The score value allows only numbers",
                row_num,
            )
    if medium_inflection is not None and medium_inflection != "":
        try:
            float(medium_inflection)
        except ValueError:
            raise ImportAssessmentException(
                "Invalid number format for medium inflection. "
                "The score value allows only numbers",
                row_num,
            )


def deserialise_list(value: str) -> list[str]:
    """
    Takes a comma separated value serialised by the CSV library, and returns it as a
    deserialised list
    """
    items = next(csv.reader([value]))
    return [item.strip() for item in items]
