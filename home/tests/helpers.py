from wagtail.models.sites import Site  # type: ignore

from home.models import SiteSettings

PFOption = tuple[str, list[str]]
PFOptions = list[PFOption]


def set_profile_field_options(profile_field_options: PFOptions) -> None:
    site = Site.objects.get(is_default_site=True)
    site_settings = SiteSettings.for_site(site)
    site_settings.profile_field_options.extend(profile_field_options)
    site_settings.save()
