import random

from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from home.models import ContentPage, ContentPageTag

from .utils import get_bcm_page_ids


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def mainmenu(request):
    tags = request.GET.get("tags", "").split(",")
    start = int(request.GET.get("start", 1))
    bcm = bool(request.GET.get("bcm"))

    ids = []
    bcm_ids = []

    pages = ContentPage.objects.all().live()
    if tags:
        for t in ContentPageTag.objects.filter(tag__name__in=tags):
            ids.append(t.content_object_id)

        if bcm:
            bcm_ids = get_bcm_page_ids()
            ids = list(set(ids).intersection(bcm_ids))

        pages = pages.filter(id__in=ids)

    text = []
    ids = []
    titles = []
    for page in pages:
        text.append(f"\n*{page.title}*")

        for child in page.get_children().live():
            if bcm and child.id not in bcm_ids:
                continue

            text.append(f"*{start}* - {child.title}")
            ids.append(str(child.id))
            titles.append(child.title)
            start += 1

    data = {
        "menu": "\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
        "count": len(ids),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def submenu(request):
    parent_id = request.GET.get("parent")
    bcm = bool(request.GET.get("bcm"))

    page = ContentPage.objects.get(id=parent_id)

    bcm_ids = []
    if bcm:
        bcm_ids = get_bcm_page_ids()

    index = 1
    text = []
    ids = []
    titles = []
    for child in page.get_children().live():
        if bcm and child.id not in bcm_ids:
            continue

        text.append(f"*{index}* - {child.title}")
        ids.append(str(child.id))
        titles.append(child.title)
        index += 1

    whatsapp_body = ""
    if page.whatsapp_body._raw_data:
        whatsapp_body = page.whatsapp_body._raw_data[0]["value"]["message"]

    data = {
        "menu": "\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
        "count": len(ids),
        "blurb": whatsapp_body,
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def randommenu(request):
    tags = request.GET.get("tags", "").split(",")
    max = int(request.GET.get("max", 3))

    pages = ContentPage.objects.all().live()
    if tags:
        ids = []
        for t in ContentPageTag.objects.all():
            if t.tag.name in tags:
                ids.append(t.content_object_id)
        pages = pages.filter(id__in=ids)

    index = 1
    text = []
    ids = []
    titles = []
    for page in pages.order_by("?"):
        text.append(f"*{index}* - {page.whatsapp_title}")
        ids.append(str(page.id))
        titles.append(page.whatsapp_title)
        index += 1

        if index > max:
            break

    data = {
        "menu": "\n\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
        "count": len(ids),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def faqmenu(request):
    tag = request.GET.get("tag", "")
    viewed = request.GET.get("viewed", "").split(",")

    pages = []
    for i in range(1, 4):
        faq_tag = f"{tag}_faq{i}"

        if faq_tag in viewed:
            continue

        for t in ContentPageTag.objects.filter(tag__name__iexact=faq_tag):
            page = ContentPage.objects.get(id=t.content_object_id)

            pages.append(
                {
                    "order": i,
                    "title": page.whatsapp_title,
                }
            )

    return Response(pages, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def suggestedcontent(request):
    topics_viewed = request.GET.get("topics_viewed", "").split(",")

    suggested_pages = []
    for topic_id in topics_viewed:
        try:
            pages = (
                ContentPage.objects.get(id=topic_id)
                .get_descendants()
                .filter(numchild=0)
                .live()
            )
        except ContentPage.DoesNotExist:
            pages = None

        if pages:
            for page in (
                ContentPage.objects.get(id=topic_id)
                .get_descendants()
                .filter(numchild=0)
                .live()
            ):
                suggested_pages.append(page)

    data = {
        "results": [
            {"id": page.id, "title": page.title}
            for page in random.sample(suggested_pages, min(3, len(suggested_pages)))
        ]
    }

    return Response(data, status=status.HTTP_200_OK)
