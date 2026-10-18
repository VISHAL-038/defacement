from django.contrib import admin
from .models import MonitoredWebsite, WebPage

@admin.register(MonitoredWebsite)
class MonitoredWebsiteAdmin(admin.ModelAdmin):
    list_display = ('uid', 'url','frequency')

@admin.register(WebPage)
class WebPageAdmin(admin.ModelAdmin):
    list_display = ('uid', 'website', 'url', 'pageHash', 'createdAt')
    list_filter = ('website',)
    search_fields = ('url', 'pageHash')
