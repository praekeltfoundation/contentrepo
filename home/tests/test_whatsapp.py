import json
from pathlib import Path

import pytest
import responses
from django.core.files.images import ImageFile  # type: ignore
from pytest_django.fixtures import SettingsWrapper
from responses.matchers import multipart_matcher
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale  # type: ignore

from home.whatsapp import create_whatsapp_template


@pytest.mark.django_db
class TestWhatsApp:
    @responses.activate
    def test_create_whatsapp_template(self) -> None:
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

        create_whatsapp_template("test-template", "Test Body", "UTILITY")

        request = responses.calls[0].request

        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_whatsapp_template_with_example_values(self) -> None:
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
        responses.add(responses.POST, url, json={})

        create_whatsapp_template(
            "test-template",
            "Hi {{1}}. You are testing as a {{2}}",
            "UTILITY",
            example_values=["Fritz", "beta tester"],
        )

        request = responses.calls[0].request
        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_whatsapp_template_with_buttons(self) -> None:
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

        create_whatsapp_template(
            "test-template",
            "Test Body",
            "UTILITY",
            quick_replies=["Test button1", "test button2"],
        )

        request = responses.calls[0].request

        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_whatsapp_template_with_image(
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

        create_whatsapp_template(
            "test-template", "Test Body", "UTILITY", image_id=saved_image.id
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
                {"type": "BODY", "text": "Test Body"},
                {
                    "type": "HEADER",
                    "format": "IMAGE",
                    "example": {"header_handle": [mock_image_handle]},
                },
            ],
        }

        assert ct_req.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(ct_req.body) == mock_create_template_data

    @responses.activate
    def test_create_whatsapp_template_with_language(self) -> None:
        """
        When we create a WhatsApp template, the language is converted to the
        appropriate WhatsApp language code.
        """
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        # The default English locale gives us a language of "en_US".
        # FIXME: Should this be "en" instead?
        en = Locale.objects.get(language_code="en")
        create_whatsapp_template("Test-Template", "Test Body", "UTILITY", locale=en)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }

        # WhatsApp doesn't support Portuguese without a country code, so we
        # pick "pt_PT" rather than "pt_BR".
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        create_whatsapp_template("Test-pt", "Corpo de Teste", "UTILITY", locale=pt)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt",
            "language": "pt_PT",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }

        # If we specifically want Brazillian Portuguese, we can use a locale
        # specifically for that.
        ptbr, _created = Locale.objects.get_or_create(language_code="pt_BR")
        create_whatsapp_template("Test-pt-BR", "Corpo de Teste", "UTILITY", locale=ptbr)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt-br",
            "language": "pt_BR",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }
