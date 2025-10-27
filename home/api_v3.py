from typing import Any

from django.core.exceptions import MultipleObjectsReturned
from django.http.response import Http404
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
    TriggeredContent
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
        print(f"Custom get_object called in V3 Pages from {self.calling_endpoint}")
        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        slug_to_display = self.request.parser_context["kwargs"].get("slug", None)
        int_to_display = self.request.parser_context["kwargs"].get("pk", None)
        print(f"INT = {slug_to_display}")
        all_queryset = ContentPage.objects.all().order_by("pk").prefetch_related("locale")
        draft_queryset = all_queryset.filter(has_unpublished_changes="True")
        page_to_return = ""
        if self.calling_endpoint == "detail":
            if slug_to_display:
                if return_drafts:
                    
                    print(f"Gonna go look for drafts with this slug `{slug_to_display}`")

                    for dp in draft_queryset:
                    # print(f"Draft Page: {dp.pk} - {dp.title} - {dp.slug}")
                        l_rev = dp.get_latest_revision_as_object()
                        if slug_to_display in l_rev.slug:
                            print(f"    Found draft match for slug `{slug_to_display}` in draft page ID {dp.id} with slug `{l_rev.slug}`")
                            draft_page_id = dp.id
                            page_to_return = ContentPage.objects.filter(id=dp.id).first()
                            print(f"Page to return is {page_to_return}")
                else:
                    print("Getting live object only")
                    page_to_return = all_queryset.filter(slug=slug_to_display).first()
                    # page_to_return = super().get_object()


                if not page_to_return:
                    print("No draft match found, going to get live object")
                    raise NotFound({"page": ["Page matching query does not exist."]})
                    
                    page_to_return = super().get_object()


            if int_to_display:
                print("Getting by ID")
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
            raise NotFound(
                {
                    "page": [
                        f"Multiple pages found. Detail View requires a single page.  Please try narrowing down your query by adding a locale query parameter e.g. '&locale={default_language_code}"
                    ]
                }
            )
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
        
        print("")
        print("********************************")
        print(f"Getting V3 Pages Queryset - Called from {self.calling_endpoint}")

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        all_queryset = ContentPage.objects.all().order_by("pk").prefetch_related("locale")
        draft_queryset = all_queryset.filter(has_unpublished_changes="True")

        if self.calling_endpoint == "detail":
            page_to_return = ""
            if return_drafts:
                slug_to_display = self.request.parser_context["kwargs"]["slug"].casefold()
                print(f"Gonna go look for drafts with this slug `{slug_to_display}`")

                for dp in draft_queryset:
                # print(f"Draft Page: {dp.pk} - {dp.title} - {dp.slug}")
                    l_rev = dp.get_latest_revision_as_object()
                    if slug_to_display in l_rev.slug:
                        print(f"    Found draft match for slug `{slug_to_display}` in draft page ID {dp.id} with slug `{l_rev.slug}`")
                        draft_page_id = dp.id
                        page_to_return = ContentPage.objects.filter(id=dp.id)
                        print(f"Page to return is {page_to_return}")

                        
            return page_to_return

        
        all_match_ids = [a.id for a in all_queryset.all() if a]
        print(f"All Queryset = {all_queryset.count()} items - {all_match_ids}")
        
        locale = self.request.query_params.get("locale", DEFAULT_LOCALE).casefold()
        slug = self.request.query_params.get("slug", "").casefold()      
        title = self.request.query_params.get("title", "").casefold()
        trigger = self.request.query_params.get("trigger", "").casefold()
        tag = self.request.query_params.get("tag", "").casefold()



        locale_matches = []
        slug_matches = [] if slug else all_match_ids
        title_matches = [] if title else all_match_ids
        trigger_matches = [] if trigger else all_match_ids
        tag_matches = [] if tag else all_match_ids



        

        print(f"BEFORE GOING INTO DRAFTS SLUG IS {slug_matches}")
        if return_drafts:
            print("")
            print("**** DRAFT QUERYSET ****")
            print("")
            
            print(f"Draft Queryset = {draft_queryset.count()} items")
            for dp in draft_queryset:
                # print(f"Draft Page: {dp.pk} - {dp.title} - {dp.slug}")
                l_rev = dp.get_latest_revision_as_object()
                if locale == l_rev.locale.language_code.casefold():
                    # print(f"    Locale match for DP {dp.id}")
                    locale_matches.append(dp.pk)
               
                if slug and slug in l_rev.slug.casefold():
                    # print(f"    Slug match for DP {dp.id} -> {slug} in {l_rev.slug.casefold()}")
                    slug_matches.append(dp.pk)
               
                if title and title in l_rev.title.casefold():
                    # print(f"    Title match for DP {dp.id} -> {title} in {l_rev.title.casefold()}")
                    title_matches.append(dp.pk)
                             
                if trigger:
                    l_rev_triggers = [t.name.casefold() for t in l_rev.triggers.all() if t]
                    # print(f"    Trigger param supplied `{trigger}` and dp has triggers {l_rev_triggers}")
                    
                    # print(f"Lrev triggers: {l_rev_triggers}")
                    for t in l_rev_triggers:
                        if trigger in t:
                            # print(f"    Trigger match for DP {dp.id}")
                            trigger_matches.append(dp.pk)
                            
                if tag:
                    l_rev_tags = [t.name.casefold() for t in l_rev.tags.all() if t]
                    # print(f"    Tag param supplied `{tag}` and dp has tags {l_rev_tags}")
                    
                    # print(f"Lrev tags: {l_rev_tags}")
                    for t in l_rev_tags:
                        if tag in t:
                            # print(f"    Tag match for DP {dp.id}")
                            tag_matches.append(dp.pk)
                                       
    
        # print("")
        # print(f"    Locale matches from drafts: {len(locale_matches)} items - {locale_matches}")
        # print(f"    Slug matches from drafts: {len(slug_matches)} items - {slug_matches}")
        # print(f"    Title matches from drafts: {len(title_matches)} items - {title_matches}")
        # print(f"    Trigger matches from drafts: {len(trigger_matches)} items - {trigger_matches}")
        # print(f"    Tag matches from drafts: {len(tag_matches)} items - {tag_matches}")
        # print("")

        print("")
        print(f"    Locale matches from drafts: {len(locale_matches)} items")
        print(f"    Slug matches from drafts: {len(slug_matches)} items")
        print(f"    Title matches from drafts: {len(title_matches)} items")
        print(f"    Trigger matches from drafts: {len(trigger_matches)} items")
        print(f"    Tag matches from drafts: {len(tag_matches)} items")
        print("")
        
        locale_set = set(locale_matches)
        slug_set = set(slug_matches)
        title_set = set(title_matches)
        trigger_set = set(trigger_matches)
        tag_set = set(tag_matches)      

        unique_draft_matches = locale_set.intersection(slug_set,title_set,locale_set, trigger_set, tag_set)
        unique_draft_list = list(unique_draft_matches)
        print(f"Draft matches combined: {len(unique_draft_list)} items - {unique_draft_list}")
        print("")


        # if title:
            # queryset_to_return = queryset_to_return.filter(title__icontains=title)
        print("")
        print("**** LIVE QUERYSET ****")
        print("")

        live_queryset = all_queryset.filter(live=True, has_unpublished_changes="False")
        print(f"Live Queryset = {live_queryset.count()} items - {[l.id for l in live_queryset.all() if l]}")

        if locale:
            # print(f"    Locale param supplied: {locale}")
            live_queryset = live_queryset.filter(locale__language_code=locale)
            print(f"    Live Queryset after locale = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}")      

        if slug:
            live_queryset = live_queryset.filter(slug__icontains=slug)
            print(f"    Live Queryset after slug = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}")

        if title:
            live_queryset = live_queryset.filter(title__icontains=title)
            print(f"    Live Queryset after title = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}")    
       
 

        if trigger:
            ids = []
            for t in TriggeredContent.objects.filter(tag__name__iexact=trigger.strip()):
                # print(f"    Trigger match {t.tag}")
                ids.append(t.content_object_id)

            live_queryset = live_queryset.filter(id__in=ids)
            print(f"    Live Queryset after triggers =  {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}")
       
        if tag:
            ids = []
            for t in ContentPageTag.objects.filter(tag__name__iexact=tag):
                ids.append(t.content_object_id)

            live_queryset = live_queryset.filter(id__in=ids)

            print(f"    Live Queryset afer tags = {live_queryset.count()} items -> {[l.id for l in live_queryset.all() if l]}")

 

        
        queryset_to_return = live_queryset | ContentPage.objects.filter(id__in=unique_draft_list)

        print("")
        print("**** QUERYSET TO RETURN ****")
        print("")
        # [t.name.casefold() for t in l_rev.tags.all() if t]
        print(f"QuerysetToReturn IDs: {[l.id for l in queryset_to_return.all() if l]}")
        print("")       

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
