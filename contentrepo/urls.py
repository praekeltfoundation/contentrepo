from django.conf import settings
from django.contrib import admin
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from home import views as home_views
from home.api import api_router
from menu import views as menu_views
from search import views as search_views

from drf_spectacular.views import (  # isort:skip
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"cms-forms", home_views.AssessmentListViewSet, basename="cms-form")

custom_v2router = routers.DefaultRouter()
custom_v2router.register("ratings", home_views.ContentPageRatingViewSet)
custom_v2router.register("pageviews", home_views.PageViewViewSet)

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", RedirectView.as_view(url=reverse_lazy("wagtailadmin_home"))),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("mainmenu/", menu_views.mainmenu, name="mainmenu"),
    path("submenu/", menu_views.submenu, name="submenu"),
    path("randommenu/", menu_views.randommenu, name="randommenu"),
    path("faqmenu/", menu_views.faqmenu, name="faqmenu"),
    path("suggestedcontent/", menu_views.suggestedcontent, name="suggestedcontent"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/whatsapptemplates/", menu_views.randommenu, name="whatsapptemplate"),
    path("api/v2/", include(router.urls)),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's page serving mechanism. This should be the last pattern in
    # the list:
    path("api/v2/", api_router.urls),
    path("api/v2/token/", obtain_auth_token),
    path("api/v2/custom/", include(custom_v2router.urls)),
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]
