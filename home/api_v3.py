from typing import Any

from django.core.exceptions import MultipleObjectsReturned
from django.http.response import Http404
from django.urls import path
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.models.sites import Site

from home.serializers_v3 import ContentPageSerializerV3, WhatsAppTemplateSerializer

from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    TriggeredContent,
    WhatsAppTemplate,
)


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

    def detail_view(self, request, pk=None, slug=None):
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
            .order_by("latest_revision_id")
            .prefetch_related("locale")
        )
        live_queryset = draft_queryset.filter(live=True).order_by("last_published_at")

        queryset_to_return = live_queryset

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )

        if return_drafts:
            queryset_to_return = draft_queryset | live_queryset
        else:
            queryset_to_return = live_queryset

        slug = self.request.query_params.get("slug", "")
        if slug:
            queryset_to_return = queryset_to_return.filter(slug__icontains=slug)

        locale = self.request.query_params.get("locale", "")
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
            path("<int:pk>/", cls.as_view({"get": "detail_view"}), name="detail"),
            path("<slug:slug>/", cls.as_view({"get": "detail_view"}), name="detail"),
            path("find/", cls.as_view({"get": "find_view"}), name="find"),
        ]


class ContentPagesV3APIViewset(PagesAPIViewSet):
    """
    Our custom V3 Pages API endpoint that allows finding pages by pk or slug
    """

    model = ContentPage
    base_serializer_class = ContentPageSerializerV3
    meta_fields = []
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

    pagination_class = PageNumberPagination

    def validate_channel(self):
        channel = self.request.query_params.get("channel", "").lower()
        if channel not in {"", "web", "whatsapp", "sms", "ussd", "messenger", "viber"}:
            raise ValidationError(
                {"channel": [f"Channel matching query '{channel}' does not exist."]}
            )
        return channel

    def detail_view(self, request, pk=None, slug=None):
        _channel = self.validate_channel()
        if slug is not None:
            self.lookup_field = "slug"
        else:
            self.lookup_field = "pk"

        try:
            instance = self.get_object()
            if self.request.query_params.get("return_drafts", "").lower() == "true":
                instance = instance.get_latest_revision_as_object()

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

    def listing_view(self, request, *args, **kwargs):
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
        # In this context, 'live()' means ONLY page revisions that have been published
        # 'not_live()' refers to page revisions that has been saved as a draft, but not published
        # 'return_drafts' means 'Give me the latest revisions of everything, whether that is a published page, or an unpublished revision'

        draft_queryset = ContentPage.objects.not_live().prefetch_related("locale")
        live_queryset = ContentPage.objects.live().prefetch_related("locale")
        queryset_to_return = live_queryset

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )

        if return_drafts:
            queryset_to_return = draft_queryset | live_queryset
        else:
            queryset_to_return = live_queryset

        title = self.request.query_params.get("title", "")
        if title:
            queryset_to_return = queryset_to_return.filter(title__icontains=title)

        slug = self.request.query_params.get("slug", "")
        if slug:
            queryset_to_return = queryset_to_return.filter(slug__icontains=slug)

        # TODO: Add tests for this once we have locale support in test page builder
        locale = self.request.query_params.get("locale", "")
        if locale:
            queryset_to_return = queryset_to_return.filter(locale__language_code=locale)

        # TODO: We may want to add an environment variable for
        # V3_LOCALE_OPTIONAL = True
        # If false, then not sending locale with request is an error, 400
        # If true, then not sending locale with request use default
        # Query param overwrites regardless
        # TODO: The V2 API allowed a "search" query param to be passed.
        # I don't think we want that here, but leaving this here for now

        # search = self.request.query_params.get("search", "")
        # if search:
        #     queryset_to_return = queryset_to_return.search(search)

        tag = self.request.query_params.get("tag")
        if tag:
            ids = []
            for t in ContentPageTag.objects.filter(tag__name__iexact=tag):
                ids.append(t.content_object_id)

            queryset_to_return = queryset_to_return.filter(id__in=ids)

        trigger = self.request.query_params.get("trigger")
        if trigger is not None:
            ids = []
            for t in TriggeredContent.objects.filter(tag__name__iexact=trigger.strip()):
                ids.append(t.content_object_id)

            queryset_to_return = queryset_to_return.filter(id__in=ids)

        return queryset_to_return

    @classmethod
    def get_urlpatterns(cls):
        """
        This returns a list of URL patterns for the endpoint
        """

        return [
            path("", cls.as_view({"get": "listing_view"}), name="listing"),
            path("<int:pk>/", cls.as_view({"get": "detail_view"}), name="detail"),
            path("<slug:slug>/", cls.as_view({"get": "detail_view"}), name="detail"),
            path("find/", cls.as_view({"get": "find_view"}), name="find"),
        ]


api_router_v3 = WagtailAPIRouter("wagtailapiv3_router")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
