import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import responses
from django.core.files.images import ImageFile  # type: ignore
from pytest_django.fixtures import SettingsWrapper
from responses.matchers import multipart_matcher
from wagtail.images.models import Image  # type: ignore
from wagtail.models import Locale  # type: ignore

from home.models import WhatsAppTemplate
from home.whatsapp import (
    TemplateSubmissionClientException,
    TemplateSubmissionServerException,
    create_whatsapp_template,
    submit_to_meta_action,
)


@pytest.mark.django_db
class TestWhatsApp:
    @responses.activate
    def test_create_whatsapp_template(self, settings: SettingsWrapper) -> None:
        """
        Creating a WhatsApp template results in a single HTTP call to the
        WhatsApp API containing the template data.
        """
        settings.WHATSAPP_CREATE_TEMPLATES = True
        data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }
        url = "http://whatsapp/graph/v14.0/27121231234/message_templates"
        responses.add(responses.POST, url, json={"id": "123456789"})

        locale = Locale.objects.get(language_code="en")
        create_whatsapp_template(
            name="test-template", body="Test Body", category="UTILITY", locale=locale
        )

        request = responses.calls[0].request

        assert request.headers["Authorization"] == "Bearer fake-access-token"
        assert json.loads(request.body) == data

    @responses.activate
    def test_create_whatsapp_template_with_example_values(
        self, settings: SettingsWrapper
    ) -> None:
        """
        When we create a WhatsApp template with example values, the examples
        are included in the HTTP request's template body component.
        """
        settings.WHATSAPP_CREATE_TEMPLATES = True
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
        create_whatsapp_template(
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
    def test_create_whatsapp_template_with_buttons(
        self, settings: SettingsWrapper
    ) -> None:
        """
        When we create a WhatsApp template with quick-reply buttons, the
        template data includes a buttons component that contains the buttons.
        """
        settings.WHATSAPP_CREATE_TEMPLATES = True
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
        responses.add(responses.POST, url, json={"id": "123456789"})

        locale = Locale.objects.get(language_code="en")
        create_whatsapp_template(
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
        settings.WHATSAPP_CREATE_TEMPLATES = True
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
        create_whatsapp_template(
            "test-template",
            "Test Body",
            "UTILITY",
            image_id=saved_image.id,
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
        # Fritz -> Have talked to Jeremy about this.  We feel like we need to understand the locale mappings/translations between the various parts of this solution better.  We feel this should be a separate ticket
        en = Locale.objects.get(language_code="en")
        create_whatsapp_template("test-template", "Test Body", "UTILITY", locale=en)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }

        # WhatsApp doesn't support Portuguese without a country code, so we
        # pick "pt_PT" rather than "pt_BR".
        pt, _created = Locale.objects.get_or_create(language_code="pt")
        create_whatsapp_template("test-pt", "Corpo de Teste", "UTILITY", locale=pt)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt",
            "language": "pt_PT",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }

        # If we specifically want Brazillian Portuguese, we can use a locale
        # specifically for that.
        ptbr, _created = Locale.objects.get_or_create(language_code="pt_BR")
        create_whatsapp_template("test-pt-br", "Corpo de Teste", "UTILITY", locale=ptbr)
        assert json.loads(responses.calls[-1].request.body) == {
            "category": "UTILITY",
            "name": "test-pt-br",
            "language": "pt_BR",
            "components": [{"type": "BODY", "text": "Corpo de Teste"}],
        }


class DummySubmissionStatus:
    SUBMITTED = "SUBMITTED"
    FAILED = "FAILED"


class DummyRevisionObj:
    def __init__(self) -> None:
        self.message = "msg"
        self.category = "UTILITY"
        self.locale = mock.Mock()
        self.buttons = mock.Mock(raw_data=[{"value": {"title": "Button1"}}])
        self.image = None
        self.example_values = mock.Mock(raw_data=[{"value": "val1"}])
        self.submission_name = None
        self.submission_status = None
        self.submission_result: str = ""
        self.SubmissionStatus = DummySubmissionStatus

    def create_whatsapp_template_name(self) -> str:
        return "template_123"

    def save(self) -> None:
        pass


class DummyRevision:
    def as_object(self) -> DummyRevisionObj:
        return DummyRevisionObj()


class DummyModel:
    def __init__(self, revision: DummyRevision | None = None) -> None:
        self._revision = revision
        self.message = "msg"
        self.category = "UTILITY"
        self.locale = mock.Mock()
        self.buttons = mock.Mock(raw_data=[{"value": {"title": "Button1"}}])
        self.image = None
        self.example_values = mock.Mock(raw_data=[{"value": "val1"}])
        self.submission_name = None
        self.submission_status = None
        self.submission_result: str = ""
        self.SubmissionStatus = DummySubmissionStatus

    def get_latest_revision(self) -> DummyRevision | None:
        return self._revision

    def create_whatsapp_template_name(self) -> str:
        return "template_123"

    def save(self) -> None:
        pass


@pytest.mark.django_db
def test_submit_to_meta_action_success(monkeypatch: pytest.MonkeyPatch) -> None:
    model = DummyModel()

    def fake_create_standalone_whatsapp_template(
        **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        return {"id": "fakeid123"}

    monkeypatch.setattr(
        "home.whatsapp.create_standalone_whatsapp_template",
        fake_create_standalone_whatsapp_template,
    )

    submit_to_meta_action(model)
    assert model.submission_status == DummySubmissionStatus.SUBMITTED
    assert model.submission_result.startswith("Success! Template ID = ")


@pytest.mark.django_db
def test_submit_to_meta_action_server_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = DummyModel()

    def fake_create_standalone_whatsapp_template(
        **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        raise TemplateSubmissionServerException("server error")

    monkeypatch.setattr(
        "home.whatsapp.create_standalone_whatsapp_template",
        fake_create_standalone_whatsapp_template,
    )

    submit_to_meta_action(model)
    assert model.submission_status == DummySubmissionStatus.FAILED
    assert "Internal Server Error" in model.submission_result


@pytest.mark.django_db
def test_submit_to_meta_action_client_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = DummyModel()

    def fake_create_standalone_whatsapp_template(
        **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        raise TemplateSubmissionClientException("client error")

    monkeypatch.setattr(
        "home.whatsapp.create_standalone_whatsapp_template",
        fake_create_standalone_whatsapp_template,
    )

    submit_to_meta_action(model)
    assert model.submission_status == DummySubmissionStatus.FAILED
    assert model.submission_result == "Error! client error"


@pytest.mark.django_db
def test_submit_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Test that submitting a WhatsAppTemplate Revision doesn't overwrite the live template
    """
    wat = WhatsAppTemplate(
        name="valid-named-variables",
        message="This is a message with 2 valid named vars {{1}} and {{2}}",
        category="UTILITY",
        locale=Locale.objects.get(language_code="en"),
        example_values=[("example_values", "Ev1"), ("example_values", "Ev2")],
    )
    wat.save()
    wat.save_revision().publish()
    rev1 = wat.get_latest_revision().as_object()
    latest_revision = wat.get_latest_revision().as_object()
    assert rev1.category == "UTILITY"
    latest_revision.category = "MARKETING"
    latest_revision.save_revision()

    assert wat.category == rev1.category == "UTILITY"

    rev2 = wat.revisions.order_by("-created_at").first()
    pk = rev2.id
    rev_object = rev2.as_object()
    assert rev_object.category == "MARKETING"

    def fake_create_standalone_whatsapp_template(
        **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        return {"id": "fakeid123"}

    monkeypatch.setattr(
        "home.whatsapp.create_standalone_whatsapp_template",
        fake_create_standalone_whatsapp_template,
    )

    submit_to_meta_action(rev2)

    rev3 = wat.revisions.order_by("-created_at").first()
    rev3_obj = rev3.as_object()
    assert rev3_obj.submission_name == f"valid-named-variables_{pk}"
    assert rev3_obj.submission_status == DummySubmissionStatus.SUBMITTED
    assert rev3_obj.submission_result.startswith("Success! Template ID = ")

    wat = WhatsAppTemplate.objects.filter(live=True).first()
    latest_rev = wat.revisions.order_by("-created_at").first().as_object()
    assert wat.category == rev1.category
    assert wat.category != latest_rev.category
