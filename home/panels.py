from django.utils.html import format_html
from wagtail.admin.edit_handlers import EditHandler


class PageRatingPanel(EditHandler):
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
