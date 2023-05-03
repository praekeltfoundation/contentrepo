import json

import responses
from django.test import TestCase

from home.whatsapp import create_whatsapp_template


class WhatsAppTests(TestCase):
    @responses.activate
    def test_create_whatsapp_template(self):
        data = {
            "category": "UTILITY",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }
        url = "http://whatsapp/graph/v3.3/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        create_whatsapp_template("Test-Template", "Test Body")

        request = responses.calls[0].request

        self.assertEquals(request.headers["Authorization"], "Bearer fake-access-token")
        self.assertEquals(request.body, json.dumps(data, indent=4))

    @responses.activate
    def test_create_whatsapp_template_with_buttons(self):
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
        url = "http://whatsapp/graph/v3.3/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        create_whatsapp_template(
            "Test-Template", "Test Body", ["Test button1", "test button2"]
        )

        request = responses.calls[0].request

        self.assertEquals(request.headers["Authorization"], "Bearer fake-access-token")
        self.assertEquals(request.body, json.dumps(data, indent=4))
