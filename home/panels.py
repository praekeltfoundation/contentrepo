from django.utils.html import format_html
from wagtail.admin.panels import Panel


class PageRatingPanel(Panel):
    class BoundPanel(Panel.BoundPanel):
        template_name = "panels/page_rating_panel.html"

        def get_context_data(self, parent_context=None):
            context = super().get_context_data(parent_context)
            context["page_value"] = self.instance.page_rating
            context["revision_value"] = self.instance.latest_revision_rating
            return context

        def render(self):
            page_value = self.instance.page_rating
            revision_value = self.instance.latest_revision_rating
            return format_html(
                '<ul class="fields"><li><div style="padding-top: 1.2em;">'
                'Page: {}</div><div style="padding-top: 1.2em;">'
                "Latest Revision: {}</div></li></ul>",
                page_value,
                revision_value,
            )

        def render_as_object(self):
            return format_html(
                "<fieldset><legend>{}</legend>"
                '<ul class="fields"><li><div class="field">{}</div></li></ul>'
                "</fieldset>",
                self.heading,
                self.render(),
            )
