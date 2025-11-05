# Understanding the V2 API

The API is implemented on top of Wagtail's API, [documentation can be found here](https://docs.wagtail.org/en/latest/advanced_topics/api/v2/usage.html)

## Platforms

The four platforms currently supported by the content repo are **Web**, **Whatsapp**, **Viber** and **Messenger**. The API only returns results for one platform at a time depending on which platform is requested.

## Requesting content for different platforms

In order to retrieve content for a platform, the following endpoints are accepted

`/api/v2/pages/<page-id>/?whatsapp=True`

`/api/v2/pages/<page-id>/?viber=True`

`/api/v2/pages/<page-id>/?sms=True`

`/api/v2/pages/<page-id>/?ussd=True`

`/api/v2/pages/<page-id>/?messenger=True`

If no platform is provided in the query string, the API will return the web content.

_If a platform has been requested but has not been enabled on the CMS no content will be returned_

## Content Body Pagination

For Whatsapp, Viber, SMS, USSD and Messenger, each text block in the CMS counts as 1 message. If no message index is sent in the query string, the API will return the first message. Below are examples of how to request specific messages.

`/api/v2/pages/<page-id>/?whatsapp=True&message=1`

`/api/v2/pages/<page-id>/?viber=True&message=4`

`/api/v2/pages/<page-id>/?messenger=True&message=2`

`/api/v2/pages/<page-id>/?sms=True&message=3`

`/api/v2/pages/<page-id>/?ussd=True&message=5`

The content body that is returned will return the indexes of the previous and next messages as well, and None if no previous or next message.

## Content Pages Pagination

You can paginate content pages by adding a limit and an offset. The limit is the page size, and the offset is the amount to start from. For example:

`/api/v2/pages/?offset=2&limit=2` will give the second page with 2 results

`/api/v2/pages/?offset=4&limit=2` will give the third page with 2 results

## Content Pages Filtering

`/api/v2/pages/?tag=relationships` will give all the articles that have been tagged for relationships

More information about fetching content from the API can be seen [here](https://docs.wagtail.io/en/stable/advanced_topics/api/v2/usage.html)

## Content page fields
All content pages have the following fields:
|Name|Description|
|----|-----------|
|id|The database identifier for the content page|
|meta|The metadata for the page. See the Metadata fields section for more details|
|title|The title of the content to display to the user. This changes depending on the channel|
|subtitle|The subtitle to display to the user. This is only present for the web channel type|
|body|The body of the content to show to the user. This differs depending on the channel type|
|tags|The tags of the content page, as strings in an array. Used to organise and classify pages|
|triggers|The keywords that should trigger this content page, as strings in an array|
|quick_replies|(deprecated) The buttons that should be displayed with the content|
|related_pages|A list of pages that are related to this one|

### Metadata fields
These are the fields that fall under the `meta` field.
|Name|Description|
|----|-----------|
|type|The database model for this page, `home.ContentPage` for content pages|
|detail_url|The API URL for this page's details|
|html_url|The URL for the web version of this content|
|slug|This, together with the locale, form the unique identifier for this page|
|show_in_menus|String that's "true" or "false". Whether or not to show in menus|
|seo_title|Title to use for SEO|
|search_description|Description to use for SEO|
|first_published_at|Timestamp of when this page was first published|
|alias_of|Details of the page this is an alias of, otherwise null|
|parent|The details of this page's parent. Contains the ID, title, and in the "meta" key the type and html URL|
|locale|The language code for the locale of this page|

### WhatsApp body fields
If you've requested the WhatsApp content for the content page, the body field will contain the following fields:
|Name|Description|
|----|-----------|
|message|Which number this is. Only one message is shown per request, and the `message` query parameter controls which one|
|next_message|The message number for the next message, if there is one, else `null`|
|previous_message|The message number for the previous message, if there is one, else `null`|
|total_messages|The total number of WhatsApp messages present in this content page|
|text|This object contains the content of the WhatsApp message|
|text.value.image|The integer ID of the image linked to this message, else `null`|
|text.value.media|The integer ID of the media linked to this message, else `null`|
|text.value.footer|A string containing the message footer|
|text.value.buttons|A list of objects representing buttons.|
|text.value.buttons.type|The type of button. Can be `next_message`, `go_to_page`, or `go_to_form`|
|text.value.buttons.value|The value of the button. Contains `title`, the button's title. For go_to_page, there's a `page` field, whose value is an integer page ID. For go_to_form, there's a `form` field, whose value is an integer form ID.`
|text.value.message|The text of the whatsapp message|
|text.value.document|The integer ID of the document linked to this message, else `null`|
|text.value.list_items|(deprecated)A list of objects representing list items. Each object has a `value`, which is the text for the list item. See `list_items_v2` for the full list item values.|
|text.value.list_title|The title of the list, used for the button that opens the list|
|text.value.next_prompt|(deprecated)The text for the button that goes to the next message. Rather use `buttons` here|
|text.value.example_values|For template messages, a list of examples for the variables|
|text.value.variation_messages|A list of variations for this message. Each variation contains `profile_field` and `value`, which determines what the value of the contact's profile field should be for this variation to apply, and `message`, which is the text that should be used if the variation condition applies|
|text.value.list_items_v2|An array of objects representing the list items. Same format as `buttons`|
|revision|The integer ID for the revision of this content page|
|is_whatsapp_template|A boolean that represents whether this is a whatsapp template or not|
|whatsapp_template_name|If this is a whatsapp template, the name that was used to submit this to the Meta API|
|whatsapp_template_category|If this is a whatsapp template, the category that this was submitted under to the Meta API|


## Next Prompts

## Triggers

## Related Pages