import json
import os
import mimetypes
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from wagtail.images import get_image_model


def create_whatsapp_template(name, body, quick_replies=(), image_id=None):
    print("Running create_whatsapp_template")
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
    print("Running get_upload_session_id")
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
    file_path = img_obj.file.path
    data = {
        "file_length": file_size,
        "file_type": mime_type,
        "access_token": settings.WHATSAPP_ACCESS_TOKEN,
        "number": settings.FB_BUSINESS_ID,
    }
    print("REQUEST DATA")
    print(data)

    response = requests.post(
        url,
        headers=headers,
        data=json.dumps(data, indent=4),
    )
    print("RESPONSE DATA")
    print(response.json())

    upload_details = {
        "upload_session_id": response.json()["id"],
        "upload_file": img_obj.file,
        "mime_type": mime_type,
    }

    response.raise_for_status()
    return upload_details


def upload_image(image_id):
    print("Running upload_image")
    upload_details = get_upload_session_id(image_id)
    url = urljoin(
        settings.WHATSAPP_API_URL,
        f"graph/{upload_details['upload_session_id']}",
    )

    headers = {
        "file_offset": "0",
    }
    file_path = upload_details['upload_file'].path
    print(f"FILEPATH = '{file_path}'")
    file_name = os.path.basename(file_path).split('/')[-1]
    print(f"FILENAME = '{file_name}'")
    files_data = {
        "file": ( file_name, upload_details['upload_file'].open("rb"), upload_details['mime_type']),
    }
    form_data =  {"number": settings.FB_BUSINESS_ID, "access_token": settings.WHATSAPP_ACCESS_TOKEN}
    print("FILES DATA")
    print(files_data)
    response = requests.post(
        url,
        headers=headers,
        files=files_data,
        data=form_data
    )
    print("RESPONSE TEXT FOR START UPLOAD")
    print(response.text)
    response.raise_for_status()
    return response.json()["h"]
