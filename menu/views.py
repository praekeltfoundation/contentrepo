from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer

from home.models import ContentPage, ContentPageTag


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def mainmenu(request):
    tag = request.GET.get("tag", None)
    start = int(request.GET.get("start", 1))

    pages = ContentPage.objects.all()
    if tag is not None:
        ids = []
        for t in ContentPageTag.objects.all():
            if t.tag.name == tag:
                ids.append(t.content_object_id)
        pages = pages.filter(id__in=ids)

    text = []
    ids = []
    titles = []
    for page in pages:
        text.append(f"\n*{page.title}*")

        for child in page.get_children():
            text.append(f"*{start}* - {child.title}")
            ids.append(str(child.id))
            titles.append(child.title)
            start += 1

    data = {
        "menu": "\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def submenu(request):
    parent_id = request.GET.get("parent")
    page = ContentPage.objects.get(id=parent_id)

    index = 1
    text = []
    ids = []
    titles = []
    for child in page.get_children():
        text.append(f"*{index}* - {child.title}")
        ids.append(str(child.id))
        titles.append(child.title)
        index += 1

    data = {
        "menu": "\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
    }
    return Response(data, status=status.HTTP_200_OK)


@api_view(("GET",))
@renderer_classes((JSONRenderer,))
def randommenu(request):
    tag = request.GET.get("tag", None)
    max = int(request.GET.get("max", 3))

    pages = ContentPage.objects.all()
    if tag is not None:
        ids = []
        for t in ContentPageTag.objects.all():
            if t.tag.name == tag:
                ids.append(t.content_object_id)
        pages = pages.filter(id__in=ids)

    index = 1
    text = []
    ids = []
    titles = []
    for page in pages.order_by("?"):
        text.append(f"*{index}* - {page.title}")
        ids.append(str(page.id))
        titles.append(page.title)
        index += 1

        if index > max:
            break

    data = {
        "menu": "\n".join(text),
        "ids": ",".join(ids),
        "titles": ",".join(titles),
    }
    return Response(data, status=status.HTTP_200_OK)
