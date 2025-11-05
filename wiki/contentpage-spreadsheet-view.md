# Contentrepo ContentPages View

The ContentPages view is a spreadsheet view that shows a spreadsheet view of the `ContentPage` objects in the Contentrepo. This gives the user a good overview of all the content currently available on the Contentrepo. You can find it by clicking "ContentPages" in the left sidebar, or by navigating to "/admin/home/contentpage/".

The view has the headings `Slug`, `Title`, `Web Body`, `Subtitle`, `Whatsapp Body`, `Messenger Body`, `SMS Body`, `USSD Body`, `Quick Replies`, `Triggers` `Tags`, `Related pages`, `Parent`.
 
This view is managed in `home/wagtail_hooks.py` under the class `ContentPageAdmin`, which is a `ModelAdmin` with methods to convert the object's attributes to string.

The content sheet in this view can also be exported to either `XLSX` or `CSV` format. The export logic resides in the `home/content_import_export.py` and is further discussed in [Export ContentPage](import-and-export).

The custom spreadsheet export logic is implemented by adding a `CustomIndexView` in `home/views.py`. This index view then makes use of the `SpreadsheetExportMixin` in `home/mixins.py`, which implements the custom export logic for the CSV and XLSX formats, by calling the methods defined in `home/content_import_export.py`

There is also an "Import" button, which facilitates importing exported CSV and XLSX files. The import logic can be found in `home/import_content_pages.py`, which is called by the `ContentUploadView` defined in `home/views.py`. Import is further discussed in [Import Content](import-and-export)