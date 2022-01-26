import threading

from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from django.shortcuts import render
from django_filters import rest_framework as filters
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.pagination import CursorPagination

from .forms import UploadFileForm
from .models import ContentPage, ContentPageRating, PageView
from .serializers import PageViewSerializer, ContentPageRatingSerializer
from .utils import import_content_csv


class ContentUploadThread(threading.Thread):
    def __init__(self, file, splitlines, newline, purge, locale, **kwargs):
        self.file = file
        self.splitlines = splitlines
        self.purge = purge
        self.locale = locale
        self.newline = newline
        super(ContentUploadThread, self).__init__(**kwargs)

    def run(self):
        import_content_csv(
            self.file, self.splitlines, self.newline, self.purge, self.locale
        )


def upload_file(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data["purge"] == "True":
                ContentPage.objects.all().delete()
            ContentUploadThread(
                request.FILES["file"],
                form.cleaned_data["split_messages"],
                form.cleaned_data["newline"],
                form.cleaned_data["purge"],
                form.cleaned_data["locale"],
            ).start()
    else:
        form = UploadFileForm()
    return render(request, "upload.html", {"form": form})


def CursorPaginationFactory(field):
    """
    Returns a CursorPagination class with the field specified by field
    """

    class CustomCursorPagination(CursorPagination):
        ordering = field
        page_size = 1000

    name = "{}CursorPagination".format(field.capitalize())
    CustomCursorPagination.__name__ = name
    CustomCursorPagination.__qualname__ = name

    return CustomCursorPagination


class PageViewFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = PageView
        fields: list = []


class ContentPageRatingFilter(filters.FilterSet):
    timestamp_gt = filters.IsoDateTimeFilter(field_name="timestamp", lookup_expr="gt")

    class Meta:
        model = ContentPageRating
        fields: list = []


class GenericListViewset(GenericViewSet, ListModelMixin):
    page_size = 1000
    pagination_class = CursorPaginationFactory("timestamp")
    filter_backends = [filters.DjangoFilterBackend]
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)


class PageViewViewSet(GenericListViewset):
    queryset = PageView.objects.all()
    serializer_class = PageViewSerializer
    filterset_class = PageViewFilter


class ContentPageRatingViewSet(GenericListViewset, CreateModelMixin):
    queryset = ContentPageRating.objects.all()
    serializer_class = ContentPageRatingSerializer
    filterset_class = ContentPageRatingFilter

    def create(self, request, *args, **kwargs):
        if "page" in request.data:
            try:
                page = ContentPage.objects.get(id=request.data["page"])
                request.data["revision"] = page.get_latest_revision().id
            except ContentPage.DoesNotExist:
                raise ValidationError({"page": ["Page matching query does not exist."]})

        return super().create(request, *args, **kwargs)
