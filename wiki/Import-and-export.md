# Importing and Exporting Content Pages
This features allows you to import content from an Excel (.xlsx) or comma-separated value (.csv) file. This is useful for bulk uploads of content pages.

## Importing
To import a file, click the "Import" button on the Content Pages list view. You are then presented with the following options:
| Option | Description |
| ------ | ----------- |
| File | The file on your computer that you want to upload |
| File type | The type of file that you're uploading. This can either be an Excel (.xlsx) or comma-separated value (.csv) file |
| Purge | Whether to delete all existing content before uploading this content. If you delete a row in your upload file, it will not get deleted when you perform the import, so you need to select "Yes" to this option if your import includes all of your content and you want removed rows to be removed from the CMS. Note that this will delete all locales, not just the locale selected for the Locale option |
| Locale | Which locales in the import file to import. Defaults to importing all locales from the import file. If the import file contains many locales, and you select a locale here, all rows for other locales will be ignored during the import |

After clicking "Upload", you will be presented with a progress bar that shows the progress of the import. After the import is complete, if it is successful, you will get a success message. If it is not, you will get an error message, and the content will be reverted to how it was before the import was started. Hopefully the error message is descriptive enough to help you fix the import file. If not, then you will have to contact the engineering team to figure out what is going wrong, so that they can help you fix the import file and add a better error message if this happens again.

The importer iterates over each row of the sheet. If the row has a `web_title`, but does not have a `parent`, `web_body`, `whatsapp_body`, `messenger_body`, `viber_body`, `sms_body` or `ussd_body`, it will be assumed to be an Index page, and it will be added under the Home Page for the specified locale.

If there is a `web_title`, then the row is assumed to be a Content page.

If there is no `web_title`, but there is a `variation_body`, then it is assumed to be a variation message for the last whatsapp message for the content page specified by the row's slug and locale.

If there is no `web_title` and no `variation_body`, but there are either `whatsapp_body`, `messenger_body`, `viber_body`, `sms_body` or `ussd_body` then it is added as a message to the content page specified by the row's `slug` and `locale`.

All values are stripped of leading and trailing whitespace before being imported.

Images, documents, and media are not currently imported.

The `page_id` row is ignored on import. The `slug` and `locale` are used to find the existing content page when importing. This is done to ensure that content can be reliably imported across different instances of ContentRepo, that may have different page IDs for the same piece of content. As such, it is enforced that slugs are unique per locale.

## Exporting
To export the content pages inside the CMS to a file, click the "Download XLSX" button on the Content Page list view. If you want it in CSV format, click the arrow next to that button to open the drop-down, and then the "Download CSV" button.

The export creates a CSV or XLSX file in the same format the import expects.

The XLSX has additional styling, layout, and frozen panels added to it, but otherwise is identical to the CSV format.

The export works by going through all the locales and getting the home page for each locale. For each home page, it will export all index pages and all content pages rows. For content pages with multiple messages, or messages with variations, each additional message or variation is added as an extra row to the export.

## Fields
The exporter will export content with the following fields, and the importer expects these fields to be present:

