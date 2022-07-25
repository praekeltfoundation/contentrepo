from rest_framework.pagination import PageNumberPagination
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from .serializers import ContentPageSerializer
from .models import ContentPage, ContentPageTag, ContentPageIndex, TriggeredContent
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class ContentPagesViewSet(PagesAPIViewSet):
    base_serializer_class = ContentPageSerializer
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "trigger",
            "page",
        ]
    )
    pagination_class = PageNumberPagination

    @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).get(self, request, *args, **kwargs)

    def detail_view(self, request, pk):
        ContentPage.objects.get(id=pk).save_page_view(request.query_params)
        return super().detail_view(request, pk)

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).list(self, request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(ContentPagesViewSet, self).get_queryset()
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


api_router = WagtailAPIRouter("wagtailapi")

api_router.register_endpoint("pages", ContentPagesViewSet)
api_router.register_endpoint("indexes", ContentPageIndexViewSet)
api_router.register_endpoint("images", ImagesAPIViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)
