import json
import mimetypes
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from wagtail.images import get_image_model


def create_whatsapp_template(name, body, quick_replies=(), image_id=None):
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/v14.0/{settings.FB_BUSINESS_ID}/message_templates",
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

    if image_id:
        image_handle = upload_image(image_id)
        components.append(
            {
                "type": "HEADER",
                "format": "IMAGE",
                "example": {"header_handle": [image_handle]},
            }
        )

    data = {
        "category": "UTILITY",
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


def get_upload_session_id(image_id):
    url = urljoin(
        settings.WHATSAPP_API_URL,
        "graph/v14.0/app/uploads",
    )
    headers = {
        "Content-Type": "application/json",
    }

    img_obj = get_image_model().objects.get(id=image_id)
    mime_type = mimetypes.guess_type(img_obj.file.name)[0]
    file_size = img_obj.file.size
    file_path = img_obj.file
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
    upload_details = {
        "upload_session_id": response.json()["id"],
        "path_to_file": file_path,
    }

    response.raise_for_status()
    return upload_details


def upload_image(image_id):
    upload_details = get_upload_session_id(image_id)
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/{upload_details['upload_session_id']}",
    )

    headers = {
        "file_offset": "0",
    }

    response = requests.post(
        url,
        headers=headers,
        files={
            "file": upload_details["path_to_file"].open("rb"),
            "number": settings.FB_BUSINESS_ID,
            "access_token": settings.WHATSAPP_ACCESS_TOKEN,
        },
    )
    response.raise_for_status()
    return response.json()["h"]
