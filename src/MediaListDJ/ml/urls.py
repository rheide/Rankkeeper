from django.conf.urls.defaults import *
from django.contrib import admin
from django.contrib.auth.views import password_reset, password_reset_done, password_change, password_change_done
from haystack.forms import ModelSearchForm
from haystack.query import SearchQuerySet
from haystack.views import SearchView, search_view_factory
from search_form import MediaSearchForm
from MediaListDJ.ml.views import MediaSearchView

urlpatterns = patterns('MediaListDJ.ml.views',
   
    url(r'^$', 'index',name='ml_home'),
    
    # Media
    url(r'^media/(?P<media_id>\d+)/$','media',name='ml_media'),
    url(r'^media/(?P<media_id>\d+)/notify/$','media_notify',name='ml_media_notify'),
    url(r'^media/(?P<media_id>\d+)/notify/done/$','media_notify_done',name='ml_media_notify_done'), 
    
    # Ratings
    url(r'^addexternal/$','addExternalRating',name='ml_addexternal'),
    url(r'^addrating/$','addRating', name='ml_addrating'),
    url(r'^deleterating/$','deleteRating', name='ml_deleterating'),
    
    
    # Ajax rating update for media
    url(r'^rating/m(?P<media_id>\d+)r(?P<re_id>\d+)/update/(?P<update_what>[a-z]+)/(?P<new_value>\d+)/$','ajaxUpdateMediaRatingEvent'),
    url(r'^rating/m(?P<media_id>\d+)r(?P<re_id>\d+)/update/(?P<update_what>[a-z]+)/type/(?P<type_id>\d+)/(?P<new_value>\d+)/$','ajaxUpdateMediaRatingEvent'),
    
    
    # Ajax rating update
    url(r'^rating/(?P<re_id>\d+)/update/(?P<update_what>[a-z]+)/(?P<new_value>[^/]*)/$','ajaxUpdateRatingEvent'),
    url(r'^rating/(?P<re_id>\d+)/update/(?P<update_what>[a-z]+)/type/(?P<type_id>\d+)/(?P<new_value>\d+)/$','ajaxUpdateRatingEvent'),
    
    # Import
    url(r'^import/$','importRating',name='ml_import'),
    url(r'^import/add/$','addImportSite', name='ml_import_add'),
    url(r'^import/delete/(?P<task_id>\d+)/$','deleteImportSite', name='ml_import_delete'),
    
    
    # Misc
    url(r'^contact/$','contact', name='ml_contact'),
    url(r'^static/(?P<pagename>[a-zA-Z0-9_-]+)/$','static',name='ml_static'),
    
    
    # User registration
    (r'^user/', include('registration.backends.default.urls')),
    url(r'^users/(?P<username>[a-zA-Z0-9_-]+)/profile/$','user_profile',name='ml_profile'),

    # Media lists
    url(r'^users/(?P<username>[a-zA-Z0-9_-]+)/$','media_list',name='ml_list'),
    url(r'^users/(?P<username>[a-zA-Z0-9_-]+)/(?P<typename>[a-zA-Z0-9_-]+)/$','media_list',name='ml_list-type'),
    url(r'^users/(?P<username>[a-zA-Z0-9_-]+)/(?P<typename>[a-zA-Z0-9_-]+)/(?P<statusname>[a-zA-Z0-9_-]+)/$','media_list',name='ml_list-typestatus'),
    
    # Django Admin
    (r'^admin/', include(admin.site.urls)),
)

# Search
urlpatterns += patterns('haystack.views',
    url(r'^search/', search_view_factory(
        view_class=MediaSearchView,
        template='ml/search.html',
        form_class=MediaSearchForm
    ), name='haystack_search'),
)


# More user administration


