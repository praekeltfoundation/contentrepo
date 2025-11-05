# Understanding the V3 API

The API is implemented on top of Wagtail's API, [documentation can be found here](https://docs.wagtail.org/en/latest/advanced_topics/api/v2/usage.html)

The V3 API was developed to clean up and simplify the API, add support the new Standalone Whatsapp Templates functionality, while keeping the [V2 API](Understanding-the-V2-API.md) functioning as normal in parallel. The V2 API is still available at the moment, but it will be deprecated at some point in the future.

For now, the V3 API supports the `/pages/`, `/indexes/`, and `/whatsapptemplates/` endpoints.

## Core Changes
- Remove uneccessary fields and complicated structures
- Use Slugs instead of IDs
- Rename fields or parameters or data structures to better reflect their purpose


### QA / Return Drafts

In the V2 API there is an undocumented `?qa=<true-or-false>`parameter on some of the endpoints, that was used by our internal team to check unpublished content on live sites, to make sure it displays correctly before publishing that content item.  Essentially, if `qa` was set to `True`, we would return the latest revision of that content item, regardless of whether it was published or still in draft.

This parameter as now been renamed to `?return-drafts=<true-or-false>`, as this better reflects its function.

### Platforms are now Channels
The five channels currently supported by the content repo are **Web**, **Whatsapp**, **Viber**,  **Messenger** and **SMS**. The API only returns results for one channel at a time depending on which channel is requested.

The channels can be conceptually grouped as follows:
|Name|Description|
|----|-----------|
|web|The default channel.  Uses the `Page` object for things like `title`, `subtitle` etc|
|whatsapp|The most used channel at this point.  The CMS support for this channel is more advanced, with support for things like Standalone Whatsapp Templates, Buttons, Example Values, Images, Media, etc|
|generics|These are channels that we have basic support for in the CMS, with no additional advanced functionality at this stage.  These include `viber`,`messenger`, `ussd` and `sms`

### Channel Filtering

In the V2 API, channel filtering is handled by multiple channel-named parameters with a Boolean argument, for example `?whatsapp=True`, `?viber=True` etc.  
In V3 it is now done via a single `channel` parameter, which takes a single `channel-name` argument, for example `?channel=whatsapp`, `?channel=viber`

In order to retrieve content for a specific channel, you can use the `channel` query parameter at any of the V3 page endpoints, for example:

- `/api/v3/pages/?channel=<channel-name>`
- `/api/v3/pages/<page-id>/?channel=<channel-name>`
- `/api/v3/pages/<page-slug>/?channel=<channel-name>`

# Standalone Whatsapp Templates

We have added functionality for standalone templates. This allowed us to build much more sophisticated support for templates into the CMS (e.g. variables and approval status indicators). It also simplifies the design of the ContentPages, therefore making the application more extensible and easier to maintain.

## WhatsApp Templates API

### Endpoints

1. `GET /api/v3/whatsapptemplates/` - List all WhatsApp templates
2. `GET /api/v3/whatsapptemplates/<id>/` - Get template by ID
3. `GET /api/v3/whatsapptemplates/<slug>/` - Get template by slug

### Query Parameters

| Name | Description |
|------|-------------|
| `return_drafts` | If "true", returns draft versions of templates. Default is false. |
| `slug` | Filter templates by slug (partial match) |
| `locale` | Filter templates by locale/language code. Defaults to site's default locale. |
| `page` | Page number for pagination |
| `search`(deprecated)| This parameter was supported by earlier versions of the API, but has been deprecated going forward, in favour of searching via specific fields like `slug` or `title`

### Response Fields

| Field Name | Description |
|------------|-------------|
| `slug` | Unique identifier for the template |
| `detail_url` | Full URL to access this template |
| `locale` | Language code of the template (e.g., "en") |
| `category` | WhatsApp template category |
| `image` | Associated image ID (if any) |
| `message` | The template message content |
| `example_values` | List of example values for template variables |
| `buttons` | List of interactive buttons configured for the template |
| `revision` | Latest revision ID of the template |
| `status` | Current status of the template |
| `submission_name` | Name used for WhatsApp submission |
| `submission_status` | Status of WhatsApp submission |
| `submission_result` | Result of WhatsApp submission |

## Content Pages API (V3)

### Endpoints

1. `GET /api/v3/pages/` - List all content pages
2. `GET /api/v3/pages/<id>/` - Get page by ID
3. `GET /api/v3/pages/<slug>/` - Get page by slug
4. `GET /api/v3/indexes/` - List all content page indexes

### Query Parameters

| Name | Description |
|------|-------------|
| `return_drafts` | If "true", returns draft versions of pages |
| `channel` | Filter by channel ("web", "whatsapp", "sms", "ussd", "messenger", "viber"). Required. |
| `locale` | Filter by locale/language code. Defaults to site's default locale. |
| `slug` | Filter pages by slug (partial match) |
| `title` | Filter pages by title (partial match) |
| `trigger` | Filter pages by trigger name |
| `tag` | Filter pages by tag name |
| `child_of` | Filter pages to children of specified parent page slug |
| `page` | Page number for pagination |

### Response Fields

| Field Name | Description |
|------------|-------------|
| `slug` | Unique identifier for the page |
| `detail_url` | Full URL to access this page |
| `locale` | Language code of the page |
| `title` | Page title (channel-specific if specified) |
| `subtitle` | Page subtitle |
| `messages` | Content messages formatted for the specified channel |
| `tags` | List of associated tags |
| `triggers` | List of associated triggers |
| `has_children` | Boolean indicating if the page has child pages |
| `related_pages` | List of related pages with their slugs and titles |

### WhatsApp Message Fields

For WhatsApp channel responses, message objects include:

| Field Name | Description |
|------------|-------------|
| `message` | The text content of the WhatsApp message |
| `image` | Image ID if attached, else `null` |
| `document` | Document ID if attached, else `null` |
| `media` | Media ID if attached, else `null` |
| `footer` | Footer text (max 60 chars) |
| `buttons` | List of button objects (max 3). Each has `type` (`next_message`, `go_to_page`, `go_to_form`) and `value` with `title` and destination fields |
| `list_title` | Title for list button (max 24 chars) |
| `list_items` | List of items (max 10), same format as buttons |
| `variation_messages` | Message variations based on profile fields (`gender`, `age`, `relationship`) |
| `example_values` | Example values for template variables |



