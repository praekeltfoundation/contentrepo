from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    WhatsAppTemplate,
    TriggeredContent,
)
from typing import Any

from django.core.exceptions import MultipleObjectsReturned
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import path
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.models.sites import Site
from .models import ContentPageIndex

from home.serializers_v3 import ContentPageSerializerV3, WhatsAppTemplateSerializer

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
            WhatsAppTemplate.objects.all().order_by("pk").select_related("locale")
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
        ]

class ContentPageIndexV3ViewSet(PagesAPIViewSet):
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return ContentPageIndex.objects.live()

class ContentPagesV3APIViewset(PagesAPIViewSet):
    """
    Our custom V3 Pages API endpoint that allows finding pages by pk or slug
    """

    model = ContentPage
    base_serializer_class = ContentPageSerializerV3
    meta_fields: list[str] = []
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "trigger",
            "page",
            "return_drafts",
            "channel",
            "slug",
            "child_of",
        ]
    )
    pagination_class = PageNumberPagination

    def validate_channel(self) -> str:
        channel = self.request.query_params.get("channel", "").lower()
        if channel not in VALID_CHANNELS:
            raise ValidationError(
                {"channel": [f"Channel matching query '{channel}' does not exist."]}
            )
        return channel

    @property
    def return_drafts(self):
        return self.request.query_params.get("return_drafts", "").casefold() == "true"

    def get_object(self):
        # A slug could have changed in a draft version of a page
        if self.lookup_field == "slug" and self.return_drafts:
            queryset = self.get_queryset()
            # Check the latest draft of each page with changes
            draft_queryset = queryset.filter(has_unpublished_changes=True)
            for draft_page in draft_queryset:
                latest_revision = draft_page.get_latest_revision_as_object()
                if self.kwargs["slug"] == latest_revision.slug:
                    return latest_revision
            # Now check all pages without changes
            published_queryset = queryset.filter(has_unpublished_changes=False)
            return get_object_or_404(published_queryset, slug=self.kwargs["slug"])

        return super().get_object()

    def process_detail_view(self, request, pk=None, slug=None):
        self.validate_channel()
        if slug is not None:
            self.lookup_field = "slug"
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
        all_queryset = (
            ContentPage.objects.all().order_by("pk").prefetch_related("locale")
        )
        draft_queryset = all_queryset.filter(has_unpublished_changes=True)
        live_queryset = all_queryset.filter(live=True)

        locale = self.request.query_params.get("locale", DEFAULT_LOCALE).casefold()
        slug = self.request.query_params.get("slug", "").casefold()
        title = self.request.query_params.get("title", "").casefold()
        trigger = self.request.query_params.get("trigger", "").casefold()
        tag = self.request.query_params.get("tag", "").casefold()
        child_of = self.request.query_params.get("child_of", "").casefold()

        locale_matches = set()
        slug_matches = set()
        title_matches = set()
        trigger_matches = set()
        tag_matches = set()

        # Build of Draft results
        if self.return_drafts:
            for dp in draft_queryset:
                l_rev = dp.get_latest_revision_as_object()
                if locale == l_rev.locale.language_code.casefold():
                    locale_matches.add(dp.pk)
                if slug and slug in l_rev.slug.casefold():
                    slug_matches.add(dp.pk)
                if title and title in l_rev.title.casefold():
                    title_matches.add(dp.pk)
                if trigger:
                    l_rev_triggers = {
                        t.name.casefold() for t in l_rev.triggers.all() if t
                    }
                    if trigger in l_rev_triggers:
                        trigger_matches.add(dp.pk)
                if tag:
                    l_rev_tags = {t.name.casefold() for t in l_rev.tags.all() if t}
                    if tag in l_rev_tags:
                        tag_matches.add(dp.pk)
            draft_ids = locale_matches
            if slug:
                draft_ids &= slug_matches
            if title:
                draft_ids &= title_matches
            if trigger:
                draft_ids &= trigger_matches
            if tag:
                draft_ids &= tag_matches

            # We have filtered drafts, now we only need to filter pages without drafts
            live_queryset = all_queryset.filter(has_unpublished_changes=False)

        # Build up Live results
        if locale:
            live_queryset = live_queryset.filter(locale__language_code=locale)
        if slug:
            live_queryset = live_queryset.filter(slug__icontains=slug)
        if title:
            live_queryset = live_queryset.filter(title__icontains=title)
        if child_of:
            try:
                parent_page = ContentPage.objects.get(slug=child_of)
                live_queryset = live_queryset.child_of(parent_page)
            except ContentPage.DoesNotExist:
                raise NotFound({"child_of": [f"Parent page with id {child_of} does not exist."]})

        if trigger:
            ids = TriggeredContent.objects.filter(
                tag__name__iexact=trigger
            ).values_list("content_object_id")
            live_queryset = live_queryset.filter(id__in=ids)
        if tag:
            ids = ContentPageTag.objects.filter(tag__name__iexact=tag).values_list(
                "content_object_id"
            )
            live_queryset = live_queryset.filter(id__in=ids)

        # Decide which results to return
        if self.return_drafts:
            queryset_to_return = all_queryset.filter(id__in=draft_ids) | live_queryset
        else:
            queryset_to_return = live_queryset

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
        ]


api_router_v3 = WagtailAPIRouter("wagtailapiv3_router")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
api_router_v3.register_endpoint("indexes", ContentPageIndexV3ViewSet)
