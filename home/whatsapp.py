import json
import logging
import mimetypes
import re
from collections.abc import Iterable
from enum import Enum
from typing import Any
from urllib.parse import urljoin

import pyparsing as pp
import requests
from django.conf import settings  # type: ignore
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale  # type: ignore

from .constants import WHATSAPP_LANGUAGE_MAPPING

logger = logging.getLogger(__name__)


class WhatsAppLanguage(Enum):
    """
    These are the languages supported by WhatsApp message templates as per
    https://developers.facebook.com/docs/whatsapp/api/messages/message-templates#supported-languages
    (Fetched 2023-11-16)
    """

    af = "af"  # Afrikaans
    sq = "sq"  # Albanian
    ar = "ar"  # Arabic
    az = "az"  # Azerbaijani
    bn = "bn"  # Bengali
    bg = "bg"  # Bulgarian
    ca = "ca"  # Catalan
    zh_CN = "zh_CN"  # Chinese (CHN)
    zh_HK = "zh_HK"  # Chinese (HKG)
    zh_TW = "zh_TW"  # Chinese (TAI)
    hr = "hr"  # Croatian
    cs = "cs"  # Czech
    da = "da"  # Danish
    nl = "nl"  # Dutch
    en = "en"  # English
    en_GB = "en_GB"  # English (UK)
    en_US = "en_US"  # English (US)
    et = "et"  # Estonian
    fil = "fil"  # Filipino
    fi = "fi"  # Finnish
    fr = "fr"  # French
    ka = "ka"  # Georgian
    de = "de"  # German
    el = "el"  # Greek
    gu = "gu"  # Gujarati
    ha = "ha"  # Hausa
    he = "he"  # Hebrew
    hi = "hi"  # Hindi
    hu = "hu"  # Hungarian
    id = "id"  # Indonesian
    ga = "ga"  # Irish
    it = "it"  # Italian
    ja = "ja"  # Japanese
    kn = "kn"  # Kannada
    kk = "kk"  # Kazakh
    rw_RW = "rw_RW"  # Kinyarwanda
    ko = "ko"  # Korean
    ky_KG = "ky_KG"  # Kyrgyz (Kyrgyzstan)
    lo = "lo"  # Lao
    lv = "lv"  # Latvian
    lt = "lt"  # Lithuanian
    mk = "mk"  # Macedonian
    ms = "ms"  # Malay
    ml = "ml"  # Malayalam
    mr = "mr"  # Marathi
    nb = "nb"  # Norwegian
    fa = "fa"  # Persian
    pl = "pl"  # Polish
    pt_BR = "pt_BR"  # Portuguese (BR)
    pt_PT = "pt_PT"  # Portuguese (POR)
    pa = "pa"  # Punjabi
    ro = "ro"  # Romanian
    ru = "ru"  # Russian
    sr = "sr"  # Serbian
    sk = "sk"  # Slovak
    sl = "sl"  # Slovenian
    es = "es"  # Spanish
    es_AR = "es_AR"  # Spanish (ARG)
    es_ES = "es_ES"  # Spanish (SPA)
    es_MX = "es_MX"  # Spanish (MEX)
    sw = "sw"  # Swahili
    sv = "sv"  # Swedish
    ta = "ta"  # Tamil
    te = "te"  # Telugu
    th = "th"  # Thai
    tr = "tr"  # Turkish
    uk = "uk"  # Ukrainian
    ur = "ur"  # Urdu
    uz = "uz"  # Uzbek
    vi = "vi"  # Vietnamese
    zu = "zu"  # Zulu

    @classmethod
    def from_locale(cls, locale: Locale) -> "WhatsAppLanguage":
        lc = WHATSAPP_LANGUAGE_MAPPING.get(locale.language_code, locale.language_code)
        # This will raise KeyError for unsupported languages.
        return cls[lc]


