import json
import logging
import queue
import threading

import django_filters
from django.contrib import messages
from django.db import connection as db_connection
from django.db.models import Count, F
from django.db.models.functions import TruncMonth
from django.forms import MultiWidget
from django.forms.widgets import NumberInput
from django.http import JsonResponse
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

from .content_import_export import import_content, import_ordered_sets
from .forms import UploadContentFileForm, UploadOrderedContentSetFileForm
from .import_content_pages import ImportException
from .mixins import SpreadsheetExportMixin
from .models import (
    ContentPage,
    ContentPageRating,
    OrderedContentSet,
    PageView,
    WhatsAppTemplate,
)
from .serializers import ContentPageRatingSerializer, PageViewSerializer

logger = logging.getLogger(__name__)


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
        ("sms", "SMS"),
        ("ussd", "USSD"),
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


class UploadThread(threading.Thread):
    def __init__(self, file, file_type, **kwargs):
        self.file = file
        self.file_type = file_type
        self.result_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        super().__init__(**kwargs)


class ContentUploadThread(UploadThread):
    def __init__(self, purge, locale, **kwargs):
        self.purge = purge
        self.locale = locale
        super().__init__(**kwargs)

    def run(self):
        try:
            import_content(
                self.file, self.file_type, self.progress_queue, self.purge, self.locale
            )
        except ImportException as e:
            self.result_queue.put(
                (
                    messages.ERROR,
                    [
                        f"Content import failed on row {e.row_num}: {msg}"
                        for msg in e.message
                    ],
                )
            )
        except Exception:
            self.result_queue.put((messages.ERROR, ["Content import failed"]))
            logger.exception("Content import failed")
        else:
            self.result_queue.put((messages.SUCCESS, ["Content import successful"]))
        # Wait until the user has fetched the result message to close the thread
        self.result_queue.join()


class OrderedContentSetUploadThread(UploadThread):
    def __init__(self, purge, **kwargs):
        self.purge = purge
        super().__init__(**kwargs)

    def run(self):
        try:
            import_ordered_sets(
                self.file, self.file_type, self.progress_queue, self.purge
            )
        except Exception:
            self.result_queue.put((messages.ERROR, "Ordered content set import failed"))
            logger.exception("Ordered content set import failed")
        else:
            self.result_queue.put(
                (messages.SUCCESS, "Ordered content set import successful")
            )
        # Wait until the user has fetched the result message to close the thread
        self.result_queue.join()


class OrderedContentSetUploadView(View):
    form_class = UploadOrderedContentSetFileForm
    template_name = "orderedcontentset_upload.html"

    def get(self, request, *args, **kwargs):
        thread = next(
            (
                t
                for t in threading.enumerate()
                if t.name == "OrderedContentSetUploadThread"
            ),
            None,
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if not thread:
                return JsonResponse({"loading": False})
            try:
                # If there's a result message from the thread, send it to the user,
                # and call task_done to end the thread.
                level, text = thread.result_queue.get_nowait()
                messages.add_message(request, level, text)
                thread.result_queue.task_done()
                return JsonResponse({"loading": False})
            except queue.Empty:
                # No message means that the task is still running
                # Get the latest task progress and return that too
                progress = None
                try:
                    while True:
                        progress = thread.progress_queue.get_nowait()
                except queue.Empty:
                    pass

                return JsonResponse({"loading": True, "progress": progress})
        form = self.form_class()
        return render(
            request, self.template_name, {"form": form, "loading": thread is not None}
        )

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data["purge"] == "True":
                OrderedContentSet.objects.all().delete()
            OrderedContentSetUploadThread(
                form.cleaned_data["purge"],
                file=request.FILES["file"],
                file_type=form.cleaned_data["file_type"],
                name="OrderedContentSetUploadThread",
            ).start()
            loading = "OrderedContentSetUploadThread" in [
                th.name for th in threading.enumerate()
            ]
            return render(
                request, self.template_name, {"form": form, "loading": loading}
            )


class ContentUploadView(View):
    form_class = UploadContentFileForm
    template_name = "upload.html"

    def get(self, request, *args, **kwargs):
        thread = next(
            (t for t in threading.enumerate() if t.name == "ContentUploadThread"), None
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            if not thread:
                return JsonResponse({"loading": False})

            try:
                # If there's a result message from the thread, send it to the user,
                # and call task_done to end the thread.
                level, texts = thread.result_queue.get_nowait()
                if isinstance(texts, str):
                    text = [texts]
                for text in texts:
                    messages.add_message(request, level, text)
                thread.result_queue.task_done()
                return JsonResponse({"loading": False})
            except queue.Empty:
                # No message means that the task is still running
                # Get the latest task progress and return that too
                progress = None
                try:
                    while True:
                        progress = thread.progress_queue.get_nowait()
                except queue.Empty:
                    pass

                return JsonResponse({"loading": True, "progress": progress})
        form = self.form_class()
        return render(
            request, self.template_name, {"form": form, "loading": thread is not None}
        )

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            ContentUploadThread(
                form.cleaned_data["purge"],
                form.cleaned_data["locale"],
                file=request.FILES["file"],
                file_type=form.cleaned_data["file_type"],
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

    name = f"{field.capitalize()}CursorPagination"
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

    def get_queryset(self):
        # filter the queryset by data jsonfield:
        queryset = self.queryset
        for key, value in self.request.GET.items():
            if "data__" in key:
                queryset = queryset.filter(**{key: value})

        # Only return unique pages
        if self.request.GET.get("unique_pages", False) == "true":
            if db_connection.vendor == "postgresql":
                # Fields used for "distinct" must be used for ordering
                self.paginator.ordering = "page"
                queryset = queryset.distinct("page")
            else:
                raise ValidationError({"unique_pages": ["This query is not supported"]})

        return queryset


class ContentPageRatingViewSet(GenericListViewset, CreateModelMixin):
    queryset = ContentPageRating.objects.all()
    serializer_class = ContentPageRatingSerializer
    filterset_class = ContentPageRatingFilter

    def create(self, request, *args, **kwargs):
        if "page" in request.data:
            try:
                page = ContentPage.objects.get(id=request.data["page"])
                # FIXME: why are we altering the request data here
                request.data["revision"] = page.get_latest_revision().id
            except ContentPage.DoesNotExist:
                raise ValidationError({"page": ["Page matching query does not exist."]})

        return super().create(request, *args, **kwargs)


class WhatsAppTemplateViewSet(GenericListViewset):
    # queryset = WhatsAppTemplate.objects.all()
    model = WhatsAppTemplate
    form_fields = ["name", "body", "category", "locale", "status"]
    icon = "user"
    add_to_admin_menu = True
    copy_view_enabled = False
    inspect_view_enabled = True
