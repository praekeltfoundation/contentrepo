from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    WhatsAppTemplate,
    TriggeredContent,
)
import logging

from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.http import HttpRequest
from django.http.response import Http404
from django.urls import path
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.models.sites import Site

from home.serializers_v3 import ContentPageSerializerV3, WhatsAppTemplateSerializer

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        # logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ],
)


DEFAULT_LOCALE = Site.objects.get(is_default_site=True).root_page.locale.language_code

VALID_CHANNELS = {"", "web", "whatsapp", "sms", "ussd", "messenger", "viber"}

class WhatsAppTemplateViewset(BaseAPIViewSet):
    model = WhatsAppTemplate
    base_serializer_class = WhatsAppTemplateSerializer
    meta_fields = []
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(
        [
            "return_drafts",
        ]
    )

    pagination_class = PageNumberPagination
    search_fields = [
        "slug",
    ]
    filter_backends = (SearchFilter,)

    def process_detail_view(self, request, pk=None, slug=None):
        if slug is not None:
            self.lookup_field = "slug"

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )

        try:
            instance = self.get_object()
            if return_drafts:
                instance = instance.get_latest_revision_as_object()

        except Http404:
            raise NotFound({"template": ["Template matching query does not exist."]})

        serializer = WhatsAppTemplateSerializer(instance, context={"request": request})

        return Response(serializer.data)

    def detail_view_by_id(self, request, pk):
        return self.process_detail_view(request, pk=pk)

    def detail_view_by_slug(self, request, slug):
        return self.process_detail_view(request, slug=slug)

    def listing_view(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset_list = self.paginate_queryset(queryset)
        serializer = WhatsAppTemplateSerializer(
            queryset_list, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    def get_queryset(self):
        draft_queryset = (
            WhatsAppTemplate.objects.all()
            .order_by("pk")
            .select_related("locale")
        )
        live_queryset = draft_queryset.filter(live=True)

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )

        queryset_to_return = draft_queryset if return_drafts else live_queryset

        slug = self.request.query_params.get("slug", "")
        if slug:
            queryset_to_return = queryset_to_return.filter(slug__icontains=slug)

        locale = self.request.query_params.get("locale", DEFAULT_LOCALE)
        if locale:
            queryset_to_return = queryset_to_return.filter(locale__language_code=locale)
        return queryset_to_return

    @classmethod
    def get_urlpatterns(cls):
        """
        This returns a list of URL patterns for the endpoint
        """
        return [
            path("", cls.as_view({"get": "listing_view"}), name="listing"),
            path("<int:pk>/", cls.as_view({"get": "detail_view_by_id"}), name="detail"),
            path(
                "<slug:slug>/",
                cls.as_view({"get": "detail_view_by_slug"}),
                name="detail",
            ),
            # path("find/", cls.as_view({"get": "find_view"}), name="find"),
        ]


class ContentPagesV3APIViewset(PagesAPIViewSet):
    """
    Our custom V3 Pages API endpoint that allows finding pages by pk or slug
    """

    model = ContentPage
    base_serializer_class = ContentPageSerializerV3
    meta_fields: list[str] = []
    _cached_queryset: QuerySet[ContentPage] | None = None  # Cache for the queryset
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "trigger",
            "page",
            "return_drafts",
            "channel",
            "slug",
        ]
    )
    calling_endpoint = ""
    pagination_class = PageNumberPagination

    def validate_channel(self) -> str:
        channel = self.request.query_params.get("channel", "").lower()
        if channel not in VALID_CHANNELS:
            raise ValidationError(
                {"channel": [f"Channel matching query '{channel}' does not exist."]}
            )
        return channel

    def _get_base_queryset(self) -> QuerySet[ContentPage]:
        """Get the base queryset with all necessary relations."""
        return (
            ContentPage.objects.all()
            .order_by("pk")
            .select_related(
                "locale",
                "owner",
                "latest_revision",
                "live_revision",
                "locked_by"
            )
        )

    def _get_draft_by_slug(self, slug: str, draft_queryset: QuerySet[ContentPage]) -> ContentPage | None:
        """Find a draft page matching the given slug."""
        for dp in draft_queryset:
            l_rev = dp.get_latest_revision_as_object()
            if slug.casefold() in l_rev.slug.casefold():
                logger.debug(
                    f"Found draft match for slug `{slug}` in draft page ID {dp.id} with slug `{l_rev.slug}`"
                )
                return ContentPage.objects.filter(id=dp.id).first()
        return None

    def get_object(self) -> ContentPage | None:
        """Get a specific page by ID or slug, handling both live and draft content."""
        logger.debug(f"Get_object called from {self.calling_endpoint} page")

        if self.calling_endpoint != "detail":
            return super().get_object()

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        slug_to_display = self.request.parser_context["kwargs"].get("slug", None)
        int_to_display = self.request.parser_context["kwargs"].get("pk", None)

        all_queryset = self._get_base_queryset()
        page_to_return = None

        if slug_to_display:
            if return_drafts:
                draft_queryset = all_queryset.filter(has_unpublished_changes="True")
                page_to_return = self._get_draft_by_slug(slug_to_display, draft_queryset)
            if not page_to_return:
                page_to_return = all_queryset.filter(slug=slug_to_display).first()

        elif int_to_display:
            page_to_return = all_queryset.filter(id=int_to_display).first()

        if not page_to_return:
            raise NotFound({"page": ["Page matching query does not exist."]})

        return page_to_return

    def process_detail_view(
        self,
        request: HttpRequest,
        pk: int | None = None,
        slug: str | None = None
    ) -> Response:
        self.calling_endpoint = "detail"
        _channel = self.validate_channel()
        if slug is not None:
            self.lookup_field = "slug"
        else:
            self.lookup_field = "pk"

        try:
            instance = self.get_object()

        # TODO: Add tests for this once we have locale support in test page builder
        except MultipleObjectsReturned:
            default_language_code = Site.objects.get(
                is_default_site=True
            ).root_page.locale.language_code
            raise MultipleObjectsReturned(
                f"Multiple pages found. Detail View requires a single page.  Please try narrowing down your query by adding a locale query parameter e.g. '&locale={default_language_code}'"
            )

        except Http404:
            raise NotFound({"page": ["Page matching query does not exist."]})

        instance.save_page_view(request.query_params)
        serializer = ContentPageSerializerV3(instance, context={"request": request})
        return Response(serializer.data)

    def detail_view_by_id(self, request: HttpRequest, pk: int) -> Response:
        return self.process_detail_view(request, pk=pk)

    def detail_view_by_slug(self, request: HttpRequest, slug: str) -> Response:
        return self.process_detail_view(request, slug=slug)

    def listing_view(self, request: HttpRequest, *args, **kwargs) -> Response:
        self.calling_endpoint = "listing"
        channel = self.validate_channel()
        queryset = self.get_queryset()
        if channel:
            queryset = queryset.filter(**{f"enable_{channel}": True})

        queryset_list = self.paginate_queryset(queryset)

        serializer = ContentPageSerializerV3(
            queryset_list, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    def _build_filters(self) -> Q:
        """Build query filters based on request parameters."""
        base_filters = Q()

        # Get and normalize query parameters
        locale = self.request.query_params.get("locale", DEFAULT_LOCALE).casefold()
        slug = self.request.query_params.get("slug", "").casefold()
        title = self.request.query_params.get("title", "").casefold()
        trigger = self.request.query_params.get("trigger", "").casefold()
        tag = self.request.query_params.get("tag", "").casefold()

        if locale:
            base_filters &= Q(locale__language_code__iexact=locale)
        if slug:
            base_filters &= Q(slug__icontains=slug)
        if title:
            base_filters &= Q(title__icontains=title)
        if trigger:
            trigger_subquery = (
                TriggeredContent.objects
                .filter(
                    tag__name__icontains=trigger.strip(),
                    content_object_id=OuterRef('pk')
                )
                .values('id')[:1]
            )
            base_filters &= Q(Exists(trigger_subquery))
        if tag:
            tag_subquery = (
                ContentPageTag.objects
                .filter(
                    tag__name__iexact=tag,
                    content_object_id=OuterRef('pk')
                )
                .values('id')[:1]
            )
            base_filters &= Q(Exists(tag_subquery))

        return base_filters

    def _get_filtered_queryset(self, queryset: QuerySet[ContentPage], filters: Q) -> QuerySet[ContentPage]:
        """Apply filters to a queryset and maintain proper select/prefetch."""
        return queryset.filter(filters)

    def get_queryset(self) -> QuerySet[ContentPage]:
        """Get a queryset of pages, handling both live and draft content."""
        logger.debug(f"Getting V3 Pages Queryset - Called from {self.calling_endpoint}")

        if self.calling_endpoint == "listing" and self._cached_queryset is not None:
            logger.debug("Returning cached queryset")
            return self._cached_queryset

        base_queryset = self._get_base_queryset()


        filters = self._build_filters()
        live_filters = filters & Q(live=True, has_unpublished_changes="False")
        live_queryset = self._get_filtered_queryset(base_queryset, live_filters)

        logger.debug(
            f"Live Queryset = {live_queryset.count()} items - {list(live_queryset.values_list('id', flat=True))}"
        )

        return_drafts = self.request.query_params.get("return_drafts", "").lower() == "true"
        if return_drafts:
            draft_queryset = base_queryset.filter(has_unpublished_changes="True")
            draft_matches = draft_queryset.filter(filters).values_list('id', flat=True)

            if draft_matches:
                logger.debug(f"Adding {len(draft_matches)} drafts - {list(draft_matches)}")
                draft_queryset = self._get_filtered_queryset(
                    ContentPage.objects.filter(id__in=draft_matches),
                    Q()
                )
                live_queryset = live_queryset | draft_queryset

        logger.debug(
            f"QuerysetToReturn IDs: {[page.id for page in live_queryset.all() if page]}"
        )

        if self.calling_endpoint == "listing":
            self._cached_queryset = live_queryset

        return live_queryset

    @classmethod
    def get_urlpatterns(cls):
        """
        This returns a list of URL patterns for the endpoint
        """

        return [
            path("", cls.as_view({"get": "listing_view"}), name="listing"),
            path("<int:pk>/", cls.as_view({"get": "detail_view_by_id"}), name="detail"),
            path(
                "<slug:slug>/",
                cls.as_view({"get": "detail_view_by_slug"}),
                name="detail",
            ),
            # path("find/", cls.as_view({"get": "find_view"}), name="find"),
        ]


api_router_v3 = WagtailAPIRouter("wagtailapiv3_router")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
