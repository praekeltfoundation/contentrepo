from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtailmedia.api.views import MediaAPIViewSet

from .models import OrderedContentSet
from .serializers import ContentPageSerializer, OrderedContentSetSerializer

from .models import (  # isort:skip
    ContentPage,
    ContentPageIndex,
    ContentPageTag,
    TriggeredContent,
)


class ContentPagesViewSet(PagesAPIViewSet):
    base_serializer_class = ContentPageSerializer
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

    def detail_view(self, request, pk):
        try:
            if "qa" in request.GET and request.GET["qa"] == "True":
                instance = ContentPage.objects.get(
                    id=pk
                ).get_latest_revision_as_object()
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
            else:
                ContentPage.objects.get(id=pk).save_page_view(request.query_params)
        except ContentPage.DoesNotExist:
            raise ValidationError({"page": ["Page matching query does not exist."]})

        return super().detail_view(request, pk)

    def listing_view(self, request, *args, **kwargs):
        # If this request is flagged as QA then we should display the pages that have the filtering tags
        # or triggers in their draft versions
        if "qa" in request.GET and request.GET["qa"] == "True":
            tag = self.request.query_params.get("tag")
            trigger = self.request.query_params.get("trigger")
            have_new_triggers = []
            have_new_tags = []
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
            serializer = self.get_serializer(queryset_list, many=True)
            return self.get_paginated_response(serializer.data)

        return super().listing_view(request)

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
        if tag is not None:
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
        s = self.request.query_params.get("s")
        if s is not None:
            from .word_embedding import retrieve_top_n_content_pieces

            platform = "web"
            if "whatsapp" in self.request.query_params:
                platform = "whatsapp"
            if "sms" in self.request.query_params:
                platform = "sms"
            if "ussd" in self.request.query_params:
                platform = "ussd"
            elif "messenger" in self.request.query_params:
                platform = "messenger"
            elif "viber" in self.request.query_params:
                platform = "viber"

            ids = retrieve_top_n_content_pieces(s, queryset, platform=platform)
            queryset = queryset.filter(id__in=ids)
        return queryset


class ContentPageIndexViewSet(PagesAPIViewSet):
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return ContentPageIndex.objects.live()


class OrderedContentSetViewSet(BaseAPIViewSet):
    model = OrderedContentSet
    base_serializer_class = OrderedContentSetSerializer
    listing_default_fields = BaseAPIViewSet.listing_default_fields + [
        "name",
        "profile_fields",
    ]
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(["page", "qa"])
    pagination_class = PageNumberPagination
    search_fields = ["name", "profile_fields"]
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")

        if qa:
            # return the latest revision for each OrderedContentSet
            queryset = OrderedContentSet.objects.all()
            for ocs in queryset:
                latest_revision = ocs.revisions.order_by("-created_at").first()
                if latest_revision:
                    latest_revision = latest_revision.as_object()
                    ocs.profile_fields = latest_revision.profile_fields

        else:
            queryset = OrderedContentSet.objects.all()
        return queryset


api_router = WagtailAPIRouter("wagtailapi")

api_router.register_endpoint("pages", ContentPagesViewSet)
api_router.register_endpoint("indexes", ContentPageIndexViewSet)
api_router.register_endpoint("images", ImagesAPIViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)
api_router.register_endpoint("media", MediaAPIViewSet)

api_router.register_endpoint("orderedcontent", OrderedContentSetViewSet)
