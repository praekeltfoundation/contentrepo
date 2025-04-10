import json
from pathlib import Path

import pytest
import responses
from django.core.exceptions import ValidationError  # type: ignore
from django.core.files.images import ImageFile  # type: ignore
from django.db.utils import IntegrityError  # type: ignore
from pytest_django.fixtures import SettingsWrapper
from responses.matchers import multipart_matcher
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale  # type: ignore

from home.models import WhatsAppTemplate
from home.whatsapp import create_standalone_whatsapp_template


@pytest.mark.django_db
class TestStandaloneWhatsAppTemplates:
    # Standalone template tests below
    @responses.activate
    def test_create_standalone_whatsapp_template(self) -> None:
        """
        Creating a WhatsApp template results in a single HTTP call to the
        WhatsApp API containing the template data.
        """
        data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        locale = Locale.objects.get(language_code="en")
        create_standalone_whatsapp_template(
            "test-template", "Test Body", "UTILITY", locale=locale
        )

        request = responses.calls[0].request

        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_standalone_template_name(self) -> None:
        """
        Creating a WhatsApp template results in a single HTTP call to the
        WhatsApp API containing the template data.
        """
        data = {
            "category": "UTILITY",
            "name": "Test template 1",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        locale = Locale.objects.get(language_code="en")
        result_json = create_standalone_whatsapp_template(
            "Test template 1", "Test Body", "UTILITY", locale=locale
        )

        assert result_json == {"id": "123456789"}
        request = responses.calls[0].request
        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_standalone_whatsapp_template_with_example_values(self) -> None:
        """
        When we create a WhatsApp template with example values, the examples
        are included in the HTTP request's template body component.
        """
        data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [
                {
                    "type": "BODY",
                    "text": "Hi {{1}}. You are testing as a {{2}}",
                    "example": {
                        "body_text": [
                            [
                                "Fritz",
                                "beta tester",
                            ]
                        ]
                    },
                },
            ],
        }
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        locale = Locale.objects.get(language_code="en")
        create_standalone_whatsapp_template(
            "test-template",
            "Hi {{1}}. You are testing as a {{2}}",
            "UTILITY",
            example_values=["Fritz", "beta tester"],
            locale=locale,
        )

        request = responses.calls[0].request
        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_match_num_example_vars_and_placeholders(
        self, settings: SettingsWrapper
    ) -> None:
        with pytest.raises(ValidationError) as err_info:
            wat = WhatsAppTemplate(
                name="wa_title",
                message="Test WhatsApp Message with 1 valid {{1}} and one malformed var here {{2}}",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[
                    ("example_values", "Ev1"),
                ],
            )
            wat.save()
            wat.save_revision()

        assert err_info.value.message_dict == {
            "message": [
                "Mismatch in number of placeholders and example values. Found 2 placeholder(s) and 1 example values."
            ],
        }

    @responses.activate
    def test_invalid_placeholders(self, settings: SettingsWrapper) -> None:
        with pytest.raises(ValidationError) as err_info:
            wat = WhatsAppTemplate(
                name="wa_title",
                message="Test WhatsApp Message with 1 valid {{name}} ",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
                example_values=[
                    ("example_values", "Ev1"),
                ],
            )
            wat.save()
            wat.save_revision()

        assert err_info.value.message_dict == {
            "message": [
                "Please provide numeric variables only. You provided ['name']."
            ],
        }

    @responses.activate
    def test_no_single_brace_variable_placeholders(
        self, settings: SettingsWrapper
    ) -> None:
        """
        Templates should not contain any single braces with one or more chars inside
        """
        with pytest.raises(ValidationError) as err_info:
            wat = WhatsAppTemplate(
                name="wa_title",
                message="Test WhatsApp Message 1 {1} and a broken var here",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
            )
            wat.save()
            wat.save_revision()

        assert err_info.value.message_dict == {
            "message": [
                "Please provide variables with valid double braces. You provided single braces ['1']."
            ],
        }

    @responses.activate
    def test_create_standalone_whatsapp_template_with_buttons(self) -> None:
        """
        When we create a WhatsApp template with quick-reply buttons, the
        template data includes a buttons component that contains the buttons.
        """
        data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [
                {"type": "BODY", "text": "Test Body"},
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {"type": "QUICK_REPLY", "text": "Test button1"},
                        {"type": "QUICK_REPLY", "text": "test button2"},
                    ],
                },
            ],
        }
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        locale = Locale.objects.get(language_code="en")
        create_standalone_whatsapp_template(
            "test-template",
            "Test Body",
            "UTILITY",
            quick_replies=["Test button1", "test button2"],
            locale=locale,
        )

        request = responses.calls[0].request

        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_standalone_whatsapp_template_with_image(
        self, tmp_path: Path, settings: SettingsWrapper
    ) -> None:
        """
        When we create a WhatsApp template with an image, the image must be
        uploaded separately:
         * A POST containing image metadata that returns a sesson id.
         * A POST containing the session id and the image data that returns an
           image handle.
         * A POST containing the template data, with the image handle in a
           header/image component.
        """
        settings.MEDIA_ROOT = tmp_path
        img_name = "test.jpeg"
        img_path = Path("home/tests/test_static") / img_name

        read_file = img_path.open("rb")
        saved_image = Image(
            title=img_name,
            file=ImageFile(read_file, name=img_name),
        )
        saved_file = saved_image.file
        saved_image.save()
        read_file.seek(0)

        mock_session_id = "TEST_SESSION_ID"
        mock_session_url = "http://whatsapp/graph/v14.0/app/uploads"
        responses.add(responses.POST, mock_session_url, json={"id": mock_session_id})

        mock_start_upload_url = f"http://whatsapp/graph/{mock_session_id}"
        mock_image_handle = "TEST_IMAGE_HANDLE"
        mock_files_data = {
            "file": (saved_file),
        }
        mock_form_data = {
            "number": settings.FB_BUSINESS_ID,
            "access_token": settings.WHATSAPP_ACCESS_TOKEN,
        }
        responses.add(
            responses.POST,
            mock_start_upload_url,
            json={"h": mock_image_handle},
            match=[multipart_matcher(mock_files_data, data=mock_form_data)],
        )
        template_url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, template_url, json={})

        locale = Locale.objects.get(language_code="en")
        create_standalone_whatsapp_template(
            "test-template",
            "Test Body",
            "UTILITY",
            image_obj=saved_image,
            locale=locale,
        )

        mock_get_session_data = {
            "file_length": 631,
            "file_type": "image/jpeg",
            "access_token": "fake-access-token",
            "number": "27121231234",
        }
        gsid_req = responses.calls[0].request
        assert json.loads(gsid_req.body) == mock_get_session_data

        ct_req = responses.calls[2].request
        mock_create_template_data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [
                {
                    "type": "HEADER",
                    "format": "IMAGE",
                    "example": {"header_handle": [mock_image_handle]},
                },
                {"type": "BODY", "text": "Test Body"},
            ],
        }

        assert ct_req.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(ct_req.body) == mock_create_template_data

    @responses.activate
    def test_create_standalone_whatsapp_template_with_language(self) -> None:
        """
        When we create a WhatsApp template, the language is converted to the
        appropriate WhatsApp language code.
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        # The default English locale gives us a language of "en_US".
        # FIXME: Should this be "en" instead?
        # Fritz -> Have talked to Jeremy about this.  We feel like we need to understand the locale mappings/translations between the various parts of this solution better.  We feel this should be a separate ticket
        en = Locale.objects.get(language_code="en")
        create_standalone_whatsapp_template(
            "test-template", "Test Body", "UTILITY", locale=en
        )
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }

        # WhatsApp doesn't support Portuguese without a country code, so we
        # pick "pt_PT" rather than "pt_BR".
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        create_standalone_whatsapp_template(
            "test-pt", "Corpo de Teste", "UTILITY", locale=pt
        )
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt",
            "language": "pt_PT",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }

        # If we specifically want Brazillian Portuguese, we can use a locale
        # specifically for that.
        ptbr, _created = Locale.objects.get_or_create(language_code="pt_BR")
        create_standalone_whatsapp_template(
            "test-pt-br", "Corpo de Teste", "UTILITY", locale=ptbr
        )
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt-br",
            "language": "pt_BR",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }

    @responses.activate
    def test_create_duplicate_name_and_locale_template(self) -> None:
        """
        We cannot create templates with a combination of name & locale that is not unique
        """
        with pytest.raises(IntegrityError) as err_info:
            wat1 = WhatsAppTemplate(
                name="Test Template Name",
                message="Test WhatsApp Message 1",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
            )
            wat1.save()
            wat1.save_revision()

            wat2 = WhatsAppTemplate(
                name="Test Template Name",
                message="Test WhatsApp Message 2",
                category="UTILITY",
                locale=Locale.objects.get(language_code="en"),
            )
            wat2.save()
            wat2.save_revision()

        assert err_info.type is IntegrityError
