import json
import requests

from urllib.parse import urljoin
from django.conf import settings


def create_whatsapp_template(name, body):
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/v3.3/{settings.FB_BUSINESS_ID}/message_templates",
    )
    headers = {
        "Authorization": "Bearer {}".format(settings.WHATSAPP_ACCESS_TOKEN),
        "Content-Type": "application/json",
    }
    data = {
        "category": "ACCOUNT_UPDATE",
        "name": name,
        "language": "en_US",
        "components": [{"type": "BODY", "text": body}],
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data, indent=4),
    )
    response.raise_for_status()
