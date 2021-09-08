from rest_framework.pagination import PageNumberPagination
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .serializers import ContentPageSerializer
from.models import ContentPageTag


class ContentPagesViewSet(PagesAPIViewSet):
    base_serializer_class = ContentPageSerializer
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union([
        'tag',
        'page',
    ])
    pagination_class = PageNumberPagination

    # cache queryset for an hour
    # @method_decorator(cache_page(60 * 60))
    def get_queryset(self):
        queryset = super(ContentPagesViewSet, self).get_queryset()
        tag = self.request.query_params.get('tag')
        if tag is not None:
            ids = []
            for t in ContentPageTag.objects.all():
                if t.tag.name == tag:
                    ids.append(t.content_object_id)
            queryset = queryset.filter(id__in=ids)
        return queryset


api_router = WagtailAPIRouter('wagtailapi')

api_router.register_endpoint('pages', ContentPagesViewSet)
api_router.register_endpoint('images', ImagesAPIViewSet)
api_router.register_endpoint('documents', DocumentsAPIViewSet)
