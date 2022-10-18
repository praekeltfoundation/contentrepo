import json
import threading

import django_filters
from django.db.models import Count, F
from django.db.models.functions import TruncMonth
from django.forms import MultiWidget
from django.forms.widgets import NumberInput
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views import View
from django_filters import rest_framework as filters
from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.pagination import CursorPagination
from rest_framework.viewsets import GenericViewSet
from wagtail.admin.filters import WagtailFilterSet
from wagtail.admin.views.reports import PageReportView, ReportView
from wagtail.admin.widgets import AdminDateInput
from wagtail.contrib.modeladmin.views import IndexView

from .forms import UploadFileForm
from .mixins import SpreadsheetExportMixin
from .models import ContentPage, ContentPageRating, PageView
from .serializers import ContentPageRatingSerializer, PageViewSerializer
from .utils import import_content


class CustomIndexView(SpreadsheetExportMixin, IndexView):
    pass


class StaleContentReportFilterSet(WagtailFilterSet):
    last_published_at = django_filters.DateTimeFilter(
        label=_("Last published before"), lookup_expr="lte", widget=AdminDateInput
    )
    view_counter = django_filters.NumberFilter(
        label=_("View count"), lookup_expr="lte", widget=NumberInput
    )
    o = django_filters.OrderingFilter(
        # tuple-mapping retains order
        fields=(
            ("view_counter", "View Count"),
            ("last_published_at", "Latest published"),
        ),
    )

    class Meta:
        model = ContentPage
        fields = ["live", "last_published_at"]


class PageViewFilterSet(WagtailFilterSet):
    platform_choices = [
        ("web", "Web"),
        ("whatsapp", "Whatsapp"),
        ("messenger", "Messenger"),
        ("viber", "Viber"),
    ]
    timestamp = django_filters.DateTimeFromToRangeFilter(
        label=_("Date Range"),
        widget=MultiWidget(widgets=[AdminDateInput, AdminDateInput]),
    )
    platform = django_filters.ChoiceFilter(choices=platform_choices)
    page = django_filters.ModelChoiceFilter(queryset=ContentPage.objects)

    class Meta:
        model = PageView
        fields = ["timestamp", "platform", "page"]


class ContentPageReportView(ReportView):
    header_icon = "time"
    title = "Content Pages"
    template_name = "reports/stale_content_report.html"
    filterset_class = StaleContentReportFilterSet
    list_export = PageReportView.list_export + ["last_published_at", "view_counter"]
    export_headings = dict(
        last_published_at="Last Published",
        view_counter="View Count",
        **PageReportView.export_headings,
    )

    def get_queryset(self):
        return ContentPage.objects.annotate(view_counter=Count("views")).all()


class PageViewReportView(ReportView):
    header_icon = "doc-empty"
    title = "Page views"
    template_name = "reports/page_view_report.html"
    filterset_class = PageViewFilterSet

    def get_queryset(self):
        return PageView.objects.all()

    def get_filtered_queryset(self):
        return self.filter_queryset(self.get_queryset())

    def get_views_data(self):
        view_per_month = list(
            self.get_filtered_queryset()[1]
            .annotate(month=TruncMonth("timestamp"))
            .values("month")
            .annotate(x=F("month"), y=Count("page_id"))
            .values("x", "y")
        )
        view_per_month.sort(key=lambda item: item["x"])
        labels = [item["x"].date() for item in view_per_month]
        return {"data": view_per_month, "labels": labels}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_view_data"] = json.dumps(
            self.get_views_data(), indent=4, sort_keys=True, default=str
        )
        return context


class ContentUploadThread(threading.Thread):
    def __init__(self, file, file_type, purge, locale, **kwargs):
        self.file = file
        self.file_type = file_type
        self.purge = purge
        self.locale = locale
        super(ContentUploadThread, self).__init__(**kwargs)

    def run(self):
        import_content(self.file, self.file_type, self.purge, self.locale)


class UploadView(View):
    form_class = UploadFileForm
    template_name = "upload.html"

    def get(self, request, *args, **kwargs):
        loading = "ContentUploadThread" in [th.name for th in threading.enumerate()]
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return HttpResponse(loading)
        form = self.form_class()
        return render(request, self.template_name, {"form": form, "loading": loading})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data["purge"] == "True":
                ContentPage.objects.all().delete()
            ContentUploadThread(
                request.FILES["file"],
                form.cleaned_data["file_type"],
                form.cleaned_data["purge"],
                form.cleaned_data["locale"],
                name="ContentUploadThread",
            ).start()
            loading = "ContentUploadThread" in [th.name for th in threading.enumerate()]
            return render(
                request, self.template_name, {"form": form, "loading": loading}
            )


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
