import inspect

from rest_framework.exceptions import NotFound
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import BaseAPIViewSet, PagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from wagtail.models import ContentType, Locale, Revision
from wagtailmedia.api.views import MediaAPIViewSet

from home.custom_paginator import QaPaginator

from .models import Assessment, AssessmentTag, ContentPage, OrderedContentSet
from .serializers import (
    AssessmentSerializer,
    ContentPageSerializer,
    OrderedContentSetSerializer,
)

from .models import (  # isort:skip
    ContentPageIndex,
    ContentPageTag,
    TriggeredContent,
)


def caller_function():
    # Get the current frame
    current_frame = inspect.currentframe()
    # Get the frame of the caller (one level up in the stack)
    caller_frame = current_frame.f_back
    # Get the code object of the caller's frame
    caller_code = caller_frame.f_code
    # Extract the name of the function from the code object
    caller_name = caller_code.co_name
    print(f"        This function was called by: {caller_name}")
    # print(f"        This current_frame : {current_frame}")
    # print(f"        This caller_frame : {caller_frame}")
    # print(f"        This caller_code : {caller_code}")


class ContentPagesViewSet(PagesAPIViewSet):
    base_serializer_class = ContentPageSerializer
    serializer_class = ContentPageSerializer
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
            "slug",
        ]
    )
    listing_default_fields = BaseAPIViewSet.listing_default_fields + [
        "title",
        "html_url",
        "slug",
        "first_published_at",
    ]

    pagination_class = QaPaginator

    paginate_queryset_call_counter = 0
    get_paginated_response_call_counter = 0
    paginator_call_counter = 0

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """

        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method." % self.__class__.__name__
        )

        return self.serializer_class

    def get_queryset(self):
        print("**********************************Starting get_queryset")
        qa = self.request.query_params.get("qa", "")
        unpublished_page_ids = []
        if qa.lower() == "true":
            print("Using QA queryset")
            # TRY SUPER ON PAGINATORS
            queryset = ContentPage.objects.not_live().prefetch_related("locale")
            for page in queryset:
                unpublished_page_ids.append(page.id)

        else:
            queryset = ContentPage.objects.live().prefetch_related("locale")

        # if "web" in self.request.query_params:
        #     queryset = queryset.filter(enable_web=True)
        # elif "whatsapp" in self.request.query_params:
        #     queryset = queryset.filter(enable_whatsapp=True)
        # elif "sms" in self.request.query_params:
        #     queryset = queryset.filter(enable_sms=True)
        # elif "ussd" in self.request.query_params:
        #     queryset = queryset.filter(enable_ussd=True)
        # elif "messenger" in self.request.query_params:
        #     queryset = queryset.filter(enable_messenger=True)
        # elif "viber" in self.request.query_params:
        #     queryset = queryset.filter(enable_viber=True)

        # print("Filtered Channels, QS now ")
        # pp.pprint(list(queryset))
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

        latest_revisions = (
            Revision.page_revisions.get_queryset()
            .filter(content_type=ContentType.objects.get_for_model(ContentPage).id)
            .order_by("object_id", "-created_at")
            .distinct("object_id")
        )
        # print("Latest Revisions")
        # pp.pprint(list(latest_revisions))
        latest_unpublished_revisions = latest_revisions.filter(
            object_id__in=unpublished_page_ids
        )

        # queryset = latest_revisions
        # queryset = ContentPage.objects.all().order_by("latest_revision_id")
        # pp.pprint(list(queryset))
        # print(f"Queryset length is {len(queryset)}")
        for cp in queryset:
            latest_revision = cp.revisions.order_by("-created_at").first()
            if latest_revision:
                latest_revision_of_page = latest_revision.as_object()
                cp = latest_revision_of_page
                cp.save()
        # print(f"CP Slug is {cp.slug}")
        # pprint.pp(list(revisions), depth=1, width=100)
        # qa_queryset = ContentPage.objects.not_live().prefetch_related("locale")
        # print(f"QA Queryset (All not live) = {qa_queryset}")
        # live_queryset = ContentPage.objects.live().prefetch_related("locale")

        # print(f"Live Queryset (All live) = {live_queryset}")
        # print("")
        # pp.pprint(list(queryset))
        # print("")

        return queryset

    def detail_view(self, request, pk):
        try:
            if "qa" in request.GET and request.GET["qa"].lower() == "true":
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
        print("Listing View")
        slug = request.query_params.get("slug", "")
        if slug:
            instance = ContentPage.objects.get(slug=slug)
            print(f"Slug = {instance}")
            serializer = self.get_serializer(instance)

            return Response(serializer.data)
        if "qa" in request.GET and request.GET["qa"].lower() == "true":
            tag = self.request.query_params.get("tag")
            trigger = self.request.query_params.get("trigger")
            have_new_triggers = []
            have_new_tags = []
            unpublished = ContentPage.objects.filter(has_unpublished_changes="True")
            for page in unpublished:
                # print(f"Unpublished Page = {page.title}")
                latest_rev = page.get_latest_revision_as_object()
                if trigger and latest_rev.triggers.filter(name=trigger).exists():
                    have_new_triggers.append(page.id)
                if tag and latest_rev.tags.filter(name=tag).exists():
                    have_new_tags.append(page.id)

            queryset = self.get_queryset()

            # pp.pprint(list(queryset))
            # for cp in queryset:
            #     print(f"Page -> id = {cp.id}, LatestRev_id = {cp.latest_revision_id}")
            # pp.pprint(dict(vars(cp)))
            # self.check_query_parameters(queryset)
            # queryset = self.filter_queryset(queryset)
            # queryset = queryset | ContentPage.objects.filter(id__in=have_new_triggers)
            # queryset = queryset | ContentPage.objects.filter(id__in=have_new_tags)
            print("")
            print("About to call self.paginate_queryset")
            qa_paginator = QaPaginator()
            queryset_list = QaPaginator.paginate_queryset(
                qa_paginator, queryset=queryset, request=request
            )
            print("")
            print("About to call self.get_serializer")
            serializer = self.get_serializer(queryset_list, many=True)
            print("About to return self.get_paginated_response(serializer.data)")
            # pp.pprint(list(serializer.data))
            return self.get_paginated_response(serializer.data)

        print("Fell thru, hiiting super")
        return super().listing_view(request)

    # def get_paginated_response(self, data):
    #     self.get_paginated_response_call_counter += 1
    #     print("")
    #     print(
    #         f"  Running get_paginated_response - Counter =  {self.get_paginated_response_call_counter}"
    #     )
    #     if self.paginator:
    #         print(f"     self.paginator =  {self.paginator}")
    #         try:
    #             print("     trying to build a paginated response ")
    #             response = {
    #                 "count": self.paginator.count,
    #                 "next": self.get_next_link(),
    #                 "previous": self.get_previous_link(),
    #                 "results": data,
    #             }
    #             print(response)
    #             return Response(response)
    #         except Exception as e:
    #             print(f"                It broke {e}")
    #     else:
    #         print("                 Else - Not a real response")
    #     return Response(
    #         {
    #             "count": "w",
    #             "next": "t",
    #             "previous": "f",
    #             "results": data,
    #         }
    #     )

    # def paginate_queryset(self, queryset, request, view=None):
    #     """
    #     Paginate a queryset if required, either returning a
    #     page object, or `None` if pagination is not configured for this view.
    #     """
    #     self.request = request
    #     page_size = self.get_page_size(request)
    #     if not page_size:
    #         return None

    #     paginator = self.django_paginator_class(queryset, page_size)
    #     page_number = self.get_page_number(request, paginator)

    #     try:
    #         self.page = paginator.page(page_number)
    #     except InvalidPage as exc:
    #         msg = self.invalid_page_message.format(
    #             page_number=page_number, message=str(exc)
    #         )
    #         raise NotFound(msg)

    #     if paginator.num_pages > 1 and self.template is not None:
    #         # The browsable API should display pagination controls.
    #         self.display_page_controls = True

    #     return list(self.page)

    # def paginate_queryset(self, queryset):
    #     """
    #     Return a single page of results, or `None` if pagination is disabled.
    #     """
    #     self.paginate_queryset_call_counter += 1
    #     print("")
    #     print(
    #         f"  Running paginate_queryset - Counter =  {self.paginate_queryset_call_counter}"
    #     )
    #     if self.paginator is None:
    #         print("                 self.paginator Is None")
    #         return None
    #     # print(f"        Vars of self.paginator is {vars(self.paginator)}")
    #     return self.paginator.paginate_queryset(queryset, self.request, view=self)

    # @property
    # def paginator(self):
    #     """
    #     The paginator instance associated with the view, or `None`.
    #     """
    #     self.paginator_call_counter += 1
    #     print("")
    #     print(f"  Running Paginator - Counter =  {self.paginator_call_counter}")
    #     caller_function()
    #     if not hasattr(self, "_paginator"):
    #         print("     Not hasattr _paginator")
    #         if self.pagination_class is None:
    #             print("     **********************self.pagination_class is None")
    #             self._paginator = None
    #         else:
    #             print(f"     self.pagination_class is {self.pagination_class}")
    #             self._paginator = self.pagination_class()
    #         print(f"        Returning {self._paginator}")
    #     else:
    #         print("     Yes hasattr _paginator")
    #     return self._paginator


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
        "locale",
        "slug",
    ]
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(
        ["page", "qa", "gender", "age", "relationship", "slug"]
    )
    pagination_class = PageNumberPagination
    search_fields = ["name", "profile_fields"]
    filter_backends = (SearchFilter,)

    def _filter_queryset_by_profile_fields(
        self, ocs, gender_value, age_value, relationship_value
    ):
        pf_gender = ocs.profile_fields.blocks_by_name("gender")
        pf_age = ocs.profile_fields.blocks_by_name("age")
        pf_relationship = ocs.profile_fields.blocks_by_name("relationship")

        pf_gender = pf_gender[0] if len(pf_gender) > 0 else None
        pf_age = pf_age[0] if len(pf_age) > 0 else None
        pf_relationship = pf_relationship[0] if len(pf_relationship) > 0 else None

        if gender_value and age_value and relationship_value:
            if (
                pf_gender
                and pf_gender.value == gender_value
                and pf_age
                and pf_age.value == age_value
                and pf_relationship
                and pf_relationship.value == relationship_value
            ):
                return ocs.id
        elif gender_value and age_value:
            if (
                pf_gender
                and pf_gender.value == gender_value
                and pf_age
                and pf_age.value == age_value
            ):
                return ocs.id
        elif gender_value and relationship_value:
            if (
                pf_gender
                and pf_gender.value == gender_value
                and pf_relationship
                and pf_relationship.value == relationship_value
            ):
                return ocs.id
        elif age_value and relationship_value:
            if (
                pf_age
                and pf_age.value == age_value
                and pf_relationship
                and pf_relationship.value == relationship_value
            ):
                return ocs.id
        elif gender_value:
            if pf_gender and pf_gender.value == gender_value:
                return ocs.id
        elif age_value:
            if pf_age and pf_age.value == age_value:
                return ocs.id
        elif relationship_value:
            if pf_relationship and pf_relationship.value == relationship_value:
                return ocs.id

    def get_queryset(self):
        qa = self.request.query_params.get("qa")
        gender = self.request.query_params.get("gender", "")
        age = self.request.query_params.get("age", "")
        relationship = self.request.query_params.get("relationship", "")
        slug = self.request.query_params.get("slug", "")
        locale = self.request.query_params.get("locale", "")

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
                    ocs.locale = latest_revision.locale
                    ocs.slug = latest_revision.slug

        else:
            queryset = OrderedContentSet.objects.filter(
                live=True,
            ).order_by("last_published_at")

        if gender or age or relationship:
            # it looks like you can't use advanced queries to filter on StreamFields
            # so we have to do it like this.``
            filter_ids = [
                self._filter_queryset_by_profile_fields(x, gender, age, relationship)
                for x in queryset
            ]
            queryset = queryset.filter(id__in=filter_ids).order_by("last_published_at")
        if slug:
            queryset = queryset.filter(slug=slug)
        if locale:
            locale = Locale.objects.get(language_code=locale)
            queryset = queryset.filter(locale=locale)
        return queryset


class AssessmentViewSet(BaseAPIViewSet):
    base_serializer_class = AssessmentSerializer
    known_query_parameters = BaseAPIViewSet.known_query_parameters.union(
        [
            "tag",
            "qa",
            "page",
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
        locale_code = self.request.query_params.get("locale")

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

        if locale_code:
            queryset = queryset.filter(locale__language_code=locale_code)

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
# api_router.register_endpoint("whatsapptemplates", WhatsAppTemplateViewset)
api_router.register_endpoint("orderedcontent", OrderedContentSetViewSet)
api_router.register_endpoint("assessment", AssessmentViewSet)
