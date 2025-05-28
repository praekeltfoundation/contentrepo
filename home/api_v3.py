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

    # body_fields = [
    #     # "id",
    #     "slug",
    #     "locale",
    #     "name",
    #     "category",
    #     "image",
    #     "message",
    #     "example_values",
    #     "buttons",
    #     "revision",
    #     "status",
    #     "submission_name",
    #     "submission_status",
    #     "submission_result",
    # ]
    # listing_default_fields = [
    #     # "id",
    #     "slug",
    #     "locale",
    #     "name",
    #     "category",
    #     "image",
    #     "message",
    #     "example_values",
    #     "buttons",
    #     "revision",
    #     "status",
    #     "submission_name",
    #     "submission_status",
    #     "submission_result",
    # ]
    pagination_class = PageNumberPagination
    search_fields = [
        "name",
    ]
    filter_backends = (SearchFilter,)

    def detail_view(self, request, pk):
        print("Detail View")
        try:
            if "qa" in request.GET and request.GET["qa"] == "True":
                instance = WhatsAppTemplate.objects.get(
                    id=pk
                ).get_latest_revision_as_object()
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
            else:
                WhatsAppTemplate.objects.get(id=pk)
        except Exception as e:
            # TODO: Handle this better
            print(f"Exception = {e}")

        return super().detail_view(request, pk)

    def listing_view(self, request, *args, **kwargs):
        print("Listing view here")
        queryset = self.get_queryset()
        queryset_list = self.paginate_queryset(queryset)
        serializer = WhatsAppTemplateSerializer(
            queryset_list, context={"request": request}, many=True
        )
        print(f"Serializer in listing view is {serializer}")
        print("")
        print("")
        print(f"Serializer DATA in listing view is {serializer.data}")
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
                    wat.name = latest_revision.name

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


# class ContentPagesViewSetV3(PagesAPIViewSet):
#     model = ContentPage
#     serializer_class = ContentPageSerializerV3
#     base_serializer_class = ContentPageSerializerV3
#     meta_fields = []
#     known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
#         [
#             "tag",
#             "trigger",
#             "page",
#             "qa",
#             "whatsapp",
#             "viber",
#             "messenger",
#             "web",
#             "s",
#             "sms",
#             "ussd",
#         ]
#     )
#     body_fields = [
#         "slug",
#         "locale",
#         "title",
#         "subtitle",
#         "messages",
#         # "buttons",
#         # "list_items",
#         "tags",
#         "triggers",
#         "has_children",
#         "related_pages",
#     ]
#     listing_default_fields = [
#         "slug",
#         "locale",
#         "title",
#         "subtitle",
#         "messages",
#         "buttons",
#         "list_items",
#         "example_values",
#         "tags",
#         "triggers",
#         "has_children",
#         "related_pages",
#     ]
#     fields = [
#         "slug",
#         "locale",
#         "title",
#         "subtitle",
#         "messages",
#         "buttons",
#         "list_items",
#         "tags",
#         "triggers",
#         "has_children",
#         "related_pages",
#     ]
#     pagination_class = PageNumberPagination

#     def detail_view(self, request, pk):
#         try:
#             if "qa" in request.GET and request.GET["qa"] == "True":
#                 instance = ContentPage.objects.get(
#                     id=pk
#                 ).get_latest_revision_as_object()
#                 serializer = self.get_serializer(instance)
#                 print(f"Serializer -{type(serializer)}")
#                 return Response(serializer.data)

#                 # print(f"V3 Instance thingy{self.get_serializer(instance)}")

#                 # return Response(serializer.data)
#             else:
#                 ContentPage.objects.get(id=pk).save_page_view(request.query_params)
#         except ContentPage.DoesNotExist:
#             raise NotFound({"page": ["Page matching query does not exist."]})

#         return super().detail_view(request, pk)


#     # def get_queryset(self):
#     #     qa = self.request.query_params.get("qa")
#     #     queryset = ContentPage.objects.live().prefetch_related("locale")
#     #     if qa:
#     #         queryset = queryset | ContentPage.objects.not_live()

#     def get_queryset(self):
#         qa = self.request.query_params.get("qa")
#         queryset = ContentPage.objects.live().prefetch_related("locale")

#         if qa:
#             queryset = queryset | ContentPage.objects.not_live()

#         if "web" in self.request.query_params:
#             queryset = queryset.filter(enable_web=True)
#         elif "whatsapp" in self.request.query_params:
#             queryset = queryset.filter(enable_whatsapp=True)
#         elif "sms" in self.request.query_params:
#             queryset = queryset.filter(enable_sms=True)
#         elif "ussd" in self.request.query_params:
#             queryset = queryset.filter(enable_ussd=True)
#         elif "messenger" in self.request.query_params:
#             queryset = queryset.filter(enable_messenger=True)
#         elif "viber" in self.request.query_params:
#             queryset = queryset.filter(enable_viber=True)

#         tag = self.request.query_params.get("tag")
#         if tag:
#             ids = []
#             for t in ContentPageTag.objects.filter(tag__name__iexact=tag):
#                 ids.append(t.content_object_id)
#             queryset = queryset.filter(id__in=ids)
#         trigger = self.request.query_params.get("trigger")
#         if trigger is not None:
#             ids = []
#             for t in TriggeredContent.objects.filter(tag__name__iexact=trigger.strip()):
#                 ids.append(t.content_object_id)
#             queryset = queryset.filter(id__in=ids)

#         return queryset


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
    # body_fields = [
    #     "slug",
    #     "locale",
    #     "title",
    #     "subtitle",
    #     "messages",
    #     "buttons",
    #     "list_items",
    #     "tags",
    #     "triggers",
    #     "has_children",
    #     "related_pages",
    # ]
    # listing_default_fields = [
    #     "slug",
    #     "locale",
    #     "title",
    #     "subtitle",
    #     "messages",
    #     "buttons",
    #     "list_items",
    #     "example_values",
    #     "tags",
    #     "triggers",
    #     "has_children",
    #     "related_pages",
    # ]
    # fields = [
    #     "slug",
    #     "locale",
    #     "title",
    #     "subtitle",
    #     "messages",
    #     "buttons",
    #     "list_items",
    #     "tags",
    #     "triggers",
    #     "has_children",
    #     "related_pages",
    # ]
    pagination_class = PageNumberPagination

    def detail_view(self, request, pk=None, slug=None):
        print("Slug and ID Api Viewset")
        # param = pk
        if slug is not None:
            self.lookup_field = "slug"

        instance = self.get_object().get_latest_revision_as_object()
        # print(f"Instance = {type(instance)}")
        # print(f"Blah {type(ContentPageSerializerV3)}")
        serializer = ContentPageSerializerV3(instance, context={"request": request})
        # print("Whoop")
        # print(f"Serializer is {serializer.data}")
        return Response(serializer.data)
        # return super().detail_view(request, param)

    def listing_view(self, request, *args, **kwargs):
        # If this request is flagged as QA then we should display the pages that have the filtering tags
        # or triggers in their draft versions
        print("LIsting view")
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
            print(f"Serialiser = {type(serializer)}")

            return self.get_paginated_response(serializer.data)

            # print(
            #     f"about to return normal listing view - {super().listing_view(request)}"
            # )
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


api_router_v3 = WagtailAPIRouter("wagtailapiv3")
api_router_v3.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router_v3.register_endpoint("pages", ContentPagesV3APIViewset)
