from home.models import ContentPageTag


def get_bcm_page_ids():
    return ContentPageTag.objects.filter(tag__name__icontains="bcm_").values_list(
        "content_object_id", flat=True
    )
