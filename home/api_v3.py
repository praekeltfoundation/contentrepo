from typing import Any

from django.core.exceptions import MultipleObjectsReturned
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import path
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.models.sites import Site
import pprint

from home.serializers_v3 import ContentPageSerializerV3, WhatsAppTemplateSerializer

from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    WhatsAppTemplate,
    TriggeredContent,
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
            print("Trying to get object...")
            instance = self.get_object()
            # print(f"Instance is {instance}")
            # if self.request.query_params.get("return_drafts", "").lower() == "true":
            #     instance = instance.get_latest_revision_as_object()
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
        print("From Listing View - Getting Queryset")
        channel = self.validate_channel()
        queryset = self.get_queryset()
        if channel:
            queryset = queryset.filter(**{f"enable_{channel}": True})

        queryset_list = self.paginate_queryset(queryset)

        serializer = ContentPageSerializerV3(
            queryset_list, context={"request": request}, many=True
        )
        print("End of listing view")
        return self.get_paginated_response(serializer.data)

    def get_queryset(self) -> Any:

        print(f"Getting V3 Pages Queryset")

        all_queryset = (
            ContentPage.objects.all().order_by("pk").prefetch_related("locale")
        )
        draft_queryset = all_queryset.filter(has_unpublished_changes=True)
        live_queryset = all_queryset.filter(live=True)

        all_match_ids = [a.id for a in all_queryset.all() if a]
        print(f"All Queryset = {all_queryset.count()} items - {all_match_ids}")

        for ap in all_queryset:
            print(
                f"  Page Id:{ap.id} - Slug:{ap.slug} - Locale:{ap.locale} - Live:{ap.live}"
            )

        locale = self.request.query_params.get("locale", DEFAULT_LOCALE).casefold()
        slug = self.request.query_params.get("slug", "").casefold()
        title = self.request.query_params.get("title", "").casefold()
        trigger = self.request.query_params.get("trigger", "").casefold()
        tag = self.request.query_params.get("tag", "").casefold()

        locale_matches = set()
        slug_matches = set()
        title_matches = set()
        trigger_matches = set()
        tag_matches = set()

        if self.return_drafts:
            print("")

            print(f"Draft Queryset = {draft_queryset.count()} items")
            for dp in draft_queryset:
                print(f"Draft Page: {dp.pk} - {dp.title} - {dp.slug}")
                l_rev = dp.get_latest_revision_as_object()
                if locale == l_rev.locale.language_code.casefold():
                    print(f"    Locale match for DP {dp.id}")
                    locale_matches.add(dp.pk)

                if slug and slug in l_rev.slug.casefold():
                    print(f"    Slug match for DP {dp.id} -> {slug} in {l_rev.slug.casefold()}")
                    slug_matches.add(dp.pk)

                if title and title in l_rev.title.casefold():
                    print(f"    Title match for DP {dp.id} -> {title} in {l_rev.title.casefold()}")
                    title_matches.add(dp.pk)

                if trigger:
                    l_rev_triggers = set(
                        t.name.casefold() for t in l_rev.triggers.all() if t
                    )
                    print(f"    Trigger param supplied `{trigger}` and dp has triggers {l_rev_triggers}")
                    if trigger in l_rev_triggers:
                        print(f"    Trigger match for DP {dp.id}")
                        trigger_matches.add(dp.pk)

                if tag:
                    l_rev_tags = set(t.name.casefold() for t in l_rev.tags.all() if t)
                    print(f"    Tag param supplied `{tag}` and dp has tags {l_rev_tags}")
                    if tag in l_rev_tags:
                        print(f"    Tag match for DP {dp.id}")
                        tag_matches.add(dp.pk)

            print("")
            draft_ids = locale_matches
            if locale:
                print(
                f"    Locale matches from drafts: {len(locale_matches)} items - {locale_matches}"
            )
            if slug:
                draft_ids &= slug_matches
                print(
                f"    Slug matches from drafts: {len(slug_matches)} items - {slug_matches}"
            )
            if title:
                draft_ids &= title_matches
                print(
                f"    Title matches from drafts: {len(title_matches)} items - {title_matches}"
            )
            if trigger:
                draft_ids &= trigger_matches
                print(
                f"    Trigger matches from drafts: {len(trigger_matches)} items - {trigger_matches}"
            )
            if tag:
                draft_ids &= tag_matches
                print(f"    Tag matches from drafts: {len(tag_matches)} items - {tag_matches}")


            print("")
            print(
                f"Draft matches combined: {len(draft_ids)} items - {draft_ids}"
            )

            # We have filtered drafts, now we only need to filter pages without drafts
            live_queryset = all_queryset.filter(has_unpublished_changes=False)

        print("")
        print(
            f"Live Queryset = {live_queryset.count()} items - {[l.id for l in live_queryset.all() if l]}"
        )
        for lp in live_queryset:
            print(
                f"  Page Id:{lp.id} - Slug:{lp.slug} - Locale:{lp.locale} - Title:{lp.title} - Live:{lp.live}"
            )

        if locale:
            # print(f"    Locale param supplied: {locale}")
            live_queryset = live_queryset.filter(locale__language_code=locale)
            print(
                f"    Live Queryset after locale = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}"
            )

        if slug:
            live_queryset = live_queryset.filter(slug__icontains=slug)
            print(
                f"    Live Queryset after slug = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}"
            )

        if title:
            live_queryset = live_queryset.filter(title__icontains=title)
            print(
                f"    Live Queryset after title = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}"
            )

        if trigger:
            ids = TriggeredContent.objects.filter(tag__name__iexact=trigger).values_list("content_object_id")
            live_queryset = live_queryset.filter(id__in=ids)
            print(
                f"    Live Queryset after triggers =  {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}"
            )

        if tag:
            ids = ContentPageTag.objects.filter(tag__name__iexact=tag).values_list("content_object_id")
            live_queryset = live_queryset.filter(id__in=ids)
            print(
                f"    Live Queryset afer tags = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}"
            )

        if self.return_drafts:
            queryset_to_return = all_queryset.filter(id__in=draft_ids) | live_queryset
        else:
            queryset_to_return = live_queryset

        # [t.name.casefold() for t in l_rev.tags.all() if t]
        print("")
        print(f"QuerysetToReturn IDs: {[l.id for l in queryset_to_return.all() if l]}")

        for qtrp in queryset_to_return:
            print(
                f"  Page Id:{qtrp.id} - Slug:{qtrp.slug} - Locale:{qtrp.locale} - Live:{qtrp.live}"
            )

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
