from typing import Any

from django.http.response import Http404
from django.urls import path
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet

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
            "qa",
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

        try:
            if "qa" in request.GET and request.GET["qa"].lower() == "true":
                instance = self.get_object().get_latest_revision_as_object()
            else:
                instance = self.get_object()
        except Exception as e:
            # TODO: Handle this better
            print(f"Exception = {e}")
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
        qa = self.request.query_params.get("qa")

        if qa:
            # return the latest revision for each WhatsApp Template
            queryset = WhatsAppTemplate.objects.all().order_by("latest_revision_id")
            for wat in queryset:
                latest_revision = wat.revisions.order_by("-created_at").first()
                if latest_revision:
                    latest_revision = latest_revision.as_object()
                    wat.slug = latest_revision.slug

        else:
            queryset = WhatsAppTemplate.objects.filter(live=True).order_by(
                "last_published_at"
            )

        return queryset

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
            if self.request.query_params.get("return_drafts", "").lower() == "true":
                instance = self.get_object().get_latest_revision_as_object()
            else:
                instance = self.get_object()

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
