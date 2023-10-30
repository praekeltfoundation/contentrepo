# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## Unreleased

### Added

### Changed
-->

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
