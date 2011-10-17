from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings

admin.autodiscover()

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^MediaListDJ/', include('MediaListDJ.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    #(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    
    (r'^', include('MediaListDJ.ml.urls')),
    
)

if settings.DEBUG: # Debug: serve static files
    print "Debug ON: static files served!"
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve',
        {'document_root': 'K:/Workspace/MLWorkspace/MediaListDJ/static',
         'show_indexes': True}),
         
         )
