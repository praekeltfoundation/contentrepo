from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.conf.urls.i18n import i18n_patterns

from rest_framework import routers

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from wagtail_content_import import urls as wagtail_content_import_urls

from search import views as search_views
from menu import views as menu_views
from home import views as home_views
from home.api import api_router

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

custom_v2router = routers.DefaultRouter()
custom_v2router.register("ratings", home_views.ContentPageRatingViewSet)
custom_v2router.register("pageviews", home_views.PageViewViewSet)

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include(wagtail_content_import_urls)),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("search/", search_views.search, name="search"),
    path("mainmenu/", menu_views.mainmenu, name="mainmenu"),
    path("submenu/", menu_views.submenu, name="submenu"),
    path("import/", home_views.upload_file, name="import"),
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
    path("api/v2/custom/", include(custom_v2router.urls)),
    path("", include(wagtail_urls)),
    # Alternatively, if you want Wagtail pages to be served from a subpath
    # of your site, rather than the site root:
    #    path("pages/", include(wagtail_urls)),
]

urlpatterns += i18n_patterns(
    path("search/", search_views.search, name="search"),
    path("", include(wagtail_urls)),
)
