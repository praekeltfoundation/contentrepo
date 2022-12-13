import json
from urllib.parse import urljoin

import requests
from django.conf import settings


def create_whatsapp_template(name, body, quick_replies=[]):
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/v3.3/{settings.FB_BUSINESS_ID}/message_templates",
    )
    headers = {
        "Authorization": "Bearer {}".format(settings.WHATSAPP_ACCESS_TOKEN),
        "Content-Type": "application/json",
    }

    components = [{"type": "BODY", "text": body}]
    if quick_replies:
        buttons = []
        for button in quick_replies:
            buttons.append({"type": "QUICK_REPLY", "text": button})
        components.append({"type": "BUTTONS", "buttons": buttons})

    data = {
        "category": "ACCOUNT_UPDATE",
        "name": name.lower(),
        "language": "en_US",
        "components": components,
    }

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data, indent=4),
    )
    response.raise_for_status()
