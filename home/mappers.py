from wagtail_content_import.mappers.converters import (  # isort:skip
    ImageConverter,
    RichTextConverter,
)
from wagtail_content_import.mappers.streamfield import StreamFieldMapper


class ContentMapper(StreamFieldMapper):
    html = RichTextConverter("paragraph")
    image = ImageConverter("image")
