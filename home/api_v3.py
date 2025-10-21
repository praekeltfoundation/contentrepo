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

from home.serializers_v3 import ContentPageSerializerV3, WhatsAppTemplateSerializer

from .models import (  # isort:skip
    ContentPage,
    ContentPageTag,
    TriggeredContent,
    WhatsAppTemplate,
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

    @extend_schema(
        operation_id="api_v3_whatsapptemplates_detail_by_id",
        parameters=[
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest content, regardless of live/draft status",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
        ],
    )
    def detail_view_by_id(self, request, pk):
        return self.process_detail_view(request, pk=pk)

    @extend_schema(
        operation_id="api_v3_whatsapptemplates_detail_by_slug",
        parameters=[
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest content, regardless of live/draft status",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
            OpenApiParameter(
                name="locale",
                description="Filter by exact match on locale",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "blank",
                        value="",
                    ),
                    OpenApiExample(
                        "English",
                        value="en",
                    ),
                ],
            ),
        ],
    )
    def detail_view_by_slug(self, request, slug):
        return self.process_detail_view(request, slug=slug)

    @extend_schema(
        operation_id="api_v3_whatsapptemplates_list_all",
        parameters=[
            OpenApiParameter(
                name="slug",
                description="Filter by partial match on slug",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "blank",
                        value="",
                    ),
                    OpenApiExample(
                        "Template",
                        value="template",
                    ),
                ],
            ),
            OpenApiParameter(
                name="locale",
                description="Filter by exact match on locale",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "blank",
                        value="",
                    ),
                    OpenApiExample(
                        "English",
                        value="en",
                    ),
                ],
            ),
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest pages, regardless of live/draft status",
                required=False,
                type=bool,
                examples=[
                    OpenApiExample(
                        "None",
                        value="False",
                    ),
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
        ],
        responses={
            201: WhatsAppTemplateSerializer,
        },
    )
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
        # draft_queryset = (
        #     WhatsAppTemplate.objects.all()
        #     .order_by("latest_revision_id")
        #     .prefetch_related("locale")
        # )
        # print("*************")
        # print("*************")
        # draft_queryset = (
        #     WhatsAppTemplate.objects.filter(has_unpublished_changes=True)
        #     .order_by("latest_revision_id")
        #     .prefetch_related("locale")
        # )

    #     for wt in draft_queryset:
    #         latest_revision = wt.revisions.order_by("-created_at").first()
    #         if latest_revision:
    #             latest_revision = latest_revision.as_object()
    #             print(f"Latest revision for template {wt.slug} is {latest_revision.id}")

    #     for dq in draft_queryset:
    #         print(
    #             f"""
    # DraftQS item: {dq} 
    # live={dq.live}  
    # latest_rev_id={dq.latest_revision_id}
    # live_rev_id={dq.live_revision_id}
    #         """
    #         )
    #         # print(vars(dq))
    #         for rev in dq.revisions.all():
    #             print(rev.id)
    #             # print("")
    #             # print(vars(rev))

        live_queryset = WhatsAppTemplate.objects.filter(
            has_unpublished_changes=False
        ).prefetch_related("locale")

        live_queryset = draft_queryset.filter(live=True).order_by("last_published_at")

        queryset_to_return = live_queryset

        return_drafts = (
            self.request.query_params.get("return_drafts", "").lower() == "true"
        )

        if return_drafts:
            queryset_to_return = draft_queryset | live_queryset
        else:
            queryset_to_return = live_queryset

        # for qtr in queryset_to_return:
        #     print(f"Draft QTR item: {qtr} ")
        #     # print(f"""
        #     # Draft QTR item: {qtr}
        #     # live={qtr.live}
        #     # latest_rev_id={qtr.latest_revision_id}
        #     # live_rev_id={qtr.live_revision_id}
        #     # """)
        #     # print(vars(qtr))
        #     # for rev in qtr.revisions.all():
        #     #     print(rev.id)
        #     #     # print("")
        #     #     # print(vars(rev))

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

    def process_detail_view(self, request, pk=None, slug=None):
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

    @extend_schema(
        operation_id="api_v3_pages_detail_by_id",
        parameters=[
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest content, regardless of live/draft status",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
            OpenApiParameter(
                name="channel",
                description="Filter by exact match on channel",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Web",
                        value="web",
                    ),
                    OpenApiExample(
                        "SMS",
                        value="sms",
                    ),
                    OpenApiExample(
                        "Whatsapp",
                        value="whatsapp",
                    ),
                    OpenApiExample(
                        "Messenger",
                        value="messenger",
                    ),
                    OpenApiExample(
                        "Viber",
                        value="viber",
                    ),
                ],
            ),
        ],
    )
    def detail_view_by_id(self, request, pk):
        return self.process_detail_view(request, pk=pk)

    @extend_schema(
        operation_id="api_v3_pages_detail_by_slug",
        parameters=[
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest content, regardless of live/draft status",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
            OpenApiParameter(
                name="channel",
                description="Filter by exact match on channel",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Web",
                        value="web",
                    ),
                    OpenApiExample(
                        "SMS",
                        value="sms",
                    ),
                    OpenApiExample(
                        "Whatsapp",
                        value="whatsapp",
                    ),
                    OpenApiExample(
                        "Messenger",
                        value="messenger",
                    ),
                    OpenApiExample(
                        "Viber",
                        value="viber",
                    ),
                ],
            ),
        ],
    )
    def detail_view_by_slug(self, request, slug):
        return self.process_detail_view(request, slug=slug)

    @extend_schema(
        operation_id="api_v3_pages_list_all",
        parameters=[
            OpenApiParameter(
                name="slug",
                description="Filter by partial match on slug",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "blank",
                        value="",
                    ),
                    OpenApiExample(
                        "Template",
                        value="template",
                    ),
                ],
            ),
            OpenApiParameter(
                name="locale",
                description="Filter by exact match on locale",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "blank",
                        value="",
                    ),
                    OpenApiExample(
                        "English",
                        value="en",
                    ),
                ],
            ),
            OpenApiParameter(
                name="title",
                description="Filter by partial match on title",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "Example 1",
                        value="page",
                    ),
                ],
            ),
            OpenApiParameter(
                name="channel",
                description="Filter by exact match on channel",
                required=False,
                type=str,
                examples=[
                    OpenApiExample(
                        "None",
                        value="",
                    ),
                    OpenApiExample(
                        "Whatsapp",
                        value="whatsapp",
                    ),
                    OpenApiExample(
                        "Messenger",
                        value="messenger",
                    ),
                ],
            ),
            OpenApiParameter(
                name="return_drafts",
                description="Returns all latest pages, regardless of live/draft status",
                required=False,
                type=bool,
                examples=[
                    OpenApiExample(
                        "None",
                        value="False",
                    ),
                    OpenApiExample(
                        "True",
                        value="true",
                    ),
                    OpenApiExample(
                        "False",
                        value="false",
                    ),
                ],
            ),
        ],
        responses={
            201: ContentPageSerializerV3,
        },
    )
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
        print("")
        print("****************************************************")
        print("****************************************************")
        print("")

        draft_queryset = (
            ContentPage.objects.not_live()
            .order_by("latest_revision_id")
            .prefetch_related("locale")
        )
        draft_queryset = draft_queryset.filter(locale__language_code=DEFAULT_LOCALE)
        print("")
        print("**************************")
        print(f"Draft Queryset: {draft_queryset.count()} items")
        print("**************************")
        for dq in draft_queryset:

            latest_revision = dq.revisions.order_by("-created_at").first()
            if latest_revision:
                latest_revision = latest_revision.as_object()
                # ocs.name = latest_revision.name
                # ocs.pages = latest_revision.pages
                # ocs.profile_fields = latest_revision.profile_fields
                # ocs.locale = latest_revision.locale
                # dq.slug = latest_revision.slug
                dq = latest_revision

            print(
                f"""
DQS item: {dq.slug}
    title={dq.title}   
    live={dq.live}
    locale={dq.locale.language_code}
    latest_rev_id={dq.latest_revision_id}
    live_rev_id={dq.live_revision_id}"""
            )
            print(f"     Revisions:{[item.id for item in dq.revisions.all()]} ")

        live_queryset = ContentPage.objects.live().prefetch_related("locale")
        live_queryset = live_queryset.filter(locale__language_code=DEFAULT_LOCALE)

        print("")
        print("**************************")
        print(f"Live Queryset: {live_queryset.count()} items")
        print("**************************")
        for lq in live_queryset:
            print(
                f"""
LQS item: {lq.slug} 
    live={lq.live}
    locale={lq.locale.language_code}   
    latest_rev_id={lq.latest_revision_id}
    live_rev_id={lq.live_revision_id}"""
            )
            # print("     Revisions:")
            # print(vars(lq))

            print(f"    Revisions:{[item.id for item in lq.revisions.all()]} ")

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
        locale = self.request.query_params.get("locale", DEFAULT_LOCALE)
        if locale:
            queryset_to_return = queryset_to_return.filter(
                locale__language_code=DEFAULT_LOCALE
            )

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

        print("")
        print("**************************")
        print(f"Queryset to return: {queryset_to_return.count()} items")
        print("**************************")
        for qtr in queryset_to_return:
            latest_revision = qtr.revisions.order_by("-created_at").first()
            if latest_revision:
                latest_revision = latest_revision.as_object()
                # ocs.name = latest_revision.name
                # ocs.pages = latest_revision.pages
                # ocs.profile_fields = latest_revision.profile_fields
                # ocs.locale = latest_revision.locale
                # dq.slug = latest_revision.slug
                qtr = latest_revision
            print(
                f"""
QTR item: {qtr.slug} 
    live={qtr.live}
    locale={qtr.locale.language_code}   
    latest_rev_id={qtr.latest_revision_id}
    live_rev_id={qtr.live_revision_id}"""
            )
            print(f"    Revisions:{[item.id for item in qtr.revisions.all()]} ")

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
