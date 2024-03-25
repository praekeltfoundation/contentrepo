from django.contrib import admin

from .models import PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = [field.name for field in PageView._meta.get_fields()]


# @admin.register(WhatsAppTemplate)
# class WhatsappTemplateAdmin(admin.ModelAdmin):
#     list_display = [field.name for field in WhatsAppTemplate._meta.get_fields()]
