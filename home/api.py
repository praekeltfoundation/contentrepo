from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet

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
        ["tag", "trigger", "page", "qa", "whatsapp", "viber", "messenger", "web"]
    )
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).get(self, request, *args, **kwargs)

    def detail_view(self, request, pk):
        try:
            ContentPage.objects.get(id=pk).save_page_view(request.query_params)
        except ContentPage.DoesNotExist:
            raise ValidationError({"page": ["Page matching query does not exist."]})

        return super().detail_view(request, pk)

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).list(self, request, *args, **kwargs)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")
        queryset = ContentPage.objects.live()

        if qa:
            queryset = queryset | ContentPage.objects.not_live()

        if "web" in self.request.query_params:
            queryset = queryset.filter(enable_web=True)
        elif "whatsapp" in self.request.query_params:
            queryset = queryset.filter(enable_whatsapp=True)
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
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(["page"])
    pagination_class = PageNumberPagination
    search_fields = ["name", "profile_fields"]
    filter_backends = (SearchFilter,)

    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, *args, **kwargs):
        super(OrderedContentSetViewSet, self).get(self, request, *args, **kwargs)

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        super(OrderedContentSetViewSet, self).list(self, request, *args, **kwargs)


api_router = WagtailAPIRouter("wagtailapi")

api_router.register_endpoint("pages", ContentPagesViewSet)
api_router.register_endpoint("indexes", ContentPageIndexViewSet)
api_router.register_endpoint("images", ImagesAPIViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)

api_router.register_endpoint("orderedcontent", OrderedContentSetViewSet)
