from django.template import Context, loader, RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404
from django.core.context_processors import csrf
from django.contrib.auth.models import User
from MediaListDJ.ml.models import *
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core import serializers
from django.utils import simplejson
from django.core.mail import send_mail
from MediaListDJ import settings
from MediaListDJ.ml.templatetags import ml_extras
from smtplib import SMTPException
from MediaListDJ.ml import mediamanager
from MediaListDJ.ml.loaders.webloader import WebLoadError, UnknownSourceError
from haystack.views import SearchView
import re
from django.views.generic.list_detail import object_list

def index(request):
    if request.user.is_authenticated(): # Pagination and user items 
        return media_list(request, request.user.username)
    else:
        return renderPage(request, "ml/static/info.html")

def importRating(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    c = Context()
    mediamanager.loadImportTasks(c,request.user)
    
    return renderPage(request, "ml/import.html", c)

def user_profile(request, username):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    
    if request.user.username != username:
        return HttpResponseForbidden()
    
    c = Context()
    c['disp_user'] = request.user
    
    return renderPage(request, "ml/profile.html", c)


def addImportSite(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    url = request.POST['site']
    loader = mediamanager.getSiteLoaderFromUrl(url)
    c = Context()
    mediamanager.loadImportTasks(c,request.user)
    if not loader:
        c['ml_error'] = "The site you specified is not supported yet."
        return renderPage(request, "ml/import.html", c) 
    else:
        if not loader.isValidRatingListUrl(url):
            c['ml_error'] = "The page you specified is not a valid list."
            return renderPage(request, "ml/import.html", c)
        
        try:
            task = RatingImportTask.objects.get(user=request.user, source=loader.getSource())
            c['ml_error'] = "You already added a list for this site"
            return renderPage(request, "ml/import.html", c) 
        except RatingImportTask.DoesNotExist:
            task = RatingImportTask(user=request.user, source=loader.getSource(), url=url)
            
            # If the user has no ratings for this source, mark the import task as fresh
            # (so we can possibly give the user the option to import immediately)
            sourceMediaCount = RatingEvent.objects.filter(user=request.user, source=loader.getSource()).count()
            if sourceMediaCount == 0:
                task.lastResult = RatingImportTask.RESULT_FRESH
            else:
                task.lastResult = RatingImportTask.RESULT_OK
            
            task.save()
            return HttpResponseRedirect(reverse("ml_import"))


def deleteImportSite(request, task_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    c = Context()
    mediamanager.loadImportTasks(c,request.user)
    try:
        task = RatingImportTask.objects.get(pk=task_id)
        if task.user.id == request.user.id:
            task.delete()
            return HttpResponseRedirect(reverse("ml_import"))
        else:
            c['ml_error'] = "Invalid request"
            return renderPage(request, "ml/import.html", c) 
    except RatingImportTask.DoesNotExist:
        raise Http404
   

def media_list(request, username, typename=None, statusname=None):
    c = {}
    try:
        user = User.objects.get(username=username)
        c['disp_user'] = user
        if request.user.id == user.id:
            c['editable'] = True
    except User.DoesNotExist:
        raise Http404
    
    ratingList = RatingEvent.objects.filter(user=user, parent=None).order_by('-date', '-id')
    
    #check for actions
    
    if 'n' in request.GET:
        titleFilter = request.GET['n'].strip()
        filters = re.compile("\s+").split(titleFilter)
        for item in filters:
            ratingList = ratingList.filter(media__name__icontains=item)
        
        c['filter_title'] = titleFilter
        
    
    if typename:
        typename = ml_extras.unurlify(typename)
        try:
            type = MediaType.objects.get(name=typename)
            c['type'] = type
            c['hidemediatype'] = True
            ratingList = ratingList.filter(media__type__id=type.id)
        except MediaType.DoesNotExist:
            raise Http404
    
    if statusname:
        statusname = ml_extras.unurlify(statusname)
        try:
            status = Status.objects.get(name=statusname, type__id=type.id)
            c['status'] = status
            ratingList = ratingList.filter(status__id=status.id)
        except Status.DoesNotExist:
            raise Http404
    
    #mediamanager.paginate(request, ratingList, c)
    #return renderPage(request, "ml/medialist.html", c)
    
    # better pagination:
    #c = __prepareExtraContext(request, c) #didn't work!
    if not c.has_key('disp_user') and request.user.is_authenticated():
        c['disp_user'] = request.user
    c.update(csrf(request))
    mediamanager.loadMediaTypes(c);
    
    return object_list(request, template_name="ml/medialist.html", queryset = ratingList,
                       paginate_by=18, extra_context=c, template_object_name="ratings")
    
    


def media_notify_done(request, media_id):
    c = Context()
    try:
        media = Media.objects.get(pk=media_id)
        c['media'] = media
        c['type'] = media.type
        c['sources'] = media.sourcemedia_set.all()
    except Media.DoesNotExist:
        raise Http404
    return renderPage(request, "ml/media_notify_done.html", c)


def media_notify(request, media_id):
    c = Context()
    try:
        media = Media.objects.get(pk=media_id)
        c['media'] = media
        c['type'] = media.type
        c['sources'] = media.sourcemedia_set.all()
    except Media.DoesNotExist:
        raise Http404
    
    message = request.POST.get('message', '')
    info = request.POST.get('info', '')
    
    if message and len(message) > 0:
        if not request.user.is_authenticated():
            raise HttpResponseForbidden # require user to make a correction
        
        mn = MediaNotification(user=request.user,media=media,message=message,
                               date=mediamanager.nowDateTimeString(),
                               info=info, host=str(request.META['REMOTE_ADDR']))
        mn.save()
        return HttpResponseRedirect(reverse("ml_media_notify_done",args=[str(media.id)]))
    else:
        return renderPage(request, "ml/media_notify.html", c)


def media(request, media_id):
    c = {}
    try:
        print "Media:" + str(media_id)
        media = Media.objects.get(pk=media_id)
        c['media'] = media
        c['hidemedianame'] = True #don't show name in media rating list
        c['hidemediatype'] = True
        c['hideratingheader'] = False
        c['type'] = media.type
        c['sources'] = media.sourcemedia_set.all()
        mediamanager.loadMediaRatings(request, media_id, c)
        
        # children?
        children = media.children.all().order_by('order')
        if len(children) > 0:
            c['children'] = children
        
    except Media.DoesNotExist:
        raise Http404
    
    # User ratings, editable, average, count
    ratingList = ()
    if request.user.is_authenticated():
        c['disp_user'] = request.user
        c['editable'] = True
        ratingList = RatingEvent.objects.filter(user__id=request.user.id)
        ratingList = ratingList.filter(media__id=media_id)
        ratingList = ratingList.order_by('-date', '-id')
    
    c.update(csrf(request))
    mediamanager.loadMediaTypes(c);
    
    return object_list(request, template_name="ml/media.html", queryset = ratingList,
                       paginate_by=18, extra_context=c, template_object_name="ratings")
    
    #return renderPage(request, "ml/media.html", c)


def contact(request):
    user = request.POST.get('name')
    message = request.POST.get('message', '')
    from_email = request.POST.get('email', '')
    to_email = settings.CONTACT_EMAIL

    if user and message and from_email:
        subject = "Contact form: " + user
        try:
            send_mail(subject, message, from_email, [to_email])
        except SMTPException:
            return HttpResponse('Could not send your contact request.')
        return HttpResponseRedirect(reverse("ml_static",args=["thankyou"]))
    else:
        c = Context()
        return renderPage(request, "ml/contact.html", c)


def static(request, pagename):
    if not pagename: 
        return Http404
    return renderPage(request, "ml/static/" + str(pagename) +".html")

def ajaxUpdateMediaRatingEvent(request, media_id, re_id, update_what, new_value, type_id=-1):
    if re_id and int(re_id) > 0:
        return ajaxUpdateRatingEvent(request, re_id, update_what, new_value, type_id)
    
    # RatingEvent does not exist, we must make a new one
    if not request.user.is_authenticated():
        return HttpResponseForbidden
    
    # figure out if there's a most recent RatingEvent that can be modified
    try:
        media = Media.objects.get(pk=media_id)
    except Media.DoesNotExist:
        print "Unknown media: "+str(media_id)
        raise Http404 # Should handle this better
    
    ratingEvent = media.getMostRecentRatingEvent(request.user)
    if ratingEvent: 
        if update_what == 'status' and new_value == 0:
            # This would delete the user's most recent rating after he added it somewhere else - very bad!
            # instead we just return the rating's current information
            return ajaxUpdateRatingEvent(request, ratingEvent.id, 'status', ratingEvent.status.id, type_id)
        else:
            # This only happens if the user used a different browser window
            # to add a new rating, then returned to the other browser window
            # that didn't know about the rating yet
            return ajaxUpdateRatingEvent(request, ratingEvent.id, update_what, new_value, type_id)
       
    # Create a new event 
    try:
        defaultStatus = media.type.status_set.get(default=True)
    except Status.DoesNotExist:
        raise Http404 # Should handle this better
    ratingEvent = RatingEvent(media=media, date=mediamanager.nowDateString(),
                     user=request.user,rating=0, status=defaultStatus)
    ratingEvent.save()
    
    if update_what == 'status' and new_value == 0:
        return ajaxUpdateRatingEvent(request, ratingEvent.id, 'status', ratingEvent.status.id, type_id)
    else: # only update if the new rating won't be deleted
        return ajaxUpdateRatingEvent(request, ratingEvent.id, update_what, new_value, type_id)


def ajaxUpdateRatingEvent(request, re_id, update_what, new_value, type_id=-1):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    
    re = None
    media = None
    try:
        re = RatingEvent.objects.get(pk=re_id)
        media = re.media
    except RatingEvent.DoesNotExist:
        raise Http404
    
    if not re.user.id == request.user.id:
        print "Invalid user! re user: %s request user: %s" % (str(re.user.id), str(request.user.id))
        return HttpResponseForbidden("You are not allowed to access this page")

    wasDeleted = False
    error = None
    if update_what == 'status':
        if int(new_value) <= 0: #delete
            error = mediamanager.deleteRating(re)
            wasDeleted = True
        else:
            error = mediamanager.updateStatus(re, new_value)
    elif update_what == 'rating':
        error = mediamanager.updateRating(re, new_value)
    elif update_what == 'progress': # check that status allows updates!
        if not re.status.durationEditable():
            error = "Cannot edit duration"
        else:
            error = mediamanager.updateProgress(re, new_value, type_id)
    elif update_what == 'date':
        error = mediamanager.updateDate(re, new_value)
    else:
        error = "Invalid update item"
    
    # Prepare the response
    if wasDeleted:
        myData = mediamanager.toAjaxDict(None, media)
    elif update_what == 'date': #don't need all the heavy stuff
        myData = {'id':re.id, 'date':re.date.strftime("%Y-%m-%d")}
    else:
        myData = mediamanager.toAjaxDict(re, re.media, dict={}, type_id=type_id)
        
    if error:
        myData["error"] = error
    else:
        myData["message"] = update_what + " updated!"
    
    return HttpResponse(simplejson.dumps(myData), mimetype='application/json')


def addRating(request):
    # add a rating!
    # TODO add errors to context and render immediately to response!
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    else:
        media_id    = request.POST['media_id']
        date        = request.POST['media_date']
        rating      = request.POST['media_rating']
        status_id   = request.POST['media_status']
        
        try:
            media = Media.objects.get(pk=media_id)
        except Media.DoesNotExist:
            raise Http404
        
        result = mediamanager.addRating(user=request.user, media_id=media_id, date=date, rating=rating, status_id=status_id)
        c = Context()
        if result: 
            c['ml_error'] = result
            c['media'] = media
            c['type'] = media.type
            return renderPage(request, "ml/addrating_result.html", c) 
        else:
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("ml_home")))


def addExternalRating(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    else:
        url = request.POST['media_url']
        
        if 'seen_date' in request.POST:
            seenDate = request.POST['seen_date']
        else:
            seenDate = mediamanager.nowDateString()
            
        rating = int(request.POST['media_rating'])
        
        print "Loading from url: "+url
        
        c = Context()
        
        # do stuff here
        sourceMedia = None
        try:
            sourceMedia = mediamanager.addSourceMedia(url)
        except UnknownSourceError, e:
            # Can't help it, really 
            c['ml_error'] = e.value
            return renderPage(request, "ml/addrating_result.html", c)
        except WebLoadError, e:  # Couldn't parse the url
            c['ml_error'] = e.value
            # Store error
            mn = MediaNotification(message="URL add failure",url=url, 
                                   date=mediamanager.nowDateTimeString(),
                                   host=str(request.META['REMOTE_ADDR']),
                                   user=request.user,info="Error: "+e.value)
            mn.save()
            return renderPage(request, "ml/addrating_result.html", c)
            
        stati = Status.objects.filter(type=sourceMedia.media.type,default=1)[:1]
        status = stati[0]
        try:
            umr = RatingEvent.objects.get(date=seenDate, user=request.user, media=sourceMedia.media)
            c['ml_error'] = "You already rated this item on this date"
            return renderPage(request, "ml/addrating_result.html", c)
        except RatingEvent.DoesNotExist:
            umr = RatingEvent(user=request.user,rating=rating,status=status,
                                  date=seenDate,media=sourceMedia.media,source=None) # ML is the source
            umr.save()
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("ml_home")))
      

