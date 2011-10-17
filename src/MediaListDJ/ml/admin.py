from MediaListDJ.ml.models import *
from django.contrib import admin
from django import forms

class DifferentlySizedTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        attrs = kwargs.setdefault('attrs', {})
        attrs.setdefault('cols', 200)
        attrs.setdefault('rows', 1)
        super(DifferentlySizedTextarea, self).__init__(*args, **kwargs)

class StatusInline(admin.TabularInline):
    model = Status
    extra = 5

class SourceMediaInline(admin.TabularInline):
    model = SourceMedia
    extra = 1

class MediaInfoInline(admin.StackedInline):
    model = MediaInfo


class MediaNotificationAdmin(admin.ModelAdmin):
    list_display = ['date','media','user','message','url','host']
    list_display_links = ['message']

class MediaAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    list_display_links = ['id', 'name']
    list_filter = ['type']
    raw_id_fields = ['parent']
    search_fields = ['name']
    ordering = ['name']
    inlines = [MediaInfoInline,SourceMediaInline]

class MediaTypeAdmin(admin.ModelAdmin):
    list_display = ('name','parent')
    search_fields = ['name']
    inlines = [StatusInline]
    
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'importClass','domain')
    search_fields = ['name']
    formfield_overrides = { models.TextField: {'widget': DifferentlySizedTextarea}}

class BaseStatusAdmin(admin.ModelAdmin):
    #list_display = ('name',)
    search_fields = ['name']
    inlines = [StatusInline]
    

admin.site.register(Media, MediaAdmin)
admin.site.register(MediaType, MediaTypeAdmin)
admin.site.register(BaseStatus, BaseStatusAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(MediaNotification, MediaNotificationAdmin)

