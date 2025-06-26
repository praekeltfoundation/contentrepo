from typing import Any

from django.urls import path
from rest_framework.exceptions import NotFound
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

import pprint as pp


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
        # TODO: I couldn't get the call to get_serializer to work correctly,  Rudi can we try fix this together please
        # serializer = self.get_serializer(instance)
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

    def detail_view(self, request, pk=None, slug=None):
        if slug is not None:
            self.lookup_field = "slug"
        else:
            self.lookup_field = "pk"

        try:
            if "qa" in request.GET and request.GET["qa"].lower() == "true":
                instance = self.get_object().get_latest_revision_as_object()
            else:
                instance = self.get_object()

            instance.save_page_view(request.query_params)
            serializer = ContentPageSerializerV3(instance, context={"request": request})
            return Response(serializer.data)

        except Exception:
            raise NotFound({"page": ["Page matching query does not exist."]})

        return super().detail_view(request, pk)

    def listing_view(self, request, *args, **kwargs):
        # If this request is flagged as QA then we should display the pages that have the filtering tags
        # or triggers in their draft versions

        queryset = ContentPage.objects.live().prefetch_related("locale")
        self.check_query_parameters(queryset)

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        if return_drafts:
            queryset = queryset | ContentPage.objects.all().order_by(
                "latest_revision_id"
            )

        slug = self.request.query_params.get("slug", "").lower()
        # If a slug is proviced as query param, filter on that
        if slug != "":
            for cp in queryset:
                print(f"CP Title = {cp.title}")
                print(f"CP Slug = {cp.slug}")

            queryset = queryset.filter(slug=slug)

            print("SLug filteredQUERYSET BELOW ")
            pp.pprint(queryset)

        # TODO: Check this section properly.  Are these all we need to filter on? Should we add buttons, list items
        # ************ SECTION START

        tag = self.request.query_params.get("tag")
        trigger = self.request.query_params.get("trigger")
        have_new_triggers = []
        have_new_tags = []
        # have_new_buttons = []
        unpublished = ContentPage.objects.filter(has_unpublished_changes="True")

        for page in unpublished:
            latest_rev = page.get_latest_revision_as_object()

            if trigger and latest_rev.triggers.filter(name=trigger).exists():
                have_new_triggers.append(page.id)
            if tag and latest_rev.tags.filter(name=tag).exists():
                have_new_tags.append(page.id)

        #     queryset = self.get_queryset()
        # queryset = self.filter_queryset(queryset)
        queryset = queryset | ContentPage.objects.filter(id__in=have_new_triggers)
        queryset = queryset | ContentPage.objects.filter(id__in=have_new_tags)
        print("TagTrig filtered Queryset Below")
        pp.pprint(queryset)

        # ************ SECTION END

        queryset_list = self.paginate_queryset(queryset)

        serializer = ContentPageSerializerV3(
            queryset_list, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)

    def get_queryset(self) -> Any:
        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )
        queryset = ContentPage.objects.live().prefetch_related("locale")

        if return_drafts == "true":
            queryset = queryset | ContentPage.objects.not_live()

        channel = ""
        if "channel" in self.request.query_params:
            channel = self.request.query_params.get("channel", "").lower()

            match channel:
                case "web":
                    queryset = queryset.filter(enable_web=True)
                case "whatsapp":
                    queryset = queryset.filter(enable_whatsapp=True)
                case "sms":
                    queryset = queryset.filter(enable_sms=True)
                case "ussd":
                    queryset = queryset.filter(enable_ussd=True)
                case "messenger":
                    queryset = queryset.filter(enable_messenger=True)
                case "viber":
                    queryset = queryset.filter(enable_viber=True)
                case _:
                    raise NotFound(
                        {
                            "channel": [
                                f"channel matching query '{channel}' does not exist."
                            ]
                        }
                    )

        tag = self.request.query_params.get("tag")
        if tag:
            ids = []
            for t in ContentPageTag.objects.filter(tag__name__iexact=tag):
                ids.append(t.content_object_id)
            queryset = queryset.filter(id__in=ids)
        trigger = self.request.query_params.get("trigger")
        if trigger is not None:
            ids = []
            for t in TriggeredContent.objects.filter(tag__name__iexact=trigger.strip()):
                ids.append(t.content_object_id)
            queryset = queryset.filter(id__in=ids)

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


api_router_v3 = WagtailAPIRouter("wagtailapiv3_router")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
