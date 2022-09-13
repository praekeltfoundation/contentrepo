from wagtail.admin.panels import Panel


class PageRatingPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "panels/page_rating_panel.html"

        # def get_context_data(self, parent_context=None):
        #     context = super().get_context_data(parent_context)
        #     if self.instance:
        #         context["page_value"] = self.instance.page_rating
        #         context["revision_value"] = self.instance.latest_revision_rating
        #     return context
