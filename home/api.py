from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtailmedia.api.views import MediaAPIViewSet

from .models import Assessment, AssessmentTag, OrderedContentSet
from .serializers import (
    AssessmentSerializer,
    ContentPageSerializer,
    OrderedContentSetSerializer,
)

from .models import (  # isort:skip
    ContentPage,
    ContentPageIndex,
    ContentPageTag,
    TriggeredContent,
    WhatsAppTemplate,
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
            raise NotFound({"page": ["Page matching query does not exist."]})

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
        "pages",
    ]
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(["page", "qa"])
    pagination_class = PageNumberPagination
    search_fields = ["name", "profile_fields"]
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")

        if qa:
            # return the latest revision for each OrderedContentSet
            queryset = OrderedContentSet.objects.all().order_by("latest_revision_id")
            for ocs in queryset:
                latest_revision = ocs.revisions.order_by("-created_at").first()
                if latest_revision:
                    latest_revision = latest_revision.as_object()
                    ocs.name = latest_revision.name
                    ocs.pages = latest_revision.pages
                    ocs.profile_fields = latest_revision.profile_fields

        else:
            queryset = OrderedContentSet.objects.filter(live=True).order_by(
                "last_published_at"
            )
        return queryset


class WhatsAppTemplateViewset(BaseAPIViewSet):
    model = WhatsAppTemplate
    listing_default_fields = BaseAPIViewSet.listing_default_fields + [
        "name",
        "body",
    ]
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(["qa"])
    pagination_class = PageNumberPagination
    search_fields = ["name", "body"]
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")

        if qa:
            # return the latest revision for each WhatsApp Template
            queryset = WhatsAppTemplate.objects.all().order_by("latest_revision_id")
            for wat in queryset:
                latest_revision = wat.revisions.order_by("-created_at").first()
                if latest_revision:
                    latest_revision = latest_revision.as_object()
                    wat.name = latest_revision.name
                    wat.pages = latest_revision.pages
                    wat.profile_fields = latest_revision.profile_fields

        else:
            queryset = WhatsAppTemplate.objects.filter(live=True).order_by(
                "last_published_at"
            )
        return queryset


class AssessmentViewSet(BaseAPIViewSet):
    base_serializer_class = AssessmentSerializer
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "qa",
        ]
    )
    model = Assessment
    body_fields = BaseAPIViewSet.body_fields + [
        "title",
        "slug",
        "version",
        "locale",
        "tags",
        "high_result_page",
        "high_inflection",
        "medium_result_page",
        "medium_inflection",
        "low_result_page",
        "skip_threshold",
        "skip_high_result_page",
        "generic_error",
        "questions",
    ]
    listing_default_fields = BaseAPIViewSet.listing_default_fields + [
        "title",
        "slug",
        "version",
        "locale",
        "tags",
        "high_result_page",
        "high_inflection",
        "medium_result_page",
        "medium_inflection",
        "low_result_page",
        "low_inflection",
        "skip_threshold",
        "skip_high_result_page",
        "generic_error",
        "questions",
    ]
    pagination_class = PageNumberPagination
    search_fields = ["title"]
    filter_backends = (SearchFilter,)

    def get_queryset(self):
        qa = self.request.query_params.get("qa")

        if qa:
            # return the latest revision for each Assessment
            queryset = Assessment.objects.all().order_by("latest_revision_id")
            for assessment in queryset:
                latest_revision = assessment.revisions.order_by("-created_at").first()
                if latest_revision:
                    latest_revision = latest_revision.as_object()
                    # set the assessment's details to that of the latest revision
                    assessment.title = latest_revision.title
                    assessment.slug = latest_revision.slug
                    assessment.version = latest_revision.version
                    assessment.locale = latest_revision.locale
                    assessment.tags = latest_revision.tags
                    assessment.high_result_page = latest_revision.high_result_page
                    assessment.high_inflection = latest_revision.high_inflection
                    assessment.medium_result_page = latest_revision.medium_result_page
                    assessment.medium_inflection = latest_revision.medium_inflection
                    assessment.low_result_page = latest_revision.low_result_page
                    assessment.skip_threshold = latest_revision.skip_threshold
                    assessment.skip_high_result_page = (
                        latest_revision.skip_high_result_page
                    )
                    assessment.generic_error = latest_revision.generic_error
                    assessment.questions = latest_revision.questions

        else:
            queryset = Assessment.objects.filter(live=True).order_by(
                "last_published_at"
            )

        tag = self.request.query_params.get("tag")
        if tag is not None:
            ids = []
            for t in AssessmentTag.objects.filter(tag__name__iexact=tag):
                ids.append(t.content_object_id)
            queryset = queryset.filter(id__in=ids)
        return queryset


api_router = WagtailAPIRouter("wagtailapi")

api_router.register_endpoint("pages", ContentPagesViewSet)
api_router.register_endpoint("indexes", ContentPageIndexViewSet)
api_router.register_endpoint("images", ImagesAPIViewSet)
api_router.register_endpoint("documents", DocumentsAPIViewSet)
api_router.register_endpoint("media", MediaAPIViewSet)
api_router.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router.register_endpoint("orderedcontent", OrderedContentSetViewSet)
api_router.register_endpoint("assessment", AssessmentViewSet)