def get_upload_session_id(image_obj: Image) -> dict[str, Any]:
    """
    Gets a session ID from the Turn API, to use with an image upload
    """
    url = urljoin(
        settings.WHATSAPP_API_URL,
        "graph/v14.0/app/uploads",
    )
    headers = {
        "Content-Type": "application/json",
    }
    mime_type = mimetypes.guess_type(image_obj.file.name)[0]
    file_size = image_obj.file.size

    data = {
        "file_length": file_size,
        "file_type": mime_type,
        "access_token": settings.WHATSAPP_ACCESS_TOKEN,
        "number": settings.FB_BUSINESS_ID,
    }
    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data, indent=4),
    )
    response.raise_for_status()
    upload_details = {
        "upload_session_id": response.json()["id"],
        "upload_file": image_obj.file,
    }

    return upload_details


def upload_image(image_obj: Image) -> str:
    """
    Uploads an image to the Turn API, and returns an image handle reference to use in the template
    """
    upload_details = get_upload_session_id(image_obj)
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/{upload_details['upload_session_id']}",
    )

    headers = {
        "file_offset": "0",
    }
    files_data = {
        "file": (upload_details["upload_file"]).open("rb"),
    }
    form_data = {
        "number": settings.FB_BUSINESS_ID,
        "access_token": settings.WHATSAPP_ACCESS_TOKEN,
    }
    response = requests.post(url=url, headers=headers, files=files_data, data=form_data)
    response.raise_for_status()
    return response.json()["h"]


def create_whatsapp_template_image(image_obj: Image) -> dict[str, Any]:
    image_handle = upload_image(image_obj)

    return {
        "type": "HEADER",
        "format": "IMAGE",
        "example": {"header_handle": [image_handle]},
    }


def submit_whatsapp_template(
    name: str,
    category: str,
    locale: Locale,
    components: list[dict[str, Any]],
) -> dict[str, str]:
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/v14.0/{settings.FB_BUSINESS_ID}/message_templates",
    )
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "category": category,
        "name": name,
        "language": WhatsAppLanguage.from_locale(locale).value,
        "components": components,
    }
    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data, indent=4),
    )

    if response.ok:
        return response.json()

    logger.warning(f"Error submitting template {response.content!r}")
    try:
        err_msg = response.json()["error"]["error_user_msg"]
    except Exception:
        raise TemplateSubmissionServerException(
            f"Couldn't parse error response: {response.content!r}"
        )

    raise TemplateSubmissionClientException(err_msg)


class TemplateSubmissionServerException(Exception):
    def __init__(self, response_content: str):
        self.response_content = response_content
        super().__init__(f"{response_content}")


class TemplateSubmissionClientException(Exception):
    def __init__(self, error_msg: str):
        self.error_msg = error_msg
        super().__init__(f"Error! {error_msg}")


###### ALL CODE ABOVE THIS LINE IS SHARED BY THE OLD CONTENTPAGE EMBEDDED TEMPLATES, AS WELL AS THE NEW STANDALONE TEMPLATES ######

###### OLD CONTENTPAGE EMBEDDED TEMPLATE CODE BELOW ######


def create_whatsapp_template(
    name: str,
    body: str,
    category: str,
    locale: Locale,
    quick_replies: Iterable[str] = (),
    image_id: int | None = None,
    example_values: Iterable[str] | None = None,
) -> None:
    """
    Create a WhatsApp template through the WhatsApp Business API.

    """

    components = create_whatsapp_template_submission(
        body, quick_replies, example_values
    )
    if image_id is not None:
        image_obj = Image.objects.get(id=image_id)
        components.append(create_whatsapp_template_image(image_obj))
    submit_whatsapp_template(
        name=name, category=category, locale=locale, components=components
    )


