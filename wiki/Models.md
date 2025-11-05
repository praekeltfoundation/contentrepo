# Contentrepo Models

Contentrepo makes use of some custom models.

## Content Pages

The `ContentPage` is a page model in the homepage app. The content page is made up of six tabs. These tabs are defined in a `TabbedInterface` object and are listed as `ObjectLists`. The tabs are `web`, `whatsapp`, `messenger`, `sms`, `ussd`, `viber`, `promote`, and `settings`. The `web`, `whatsapp`, `sms`, `ussd`, `messenger` and `viber` tabs all have titles and bodies. The bodies contain both text and images. Whatsapp bodies also contain documents, media and `next_prompt`. The `web` tab also has a subtitle field and the `whatsapp` tab has the option to be a whatsapp template.

The `ContentPage` has `body` (web body), `whatsapp_body`, `sms_body`, `ussd_body`,`viber_body` and `messenger_body` attributes that the content can be accessed on. These attributes are all `StreamValue` objects.

The promote tab has the promote panels that are present in the base `Page` object in wagtail but is extended by adding `tags`, `triggers`, `quick_replies`, `rating` and `related_pages`, all of which are discussed in the next section [Quick Replies, Triggers and Tags](#quick-replies-triggers-and-tags).

The settings tab also extends the existing `Page` settings in wagtail. The extension covers boolean fields that allow the admins to enable and disable the different platforms.

## Ordered Content Sets

Ordered Content Sets can have revisions and drafts. You can save changes as a draft allowing it to be reviewed before being published live.

## Quick Replies, Triggers and Tags

All four of these fields are created using Django's taggit module.

### Quick replies

The quick reply field is where the quick reply options are stored. The whatsapp buttons will be based on this list of Django taggit tags. For each quick reply, there will need to be an identical trigger. The class associated with quick replies is `QuickReplyContent`. These tag objects cannot be ordered.

### Triggers

Triggers will be used to link content. If a quick reply is sent by a user, the message with the corresponding trigger will be sent. This is done by providing the API with a trigger parameter. The triggered content is then returned. The associated class is `TriggeredContent`

### Tags

This uses the class `ContentPageTag` to tag content pages. This allows the admins to tag content such that all content with that tag will be returned by calling the API with the `tag` parameter.

## Related Pages

Related pages is a list of pages that can be set by the admin. Related pages make use of a page chooser block. The related pages are returned by the API as a list of pages with the `id` as a `value`, an `id` which is the `translation_key` and the `title` of the related page.

In the python,

```python
<StreamValue [<block related_page: <Page: Dogs 🐶>>, <block related_page: <Page: Cats 🐱>>]>
```

In the API,

```json
    "related_pages": [
        {
            "id": "e186899c-81c1-47cb-ade4-40db4e1eadae",
            "value": 17,
            "title": "Dogs 🐶"
        },
        {
            "id": "de7e6047-d8c3-46f3-889a-889490fcb9b6",
            "value": 18,
            "title": "Cats 🐱"
        }
    ],
```

## Page Ratings

## Images, Media, Documents

## Next prompts

Next prompts is a text field that will trigger the next message in a string of messages that will be sent to the end user. "Read more" is a good example of this. This allows us to not spam the user with messages.