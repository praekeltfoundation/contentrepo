# The error messages are processed and parsed into a list of messages we return to the user
from collections.abc import Iterator
from typing import Any

from django.core.exceptions import ValidationError  # type: ignore
from django.db.models import Model  # type: ignore
from django.forms import model_to_dict  # type: ignore
from wagtail.admin.rich_text.converters.contentstate import (  # type: ignore
    ContentstateConverter,  # type: ignore
)
from wagtail.blocks import (  # type: ignore
    StreamBlockValidationError,
    StreamValue,
    StructValue,  # type: ignore
)
from wagtail.blocks.list_block import ListValue  # type: ignore
from wagtail.coreutils import get_content_languages  # type: ignore
from wagtail.models import Locale  # type: ignore
from wagtail.rich_text import RichText  # type: ignore
from wagtail.test.utils.form_data import nested_form_data, streamfield  # type: ignore


class ImportException(Exception):
    """
    Base exception for all import related issues.
    """

    def __init__(
        self,
        message: str | list[str],
        row_num: int | None = None,
        slug: str | None = None,
        locale: Locale | None = None,
    ):
        self.row_num = row_num
        self.message = [message] if isinstance(message, str) else message
        self.slug = slug
        self.locale = locale
        super().__init__()


class LocaleHelper:
    """
    Helper class to map language names to locales
    """

    def __init__(self):
        self.locale_map: dict[str, Locale] = {}

    def locale_from_display_name(self, langname: str) -> Locale:
        """
        Get a locale from its display name.

        If the locale for the given language name does not exist, an exception is raised.

        :param langname: The name of the language.
        :return: The locale for the given language.
        :raises ImportException: If the language name is not found or has multiple codes.
        """

        if langname not in self.locale_map:
            codes = []
            for lang_code, lang_dn in get_content_languages().items():
                if lang_dn == langname:
                    codes.append(lang_code)
            if not codes:
                raise ImportException(f"Language not found: {langname}")
            if len(codes) > 1:
                raise ImportException(
                    f"Multiple codes for language: {langname} -> {codes}"
                )
            self.locale_map[langname] = Locale.objects.get(language_code=codes[0])
        return self.locale_map[langname]


def wagtail_to_formdata(val: Any) -> Any:
    """
    Convert a model dict field that may be a nested streamfield (or associated
    type) into something we can turn into form data.
    """
    match val:
        case StreamValue():  # type: ignore[misc] # No type info
            return streamfield(
                [(b.block_type, wagtail_to_formdata(b.value)) for b in val]
            )
        case StructValue():  # type: ignore[misc] # No type info
            return {k: wagtail_to_formdata(v) for k, v in val.items()}
        case ListValue():  # type: ignore[misc] # No type info
            # Wagtail doesn't have an equivalent of streamfield() for
            # listvalue, so we have to do it by hand.
            list_val: dict[str, Any] = {
                str(i): {
                    "deleted": "",
                    "order": str(i),
                    "value": wagtail_to_formdata(v),
                }
                for i, v in enumerate(val)
            }
            list_val["count"] = str(len(val))
            return list_val
        case RichText():  # type: ignore[misc] # No type info
            # FIXME: The only RichTextBlock() we currently have is in the web
            #        body and we don't appear to do any validation on it.
            #        There's probably a better way to convert and/or ignore these.
            return ContentstateConverter([]).from_database_format(val.source)
        case _:
            return val


def validate_using_form(edit_handler: Any, model: Model, row_num: int) -> None:
    form_class = edit_handler.get_form_class()

    form_data = nested_form_data(
        {k: wagtail_to_formdata(v) for k, v in model_to_dict(model).items()}
    )

    form = form_class(form_data)
    if not form.is_valid():
        errs = form.errors.as_data()
        if "slug" in errs:
            errs["slug"] = [err for err in errs["slug"] if err.code != "slug-in-use"]
            if not errs["slug"]:
                del errs["slug"]
        # TODO: better error stuff
        if errs:
            errors = []
            error_message = errors_to_list(errs)
            for err in error_message:
                errors.append(f"Validation error: {err}")
            raise ImportException(errors, row_num)


def errors_to_list(errs: dict[str, list[str]]) -> str | list[str]:

    def _extract_errors(
        data: dict[str | int, Any] | list[str]
    ) -> Iterator[tuple[list[str], str]]:
        if isinstance(data, dict):
            items = list(data.items())
        elif isinstance(data, list):
            items = list(enumerate(data))

        for key, value in items:
            key = str(key)
            if isinstance(value, dict | list):
                for child_keys, child_value in _extract_errors(value):
                    yield [key] + child_keys, child_value
            else:
                yield [key], value

    def extract_errors(data: dict[str | int, Any] | list[str]) -> dict[str, str]:
        return {"-".join(key): value for key, value in _extract_errors(data)}

    errors = errs[next(iter(errs))][0]

    if isinstance(errors, dict):
        error_message = {key: errors_to_list(value) for key, value in errs.items()}
    elif isinstance(errors, list):
        error_message = [errors_to_list(value) for value in errs]

    elif isinstance(errors, StreamBlockValidationError):
        json_data_errors = errors.as_json_data()
        error_messages = []
        error_message = ["An unknown error occurred"]
        if isinstance(json_data_errors["blockErrors"], dict):
            error_level = list(json_data_errors["blockErrors"].keys())[0]

            field_name = "Unknown Field"
            if "blockErrors" in json_data_errors["blockErrors"][error_level]:
                field_name = list(
                    json_data_errors["blockErrors"][error_level]["blockErrors"].keys()
                )[0]

                for val in json_data_errors["blockErrors"][error_level][
                    "blockErrors"
                ].values():
                    messages = list(extract_errors(val).values())
            else:
                messages = list(
                    json_data_errors["blockErrors"][error_level]["messages"]
                )

            error_messages.extend(messages)

            error_message = [f"{field_name} - {msg}" for msg in error_messages]

    elif isinstance(errors, ValidationError):
        field_name = list(errs.keys())[0]
        error_messages = errors.messages[0]
        error_message = [f"{field_name} - {error_messages}"]
    else:
        pass

    return error_message
