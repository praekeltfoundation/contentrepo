from django.apps import AppConfig


class HomeAppConfig(AppConfig):
    name = "home"

    def ready(self):
        from wagtail.models.reference_index import ReferenceIndex

        from home.models import OrderedContentSet

        ReferenceIndex.register_model(OrderedContentSet)
