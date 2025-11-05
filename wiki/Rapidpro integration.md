# Contentrepo Flow in RapidPro for Content Browsing

> **Note:** this  

The WhatsApp content is retreieved from Contentrepo by calling the API with a RapidPro webhook call and then processing the data. This flow is started by the user sending the keyword "find". Other keywords, like "ask", "share", "info" and "legal" all start other flows in RapidPro.

In this case there are two types of pages, content page and other. The content page is defined in this case as a page with **no** children. The other pages are the menus for which a selection is necessary.

Initially the language is set, and the appropriate Find Menu is found.
> **Note:** contentrepo uses 2 letter language codes (en and sw) but RapidPro uses 3 letter codes (eng and swh). This is handled in the flowstart to ensure that the user sees content in the correct language before any content is shown.

Information on the Find Menu is retrieved by making use of the query string parameters, slug for the page slug (in this case `find-menu`) and the locale (which RapidPro defaults to `en`).
```
http://<domain>/api/v2/pages/?slug=find-menu&locale=en
```

> **Note:** The base URL for the contentrepo API is stored in a global variable in RapidPro that can be accessed with `globals.content_repo_url` and can be found in the RapidPro Worspace Settings page.


A call to this endpoint returns useful information such as the page `id`, as can be seen below. 

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": <page_id>,
            "meta": {
                "type": "home.ContentPage",
                "detail_url": "http://localhost/api/v2/pages/<page_id>/",
                "html_url": "http://localhost/en/find-menu/",
                "slug": "find-menu",
                "first_published_at": "2022-01-28T13:44:31.958041Z",
                "locale": "en"
            },
            "title": "Find menu"
        }
    ]
}
```

The page `id` is then stored in RapidPro as `page_id` and used to make a request to the API for the find menu content. 
This webhook will then be used as part of a series of loops to retrieve content if the page_id is known.

```
http://<domain>/api/v2/pages/<page_id>/?whatsapp=True
```

For each endpoint called, the flow will make 3 decisions for each page retrieved:
* Is the page a content page or an "other" page?
* Does the page contain an image or text?
* Is there another message (pagination)?

## Variables saved for each page
For each endpoint called, the flow saves the `current_message`, `next_message` and `parent_id`. These `current_message` and `next_message` variables are used for pagination and will come into play later. The `parent_id` keeps track of the page tree, and the `page_id` of the previous page, this is used when a user selects `BACK`.

## Decision 1: The page is a content page
As the content page is defined in this case as a page with **no** children, pages with a `false` value for `has_children` will be categorised as "Content Page". These pages will be the leaves of the tree.

```json
{
    "has_children": false,
    ...
}
```

## Decision 1: The page is an "other" page 
A page with children is classified as "Other". These pages are menus and require selections.

```json
{
    "has_children": true,
    ...
}
```

## Decision 2: The page contains an image 
A message with an image is split into two messages by contentrepo, first an image, where the message text is the image description, and the next message is the text body, this is accessed by making use of pagnitation. This is illustrated in the snippet of the response below,

```json
    "body": {
        "text": {
            "type": "Whatsapp_Message",
            "value": {
                "image": 151,
                "document": null,
                "media": null,
                "message": "."
            },
            "id": "eac658ec-3d4e-47bc-8a8d-bc200a21c590"
        },
        ...
    },
```

If `image` has a value, the image will be aquired with the endpoint pattern, 

```
http://<domain>/api/v2/images/<image_id>
```

Which will return a response with the `download_url` of the relavent image in the metadata, which is sent to the user with the use of the send message block, under the attachments,

```
http://<domain>/media/original_images/<filename>
```

## Decision 3: The page does not contain an image 
The webhook used to get the content for the whatsapp message is slightly different for a Content Page and an Other page. 

For a content page, there are no children, so the message body is retrieved with 

```
http://<domain>/api/v2/pages/<page_id>/?whatsapp=True
```

For an "other" page, or a menu, the children need to be considered. After the text for the menu is retrieved and sent to the user, the selection options must be retrieved. A webhook call is made to the following endpoint, 

```
http://<domain>/api/v2/pages/?child_of=<page_id>&order=title
```

this returns an object with the number of child pages, and a list of details of the child pages. The pages are ordered by the title. It is important that the titles contain the number, such that the number in the title correlates to the corresponding number in the menu text. 

```json
    "body": {

        "text": {
            "type": "Whatsapp_Message",
            "value": {
                "image": null,
                "document": null,
                "media": null,
                "message": "This is the text that is used in the WhatsApp message."
            },
            ...
        }
    },
```

## Decision 4: There is a next tag in the response 
Contentrepo makes use of pagination. Thus a webhook call is made to retrieve the pages until the `next_message` tag is `null`. The webhook call makes use of the `message`. For example, if the message returns 

```json
    "body": {
        "message": 2,
        "next_message": 3,
        "previous_message": 1,
        "total_messages": 4,
        ... 
        }
```

Then to view the next message we can use the webhook call 

```
http://<domain>/api/v2/pages/<page_id>/?whatsapp=true&message=2
```

The valid `message` query parameters are `1` to `4`.

## Decision 4: There is no next tag in the response 
When the tag `next_message` returns `null`, we have reached the last message on the topic. This is `message=4` in the previous example. 

```json
    "body": {
        "message": 4,
        "next_message": null,
        "previous_message": 3,
        "total_messages": 4,
        ... 
        }
```

Once all the messages have been retrieved, RapidPro waits for a response from the user. If the page is a content page, the valid responses are generally `next` for the next content page and `back` for the previous content page. If the page is a menu or "other" page, the valid options range from `1` to the number of menu items. 

## User chooses the back option 
When the user chooses the back option, the `page_id` is set to the `parent_id` and the webhook is called for the previous page.