|Field name|Field description|
|----------|-----------------|
|structure|This shows where in the nested structure this content is found. The importer doesn't use this information, it infers it through the `parent` field, but it is helpful to identify where this content fits in the nested structure when viewing the document|
|message|This is a number representing which message in the content page this row is for. It is used when a content page has multiple messages, which get spread across multiple rows. This is not used by the importer, which infers the message order by the order of the rows. |
|page_id|The ID of this content page in the database. This isn't used in the import, the `slug` and `locale` fields are used instead as a unique identifier for a page|
|slug|The slug of the page. This along with locale is used to uniquely identify the page. During an import, if a page with the same slug and locale is found, it is overwritten instead of a new page being added|
|parent|The web title of the parent of this page. Note that this is not the slug of the parent page. If there are multiple pages in the same locale with the same title, then an error is raised. |
|web_title|The title of the web portion of this page. This is also used as the title of the page when specifying the page's parent. If this is present, then this row is assumed to be a content page instead of an index page.|
|web_subtitle|The subtitle of the web portion of this page|
|web_body|The body of the web portion of this page|
|whatsapp_title|The title of the whatsapp portion of this page|
|whatsapp_body|The body of the whatsapp portion of this page. If there are multiple whatsapp messages for a page, they are placed in separate rows. If this field is present, then this row is assumed to be a whatsapp message.|
|whatsapp_template_name|If this page is a whatsapp template, the name of that template. The name is generated when submitting the template to Meta. The import does not submit any templates to Meta, it assumes that has already been done and you are just loading the already submitted content into the CMS. If this field is present, it is assumed that this is a template message. |
|whatsapp_template_category|The category of WhatsApp template|
|example_values|If this is a whatsapp template with variables, example values for those variables. Comma separated list. The number of examples needs to match the number of template variables.|
|variation_title|If this message has any whatsapp variations, then this is the identifier for which user profiles this variation is appropriate for. It has the format of the type and value separated by a colon, with multiple of these separated by commas. eg `gender: male, relationship: single`.|
|variation_body|The body of this whatsapp variation message. If there are multiple variation messages, they are added as multiple rows.  If this is present, it is assumed that this row is a whatsapp variation message.|
|list_title|The text on the button of the whatsapp message, that when pressed opens up the list of possible items|
|list_items|The list items for a whatsapp list message. These are in the same format as `buttons`|
|sms_title|The SMS title|
|sms_body|The SMS body. If there are multiple messages, they are put as additional rows. If this field is present, it is assumed that this row is an SMS message|
|ussd_title|The USSD title|
|ussd_body|The USSD body. If there are multiple messages, they are put as additional rows. If this field is present, it is assumed that this row is a USSD message|
|messenger_title|The facebook messenger title|
|messenger_body|The facebook messenger body. If there are multiple messages, they are put as additional rows. If this field is present, it is assumed that this row is a messenger message|
|viber_title|The viber title|
|viber_body|The viber body. If there are multiple messages, they are put as additional rows. If this field is present, it is assumed that this row is a viber message|
|translation_tag|The translation key. This is used to link translations together. Two pages with the same translation key are considered translations of each other|
|tags|A comma separated list of tags|
|quick_replies|A comma separated list of quick replies. Quick replies are used as button text for templates.|
|triggers|A comma separated list of triggers|
|locale|The language that this content is in. This is in display format (e.g. `English`), not code format (e.g. `eng`)|
|next_prompt|The button text to see the next whatsapp message in this content page. This is deprecated in favour of `next_message` buttons|
|buttons|A [JSON](https://www.rfc-editor.org/rfc/rfc8259) serialisation of the whatsapp buttons for this message. It is an array of objects, each object having the keys "type" (can be "next_message", "go_to_page", or "go_to_form"), "title" (button text), and for "go_to_page" or "go_to_form" types, a "slug" key specifying the destination page or form. Example: `[{"type": "next_message", "title": "Next"}, {"type": "go_to_page", "title": "See more", "slug": "more-info"}, {"type": "go_to_form", "title": "Take Assessment", "slug": "risk-assessment"}]`|
|image_link| The link for the first image across the content types. Not imported|
|doc_link| The link for the whatsapp document. Not imported|
|media_link| The link for the whatsapp media. Not imported|
|related_pages|A comma separated list of slugs for pages that are related to this one|
|footer|The text to place in the footer of the whatsapp message.|
|language_code|The code of the language that this content is in. This is in display format (e.g. `en`)

# Importing and Exporting Ordered Content Sets
This features allows you to bulk import and export ordered content sets in Excel (.xlsx) and comma-separated value (.csv) file format.

## Importing
On the ordered content set list page, click the import button. You will then be presented with the following fields:
|Name|Description|
|----|-----------|
|File|The file that you want to upload, that contains the details of the ordered content set|
|File type|The type of the file that you want to upload, either CSV or Excel|
|Purge|Whether to delete all existing ordered content sets before creating the ones specified in the file. This option is for if your upload file contains all the ordered content sets in the CMS, and is useful if you want to ensure that deleted rows in the file result in those ordered content sets being deleted from the CMS|

After starting the upload, you will be presented with a progress bar. When the import is done, you will either be presented with a success message, or an error message. Hopefully the error message is useful enough for you to fix the import file and try again. If not, please contact engineering to investigate the error, and ensure that there's a useful error message if this issue happens again.

If an import has an error or breaks, the data in the CMS will contain how far the import completed successfully, it will not be rolled back in the case of an error like content pages.

## Exporting
In the ordered content set list view, you can click the "Download XLSX" button to perform an export in Excel format. For CSV format, click the arrow to the right of that button, and when the drop-down opens select the "Download CSV" button.

The export creates files in the same format that the importer expects.

## Fields
These are the fields that the importer expects and the exporter exports

|Name|Description|
|----|-----------|
|Slug|The slug of the ordered content set. This along with locale is used to uniquely identify the ordered content set. During an import, if an ordered content set with the same slug and locale is found, it is overwritten instead of a new ordered content set being added|
|Locale|The language that this content is in. This is in code format (e.g. en) and not in display format _English_|
|Name|The name of the ordered content set|
|Profile Fields|This is a comma separated list of the profile fields that are applicable for this ordered content set. Each item is separated by a comma, and each item contains the field name and field value, separated by a colon. e.g. `gender:male, relationship:single`|
|Page Slugs|This is a comma separated list of the slugs for all of the pages contained in the ordered content set, in order. These pages must exist in the CMS when importing|
|Time|This is the relative time for each of the content pages, in a comma separated list, e.g. `5, 10`|
|Unit|This is the unit for the relative time for each of the content pages, in a comma separated list, e.g. `minutes, days`|
|Before Or After|This is whether the relative time is before or after for each of the content pages, in a comma separated list, e.g. `before, after`|
|Contact Field|This is the contact field that the relative time is evaluated against, for each of the content pages, in a comma separated list, e.g. `signup, edd`

# Importing and Exporting Forms/Assessments
This features allows you to bulk import and export forms/assessments in Excel (.xlsx) and comma-separated value (.csv) file format.

## Importing
On the assessments list page, click the import button. You will then be presented with the following fields:
|Name|Description|
|----|-----------|
|File|The file that you want to upload, that contains the details of the assessments|
|File type|The type of the file that you want to upload, either CSV or Excel|
|Purge|Whether to delete all existing assessments before creating the ones specified in the file. This option is for if your upload file contains all the assessments in the CMS, and is useful if you want to ensure that deleted rows in the file result in those assessments being deleted from the CMS|
|Locale|Whether to upload all of the locales that are present in the import file, or to filter and only import a subset of the import file that matches the selected locale. Keep in mind that purge deletes all locales, independent of what is selected on this option.|

After starting the upload, you will be presented with a progress bar. When the import is done, you will either be presented with a success message, or an error message. Hopefully the error message is useful enough for you to fix the import file and try again. If not, please contact engineering to investigate the error, and ensure that there's a useful error message if this issue happens again.

If an import has an error, the data in the CMS will be reverted to its original state before the import started, similar to content pages.

Each row represents a single question in an assessment. The fields that are assessment-specific and not question-specific are repeated in each row.

## Exporting
In the assessments list view, you can click the "Download XLSX" button to perform an export in Excel format. For CSV format, click the arrow to the right of that button, and when the drop-down opens select the "Download CSV" button.

The export creates files in the same format that the importer expects.

Each question is on a separate row, with the fields that are the same for all questions in an assessment repeated.

## Fields
These are the fields that the importer expects and the exporter exports

|Name|Description|
|----|-----------|
|title|The human-readable title for the assessment|
|question_type|The type of question, e.g. `freetext_question` or `categorical_question`|
|tags|A comma-separated list of tags, e.g. `assessment,locus_of_control`|
|slug|Combined with the locale, this forms the unique identifier for this assessment|
|version|The version of this assessment. This is used during data analysis, to ensure that we do not compare user responses when they have different meanings, because the assessment had significant changes|
|locale|The locale of the questions and answers. This is in code format, not display format like content pages, e.g.`en`|
|high_result_page|The slug of the content page that is displayed to the user if their resulting score is categorized as high risk. This page must exist|
|high_inflection|The percentage that if the user scores at or above, categorizes them as high risk|
|medium_result_page|The slug of the content page that is displayed to the user if their resulting score is categorized as medium risk. This page must exist|
|medium_inflection|The percentage that if the user scores at or above, but below high_inflection, categorizes them as medium risk. Any percentage below this categorizes the user as low risk|
|low_result_page|The slug of the content page that is displayed to the user if their resulting score is categorized as low risk. This page must exist|
|skip_threshold|The maximum number of questions that can be skipped, before the user is shows the skip_high_result_page instead of their risk category result page|
|skip_high_result_page|The slug of the content page that is displayed to the user if they skip at or above the number of questions specified in the skip_threshold. This page must exist|
|generic_error|If the specific question doesn't have an error specified, and the user enters invalid input, this error message will be used|
|question|The question text that will be asked of the user|
|explainer|Text that can be shown to the user if they enquire why we are asking this question|
|error|Question-specific error if the user enters an invalid response|
|min|Used for integer question types, the minimum value that the user can enter|
|max|Used for integer question types, the maximum value that the user can enter|
|answers|Used for categorical and multi-select question types. A comma separated list of possible answers that a user can choose|
|scores|Used for categorical and multi-select question types. A comma separated list of scores, one for each possible answer|
|answer_semantic_ids|Used for categorical and multi-select question types. A comma separated list of IDs, one for each possible answer, that must be unique per question. These are used for storing user results, and remain the same across all translations. e.g. `Agree,Not sure,Disagree`|
|question_semantic_id|An identifier for this question, it is unique per assessment. This is used for storing user results, and remains the same across all translations. e.g. `age`.