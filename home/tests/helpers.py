from collections.abc import Iterable

from wagtail.models.sites import Site  # type: ignore

from home.constants import AGE_CHOICES, GENDER_CHOICES, RELATIONSHIP_STATUS_CHOICES
from home.models import SiteSettings

PFOption = tuple[str, list[str]]
PFOptions = Iterable[PFOption]


DEFAULT_PF_OPTIONS = (
    ("gender", [c[0] for c in GENDER_CHOICES]),
    ("age", [c[0] for c in AGE_CHOICES]),
    ("relationship", [c[0] for c in RELATIONSHIP_STATUS_CHOICES]),
)


def set_profile_field_options(pf_options: PFOptions = DEFAULT_PF_OPTIONS) -> None:
    site = Site.objects.get(is_default_site=True)
    site_settings = SiteSettings.for_site(site)
    site_settings.profile_field_options.extend(pf_options)
    site_settings.save()