def create_whatsapp_template_submission(
    body_text: str,
    quick_replies: Iterable[str] = (),
    example_values: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Create the body and buttons components of a WhatsApp template submission
    request, but not the images because those need to be uploaded separately.
    """

    # body: dict[str, Any] = {"type": "BODY", "text": body_text}

    components: list[dict[str, Any]] = []

    if example_values:
        components.append(
            {
                "type": "BODY",
                "text": body_text,
                "example": {
                    "body_text": [example_values],
                },
            }
        )
    else:
        components.append({"type": "BODY", "text": body_text})

    if quick_replies:
        buttons = []
        for button in quick_replies:
            buttons.append({"type": "QUICK_REPLY", "text": button})
        components.append({"type": "BUTTONS", "buttons": buttons})

    return components


###### OLD CONTENTPAGE EMBEDDED TEMPLATE CODE ABOVE ######
###### NEW STANDALONE TEMPLATE CODE BELOW ######


def create_standalone_template_body_components(
    message: str,
    quick_replies: Iterable[str] = (),
    example_values: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Create the body and buttons components of a WhatsApp template submission
    request, but not the images because those need to be uploaded separately.
    """

    # body: dict[str, Any] = {"type": "BODY", "text": body_text}

    components: list[dict[str, Any]] = []

    if example_values:
        components.append(
            {
                "type": "BODY",
                "text": message,
                "example": {
                    "body_text": [example_values],
                },
            }
        )
    else:
        components.append({"type": "BODY", "text": message})

    if quick_replies:
        buttons = []
        for button in quick_replies:
            buttons.append({"type": "QUICK_REPLY", "text": button})
        components.append({"type": "BUTTONS", "buttons": buttons})

    return components


def create_standalone_template_header_components(
    image_obj: Image | None = None,
) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    image_handle = upload_image(image_obj)
    components.append(
        {
            "type": "HEADER",
            "format": "IMAGE",
            "example": {"header_handle": [image_handle]},
        }
    )
    return components


def create_standalone_whatsapp_template(
    name: str,
    message: str,
    category: str,
    locale: Locale,
    quick_replies: Iterable[str] = (),
    image_obj: Image | None = None,
    example_values: Iterable[str] | None = None,
) -> dict[str, str]:
    """
    Create a WhatsApp template through the WhatsApp Business API.

    """

    components: list[dict[str, Any]] = []

    if image_obj:
        components.extend(
            create_standalone_template_header_components(image_obj=image_obj)
        )

    components.extend(
        create_standalone_template_body_components(
            message=message,
            quick_replies=quick_replies,
            example_values=example_values,
        )
    )

    return submit_whatsapp_template(name, category, locale, components)


# Define parser grammar here
vstart = pp.Literal("{{").suppress()
vend = pp.Literal("}}").suppress()
nonvar = pp.CharsNotIn("{}").suppress()
if settings.WHATSAPP_ALLOW_NAMED_VARIABLES:
    variable = (vstart + pp.Word(pp.alphanums + "_") + vend).set_name("variable")
else:
    variable = (vstart + pp.Word(pp.nums) + vend).set_name("variable")
template_body = pp.OneOrMore(variable | nonvar)


class TemplateVariableError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def validate_positional_variables(variables: list[str]):
    # Check what the expected positional variables would be
    expected_positional_variable_values = [str(j + 1) for j in range(len(variables))]
    if variables != expected_positional_variable_values:
        raise TemplateVariableError(
            f'Positional variables must increase sequentially, starting at 1. You provided "{variables}"'
        )


def validate_template_variables(body: str) -> list[str]:
    variables = []
    try:
        variables = list(template_body.parse_string(body, parse_all=True))

    except pp.ParseException as pe:
        closing_braces = body.find("}}", pe.loc)
        if closing_braces > -1:
            var_name = body[pe.loc + 2 : closing_braces]

            if settings.WHATSAPP_ALLOW_NAMED_VARIABLES:
                if not re.match("^[a-zA-Z0-9_]+$", var_name):
                    raise TemplateVariableError(
                        f"ParseException: Named variable can only contain alphanumberic and underscore characters. You provided '{var_name}'"
                    )
                else:
                    raise TemplateVariableError(
                        f"ParseException: There was a problem parsing the variable starting at character {pe.loc}"
                    )
            else:
                raise TemplateVariableError(
                    f"ParseException: Please provide numeric variables only. You provided a non-numeric variable name '{var_name}'."
                )

        else:
            raise TemplateVariableError(
                f"ParseException: Unable to parse the variable starting at character {pe.loc}"
            )

    if not variables:
        return []

    # If all the variables are ints, validate as positional variables
    if all(
        isinstance(var, int) or isinstance(var, str) and var.isdigit()
        for var in variables
    ):
        validate_positional_variables(variables)

    return variables
