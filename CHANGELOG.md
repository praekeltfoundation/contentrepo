# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## Unreleased
### Added
- Filter ordered content sets by profile field values.
- Add list_button_title to Whatsapp messages.

### Removed
- Removed word embeddings search (`s` query parameter in API)

### Fixed
- API: Fix detail URL in Pages API
- Forms: Added model import validation so that required fields are flagged on import
- API: Return all pages if tag keyword is specified without tags
- API: Added page keyword to Assessments API
- Ordered Content Sets: Import now allows for CSV values in time, unit, before or after, and contact field
- Importing certain ContentPage fields with whitespace-only values will no longer throw unhandled exceptions

### Security
- Updated sentry-sdk from 1.44.1 to 2.8.0
- Updated wagtail from 5.2.4 to 5.2.6
- Updated certifi from 2024.2.2 to 2024.7.4
- Updated django from 4.2.11 to 4.2.15
- Updated sqlparse from 0.4.4 to 0.5.0
- Updated djangorestframework from 3.15.1 to 3.15.2
- Updated urllib3 from 2.2.1 to 2.2.2
- Updated requests from 2.31.0 to 2.32.2
- Updated idna from 3.6 to 3.7
-->

## v1.2.1
### Added
- Forms: Add skip threshold and skip high result page
- Forms: Add semantic_id for questions

## v1.2.0
### Fixed
- Page not found api status change to 404 from 400
- Use cache for data when importing assessments with xlsx
- Better error handling for missing when importing content

### Added
- content page import validation using the model
- Add Age question type for forms
- Add Multiselect question type for forms
- Add Semantic ID for form answers
- Add version number to distinguish question sets
- Add Freetext question type for forms
- Add Integer question with min and max values
- Add Year of Birth type question type

### Changed
- Increased SMS limit to 459 characters
- Validate character limit fir footer and list items when importing
- Add Document upload extension validation
- Update tests to use model validations and update test data
- updated ordered content set status to include In Moderation and Live + In Moderation
- Remove pagination on page view report
- Add tests for the pageview report filters
- Make inflection points and results pages optional
- Make min and max fields mandatory for integer question type
- Custom model validation for IntegerQuestionBlock min and max
- Custom model validation for min and max values to only be positive

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
