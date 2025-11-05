## Reports

The "Reports" section in the CMS provides valuable insights into the status and performance of your content.

---

### Stale Content

The **Stale Content Report** helps you identify pages that have not been updated recently, which might indicate that the content is outdated.

* **Functionality**: This report lists all pages.
* **Filtering**: You can filter the report by:
    * **Last published before**: To view content that has last changed before this date.
    * **View count**: (deprecated) To see pages that have fewer amount of views than this amount.
    * **Live**: Whether or not the page has been published
* **Ordering**: You can order the report by:
   * **View count**: (deprecated) The number of views that the content has.
   * **Latest published**: When last an update to this page was published.

---

### Page Views (deprecated)

The **Page Views Report** provides a visual overview of how users are interacting with your content over time.

* **Functionality**: This report displays a chart of the total page views per month. Page views are tracked using a `PageView` model that records each time a page is accessed.
* **Data Tracked**: For each page view, the following information is recorded:
    * The **page** that was viewed.
    * The **timestamp** of the view.
    * The **platform** used to view the content (e.g., "web", "whatsapp").
    * The specific **message** number within the page that was viewed (for multi-message platforms like WhatsApp).
* **Filtering**: You can filter the report by
    * **Date Range** To analyse page views over a custom period.
    * **Platform** A Specific platform (e.g. WhatsApp, SMS), to see the page views for just that platform
    * **Page** Show only the page views for a specific page