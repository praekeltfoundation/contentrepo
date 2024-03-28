# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## Unreleased
### Fixed
- Ordered content set import link (PR 299, ticket omega 117)
- Import for WhatsApp list items with comma in (PR 257, ticket omega 48)
- Exporting to XLSX when pages have media (PR 251 & 266, ticket omega 63)
- Import breaking when row in import file referenced a content page in a different locale (PR 261, ticket omega 61)
- Go to page buttons where target page has been deleted breaks export (PR 264, ticket 51)
- Validate max character for WhatsApp list items during import (PR 256 & 304, ticket omega 11)
- Page not found api status change to 404 from 400. (PR 306, ticket omega 136) (QA incomplete)

### Added
- Additional fields to Ordered Content Set export (PR 259 & 268, ticket omega 33)
- Moderation to ordered content sets (PR 294, ticket omega 100) (QA incomplete)
- Draft status for Ordered Content Sets (PR 250 & 276 & 279 & 280, ticket omega 10)
- Diagrams for documentation (PR 258, ticket omega 15)
- Tests for serialisers (PR 273, ticket omega 74)
- Environment variable config for sentry environment (PR 291, ticket omega 103)
- WhatsApp template language support (PR 215, ticket omega 36)
- Script to list all of the links that are broken due to pages being deleted (PR 298, ticket omega 113)

### Changed
- Test improvements for ContentPage API (PR 263 & 265 & 269 & 270 & 283, ticket omega 75)
- Stop pages being deleted if they're linked to in other pages (PR 296 & 297, ticket omega 113)
- More informative error message when import file contains messages for a page that doesn't exist (PR 295, ticket omega 93)
- Increased SMS limit to 459 characters (PR 301, ticket omega 142) (QA incomplete)
- Validate character limit fir footer and list items when importing
- Updated pull request template (PR 300, ticket omega 123)
- Upgraded Django from 4.2.9 to 4.2.10, security patch (PR 248)
- Removed partail_match parameter from field search, deprecated (PR 262, ticket omega 91)
- Disallow imports being able to change content page parent/child structure, was causing errors in import (PR 278, ticket omega 32)
- Ensure that Content Pages can only be created as children of Content Index Pages (PR 281, ticket omega 30)
- Change from wagtail modeladmin to external modeladmin package, wagtail modeladmin deprecated (PR 292, ticket omega 105)
- Limit the extensions that are allowed to be uploaded for documents (PR 303, ticket omega 139) (QA incomplete)
- Seperate templates from contentpage (PR 277, ticket omega 27) (QA incomplete)
-->

## v1.2.0
### Fixed

### Added

### Changed

## v1.1.0
### Fixed
- Autofill for empty slug
- Fixed Web content preview in CMS
- Fixed related pages export
- Fixed API tests
- Fixed Redis caching issues

### Added
- Added support for SMS content
- Added support for USSD content
- Added support for a Footer in WhatsApp content
- Added support for List Messages in WhatsApp content
- Added error handling on WhatsApp template submission errors, and adds issue to sentry
- Added validation of variables used in WhatsApp template submission
- Added WhatsApp title check
- Added typing information for migration test
- Added CI checks for pending migrations


### Changed
- Moved slug uniqueness validation to the model validation/clean
- Empty slugs will auto-generate a unique slug, but if a duplicate slug is specified the user will get a validation error instead of their chosen slug getting overwritten with a unique one.
- Slug uniqueness is per-locale
- Test speedups, and there's a separate contentrepo/settings/test.py for test-specific settings.
- WhatsApp example values no longer show on the default API view, and forms part of the fields returned when the parameter `whatsapp=true` is added to the api call
- Improved testing of Importer
- Made text fields non-nullable
- Converted API tests to pytest and added docstrings
- Updated release process in Readme.

### Deprecated
 - Removed the old importer
 - Removed the `Authorization` and `Authentication` WhatsApp template category


## v1.1.0-dev.5
### Fixed
- Don't submit whatsapp template with no message
- Remove additional delete on purge import, to fix import rollback on error

### Added
- Added support for example values.  These values will be used when creating whatsapp templates that contain variables (also known as placeholders)
- Added support for Whatsapp Template Category selector
- Configurable whatsapp template category

### Changed
- `REDIS_LOCATION` as been changed to `CACHE_URL`, and now supports a wide range of cache backends. `REDIS_LOCATION` will still work, and is an alias for, and takes priority over `CACHE_URL`.
- Remove cache on list endpoint. There's no way to invalidate this cache, and at this point in time we're not sure if it's necessary, but it was creating issues in that the list endpoint would be out of date, so it has been removed for now. If it's needed in the future, it will be added back, but in a way that allows us to invalidate it on changes, or with a very short TTL.
- Refactoring of import & export code



## v1.1.0-dev.4

### Fixed
- ContentPage imports that fail now rollback changes

### Added
- Buttons StreamBlock for WhatsApp messages
- API endpoint for media content
- Support for creating WhatsApp templates with images
- Run tests with PostgreSQL 12, 13 and 14

### Changed
- Migrated next_prompt on WhatsApp messages to buttons
- Refactored ContentPage import. Translation keys are now added as translation keys instead of as tags
- Improved testing for import and export


### Deprecated
- next_prompt on WhatsApp messages is deprecated, use buttons instead. Will be removed on the next major release

## v1.1.0-dev.3

### Fixed

- Content_page_index.html template does not exist
- N+1 Query error


## v1.1.0-dev.2

### Added

- Support for IAM role-based auth when running in EKS (#163)
- Update workflow actions and push to ghcr.io as well as Docker Hub (#164)
- Flag for loading embedding model to reduce memory usage if not necessary (#166)
- Management command to run existing content through embedding model (#167)

### Fixed

- File decoding error in Ordered Content Set import (#161)
- Reduced Docker image size (#165)

## v1.1.0-dev.1

### Added

- Make API return draft and versions if the QA query param is set (#149)

## v1.1.0-dev.0

### Added

- NLP model hosting added and used for ContentPage filtering via API (#133)

## v1.0.0-dev.2

### Fixed

- Allow email settings to be configured through environment variables (#155)


## v1.0.0-dev.1

### Added

- Documented list of features (#151)

### Fixed

- Duplicate migration number (#150)


## v1.0.0-dev.0

This is the first major release, as well as the first LTS release.

### Changed

- Made authentication for the API mandatory (#136)


## v0.0.109

### Added

- Success and failure messages for imports (#141)
- Support for stage based messaging in ordered content sets (#143)
- Return draft content on the API with query parameter (#144)

### Changed

- Truncate message bodies in admin list view (#139)
- Progress indicators for imports change according to import progress (#142)

### Fixed

- Handle site settings not yet created properly (#140)


## v0.0.108

This release adds an index concurrently, which is a postgresql-only feature. This means that from this release forward, only the postgresql database backend is supported.

### Added

- Documented the release plan (#135)
- Redirect to wagtail admin from homepage (#137)

### Changed

- Indexed the timestamp field for page views (#134)

### Fixed

- Return appropriate error for page not found, instead of uncaught server error (#138)