def deleteRating(request):
    # add a rating!
    # TODO add errors to context and render immediately to response!
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse("auth_login"))
    else:
        result = mediamanager.deleteRatingFromPostVars(request.user, request.POST)
        c = Context()
        if result: 
            c['ml_error'] = result
            return renderPage(request, "ml/deleterating_result.html", c) 
        else:
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("ml_home")))


def renderPage(request, pageName, otherDict={}):
    c = __prepareExtraContext(request, otherDict)
    return render_to_response(pageName, c)

def __prepareExtraContext(request, otherDict={}):
    c = RequestContext(request)
    
    if not otherDict.has_key('disp_user') and request.user.is_authenticated():
        otherDict['disp_user'] = request.user
    
    otherDict.update(csrf(request))
    otherDict['next'] = request.path
    mediamanager.loadMediaTypes(otherDict);
    
    c.update(otherDict)
    return c


class MediaSearchView(SearchView):
    def __name__(self):
        return "MediaSearchView"
    
    
    def extra_context(self):
        extra = super(MediaSearchView, self).extra_context()
        
        if 'cleaned_data' in self.form and self.form.cleaned_data['t']:
            try:
                type = MediaType.objects.get(name=self.form.cleaned_data['t'])
                extra['type'] = type
            except MediaType.DoesNotExist:
                pass # it's ok
        
        mediamanager.loadMediaTypes(extra)
        
        if self.request.user.is_authenticated(): # Load ratingevents(the slow way)
            extra['disp_user'] = self.request.user
        
        return extra
    
    
    def build_rating_results(self, paginator, page):
        rating_results = []
        if self.request.user.is_authenticated():
            for res in page.object_list:
                media = res.object
                ratingEvent = media.getMostRecentRatingEvent(self.request.user)
                rating_results.append((media,ratingEvent))
        else:
            for res in page.object_list:
                rating_results.append((res.object,None))
        return rating_results
    
    
    def create_response(self):
        """
        Generates the actual HttpResponse to send back to the user.
        """
        paginator = Paginator(self.results, self.results_per_page)
        try:
            page = self.request.GET.get('page', 1)
            page_data = paginator.page(page)
        except InvalidPage:
            raise Http404
        
        context = {
            'query': self.query,
            'form': self.form,
            'page': int(page),
            'pages': paginator.num_pages,
            
            'page_obj': page_data,
            'hits': 0, #what's this?
            'results_per_page': self.results_per_page,
            'paginator': paginator,
            
            'next': int(page)+1,
            'previous': int(page)-1,
            'has_next': int(page)+ 1 <= paginator.num_pages, # TODO check this!
            'has_previous': int(page)-1 > 0, # TODO check this!
            
            'suggestion': None,
        }
        
        rating_results = self.build_rating_results(paginator, page_data)
        context['rating_results'] = rating_results
        context['empty'] = len(rating_results) == 0
        
        if getattr(settings, 'HAYSTACK_INCLUDE_SPELLING', False):
            context['suggestion'] = self.form.get_suggestion()
        
        context.update(self.extra_context())
        
        context['query_param'] = "?q=" + self.query + "&t="
        if 'type' in context:
            context['query_param'] += context['type'].id
        context['query_param'] += "&"
        print "QP: " + context['query_param']
        
        return render_to_response(self.template, context, context_instance=self.context_class(self.request))


