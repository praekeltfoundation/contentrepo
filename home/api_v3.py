from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    WhatsAppTemplate,
    TriggeredContent,
)
import logging
from typing import Any

from django.core.exceptions import MultipleObjectsReturned
from django.http.response import Http404
from django.urls import path
from django.db.models import Q, Exists, OuterRef
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


@extend_schema(tags=["v3 api"])
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
            WhatsAppTemplate.objects.all().order_by("pk").prefetch_related("locale")
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


@extend_schema(tags=["v3 api"])
class ContentPagesV3APIViewset(PagesAPIViewSet):
    """
    Our custom V3 Pages API endpoint that allows finding pages by pk or slug
    """

    model = ContentPage
    base_serializer_class = ContentPageSerializerV3
    meta_fields = []
    _cached_queryset = None  # Cache for the queryset
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

    def validate_channel(self):
        channel = self.request.query_params.get("channel", "").lower()
        if channel not in {"", "web", "whatsapp", "sms", "ussd", "messenger", "viber"}:
            raise ValidationError(
                {"channel": [f"Channel matching query '{channel}' does not exist."]}
            )
        return channel

    def get_object(self):
        logger.debug(f"Get_object called from {self.calling_endpoint} page")
        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        slug_to_display = self.request.parser_context["kwargs"].get("slug", None)
        int_to_display = self.request.parser_context["kwargs"].get("pk", None)

        all_queryset = (
            ContentPage.objects.all().order_by("pk").prefetch_related("locale")
        )
        draft_queryset = all_queryset.filter(has_unpublished_changes="True")
        page_to_return = ""
        if self.calling_endpoint == "detail":
            if slug_to_display:
                if return_drafts:

                    for dp in draft_queryset:

                        l_rev = dp.get_latest_revision_as_object()
                        if slug_to_display in l_rev.slug:
                            logger.debug(
                                f"    Found draft match for slug `{slug_to_display}` in draft page ID {dp.id} with slug `{l_rev.slug}`"
                            )
                            page_to_return = ContentPage.objects.filter(
                                id=dp.id
                            ).first()
                else:
                    page_to_return = all_queryset.filter(slug=slug_to_display).first()

                if not page_to_return:
                    raise NotFound({"page": ["Page matching query does not exist."]})

                    page_to_return = super().get_object()

            if int_to_display:
                page_to_return = all_queryset.filter(id=int_to_display).first()
                if not page_to_return:
                    raise NotFound({"page": ["Page matching query does not exist."]})

        return page_to_return

    def process_detail_view(self, request, pk=None, slug=None):
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

    def detail_view_by_id(self, request, pk):
        return self.process_detail_view(request, pk=pk)

    def detail_view_by_slug(self, request, slug):
        return self.process_detail_view(request, slug=slug)

    def listing_view(self, request, *args, **kwargs):
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

    def get_queryset(self) -> Any:
        logger.debug(f"Getting V3 Pages Queryset - Called from {self.calling_endpoint}")

        # Return cached queryset if available and we're in listing view
        if self.calling_endpoint == "listing" and self._cached_queryset is not None:
            logger.debug("Returning cached queryset")
            return self._cached_queryset

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        all_queryset = (
            ContentPage.objects.all()
            .order_by("pk")
            .select_related("locale")
            .prefetch_related(
                "latest_revision",
                "triggers",
                "tags"
            )
        )
        draft_queryset = all_queryset.filter(has_unpublished_changes="True")

        if self.calling_endpoint == "detail":
            page_to_return = ""
            if return_drafts:
                slug_to_display = self.request.parser_context["kwargs"][
                    "slug"
                ].casefold()

                for dp in draft_queryset:
                    l_rev = dp.get_latest_revision_as_object()
                    if slug_to_display in l_rev.slug:
                        logger.debug(
                            f"    Found draft match for slug `{slug_to_display}` in draft page ID {dp.id} with slug `{l_rev.slug}`"
                        )
                        page_to_return = ContentPage.objects.filter(id=dp.id)
                        logger.debug(f"Page to return is {page_to_return}")

            return page_to_return

        # Get and normalize query parameters
        locale = self.request.query_params.get("locale", DEFAULT_LOCALE).casefold()
        slug = self.request.query_params.get("slug", "").casefold()
        title = self.request.query_params.get("title", "").casefold()
        trigger = self.request.query_params.get("trigger", "").casefold()
        tag = self.request.query_params.get("tag", "").casefold()

        # Initialize filters
        base_filters = Q()
        if locale:
            base_filters &= Q(locale__language_code__iexact=locale)
        if slug:
            base_filters &= Q(slug__icontains=slug)
        if title:
            base_filters &= Q(title__icontains=title)
        if trigger:
            trigger_subquery = TriggeredContent.objects.filter(
                tag__name__icontains=trigger.strip(),
                content_object_id=OuterRef('pk')
            ).values('id')[:1]
            base_filters &= Q(Exists(trigger_subquery))
        if tag:
            tag_subquery = ContentPageTag.objects.filter(
                tag__name__iexact=tag,
                content_object_id=OuterRef('pk')
            ).values('id')[:1]
            base_filters &= Q(Exists(tag_subquery))

        # Start with live queryset
        live_queryset = all_queryset.filter(base_filters & Q(live=True, has_unpublished_changes="False"))
        logger.debug(
            f"Live Queryset = {live_queryset.count()} items - {list(live_queryset.values_list('id', flat=True))}"
        )

        # Initialize result queryset
        queryset_to_return = live_queryset

        # Add drafts if requested
        if return_drafts:
            draft_matches = draft_queryset.filter(base_filters).values_list('id', flat=True)
            if draft_matches:
                logger.debug(f"Adding {len(draft_matches)} drafts - {list(draft_matches)}")
                queryset_to_return = (
                    queryset_to_return | 
                    ContentPage.objects.filter(id__in=draft_matches)
                    .select_related("locale")
                    .prefetch_related(
                        "latest_revision",
                        "triggers",
                        "tags"
                    )
                )

        logger.debug(
            f"QuerysetToReturn IDs: {[page.id for page in queryset_to_return.all() if page]}"
        )

        # Cache the queryset if we're in listing view
        if self.calling_endpoint == "listing":
            self._cached_queryset = queryset_to_return
            
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


api_router_v3 = WagtailAPIRouter("wagtailapiv3_router")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
