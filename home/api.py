from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.viewsets import GenericViewSet
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from .serializers import ContentPageSerializer, ContentPageRatingSerializer, LanguagesSerializer
from .models import ContentPage, ContentPageTag, ContentPageIndex, ContentPageRating
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from wagtail.core.models import Locale, Page



class ContentPagesViewSet(PagesAPIViewSet):
    base_serializer_class = ContentPageSerializer

    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "page",
            "include_in_footer",
            "parent",
            "ancestors"
        ]
    )
    pagination_class = PageNumberPagination

    # @method_decorator(cache_page(60 * 60 * 2))
    def get(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).get(self, request, *args, **kwargs)

    # @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request, *args, **kwargs):
        super(ContentPagesViewSet, self).list(self, request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(ContentPagesViewSet, self).get_queryset()
        parent = self.request.query_params.get("parent")
        if parent is not None:
            parent_page = Page.objects.get(id=parent).specific
            queryset = ContentPage.objects.child_of(parent_page).live()
        ancestors = self.request.query_params.get("ancestors")
        if ancestors is not None:
            page = Page.objects.get(id=parent).specific
            queryset = ContentPage.objects.ancestor_of(page).live()
        tag = self.request.query_params.get("tag")
        if tag is not None:
            ids = []
            for t in ContentPageTag.objects.all():
                if t.tag.name == tag:
                    ids.append(t.content_object_id)
            queryset = queryset.filter(id__in=ids)
        include_in_footer = self.request.query_params.get("include_in_footer")
        if include_in_footer is not None:
            queryset = queryset.filter(contentpage__include_in_footer=include_in_footer)
        return queryset


class ContentPageIndexViewSet(PagesAPIViewSet):
    pagination_class = PageNumberPagination

    def get_queryset(self):
        return ContentPageIndex.objects.live()


class LanguagesViewSet(GenericViewSet, ListModelMixin):
    pagination_class = None
    queryset = Locale.objects.all()
    serializer_class = LanguagesSerializer


class ContentPageRatingViewSet(GenericViewSet, CreateModelMixin):
    queryset = ContentPageRating.objects.all()
    serializer_class = ContentPageRatingSerializer
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        if "page" in request.data:
            try:
                page = ContentPage.objects.get(id=request.data["page"])
                request.data["revision"] = page.get_latest_revision().id
            except ContentPage.DoesNotExist:
                raise ValidationError({"page": ["Page matching query does not exist."]})

        return super().create(request, *args, **kwargs)


api_router = WagtailAPIRouter("wagtailapi")

api_router.register_endpoint("pages", ContentPagesViewSet)
api_router.register_endpoint("indexes", ContentPageIndexViewSet)
api_router.register_endpoint("images", ImagesAPIViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)
