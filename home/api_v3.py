from django.urls import path
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
            if "qa" in request.GET and request.GET["qa"] == "True":
                instance = self.get_object().get_latest_revision_as_object()
                # instance = WhatsAppTemplate.objects.get(
                #     id=pk
                # ).get_latest_revision_as_object()
                # serializer = WhatsAppTemplateSerializer(
                #     instance, context={"request": request}
                # )
                # return Response(serializer.data)
            else:
                # WhatsAppTemplate.objects.get(id=pk)
                instance = self.get_object()
        except Exception as e:
            # TODO: Handle this better
            print(f"Exception = {e}")

        serializer = WhatsAppTemplateSerializer(instance, context={"request": request})
        return Response(serializer.data)
        # return super().detail_view(request, pk)

    def listing_view(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        queryset_list = self.paginate_queryset(queryset)
        serializer = WhatsAppTemplateSerializer(
            queryset_list, context={"request": request}, many=True
        )
        return self.get_paginated_response(serializer.data)
        # return super().listing_view(request)

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

    def get_serializer_context(self):
        """
        The serialization context differs between listing and detail views.
        """
        return {
            "request": self.request,
            "view": self,
            "router": self.request.wagtailapiv3_router,
        }

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
            "qa",
            "whatsapp",
            "viber",
            "messenger",
            "web",
            "s",
            "sms",
            "ussd",
        ]
    )

    pagination_class = PageNumberPagination

    def detail_view(self, request, pk=None, slug=None):
        if slug is not None:
            self.lookup_field = "slug"

        instance = self.get_object().get_latest_revision_as_object()
        serializer = ContentPageSerializerV3(instance, context={"request": request})
        return Response(serializer.data)
        # return super().detail_view(request, param)

    def listing_view(self, request, *args, **kwargs):
        # If this request is flagged as QA then we should display the pages that have the filtering tags
        # or triggers in their draft versions
        if "qa" in request.GET and request.GET["qa"] == "True":
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

            queryset = self.get_queryset()

            self.check_query_parameters(queryset)
            queryset = self.filter_queryset(queryset)
            queryset = queryset | ContentPage.objects.filter(id__in=have_new_triggers)
            queryset = queryset | ContentPage.objects.filter(id__in=have_new_tags)

            queryset_list = self.paginate_queryset(queryset)

            serializer = ContentPageSerializerV3(
                queryset_list, context={"request": request}, many=True
            )
            return self.get_paginated_response(serializer.data)

        queryset = self.get_queryset()
        queryset_list = self.paginate_queryset(queryset)

        serializer = ContentPageSerializerV3(
            queryset_list, context={"request": request}, many=True
        )

        return self.get_paginated_response(serializer.data)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")
        queryset = ContentPage.objects.live().prefetch_related("locale")

        if qa:
            queryset = queryset | ContentPage.objects.not_live()

        if "web" in self.request.query_params:
            queryset = queryset.filter(enable_web=True)
        elif "whatsapp" in self.request.query_params:
            queryset = queryset.filter(enable_whatsapp=True)
        elif "sms" in self.request.query_params:
            queryset = queryset.filter(enable_sms=True)
        elif "ussd" in self.request.query_params:
            queryset = queryset.filter(enable_ussd=True)
        elif "messenger" in self.request.query_params:
            queryset = queryset.filter(enable_messenger=True)
        elif "viber" in self.request.query_params:
            queryset = queryset.filter(enable_viber=True)

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
