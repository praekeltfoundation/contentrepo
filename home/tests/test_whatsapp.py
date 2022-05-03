import json
import responses
from django.test import TestCase

from home.whatsapp import create_whatsapp_template


class WhatsAppTests(TestCase):
    @responses.activate
    def test_create_whatsapp_template(self):
        data = {
            "category": "ACCOUNT_UPDATE",
            "name": "test-template",
            "language": "en_US",
            "components": [{"type": "BODY", "text": "Test Body"}],
        }
        url = f"http://whatsapp/graph/v3.3/27121231234/message_templates"
        responses.add(responses.POST, url, json={})

        create_whatsapp_template("test-template", "Test Body")

        request = responses.calls[0].request

        self.assertEquals(request.headers["Authorization"], "Bearer fake-access-token")
        self.assertEquals(request.body, json.dumps(data, indent=4))
