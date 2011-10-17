from MediaListDJ.ml.models import *
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.db import *
from MediaListDJ.ml.loaders.webloader import WebLoadError, UnknownSourceError
import datetime
import time
import urlparse
from MediaListDJ.ml.templatetags import ml_extras

# Dummy
#connection = None

def loadImportTasks(context, user):
    tasks = RatingImportTask.objects.filter(user=user).order_by('source__name')
    context['tasks'] = tasks


def loadMediaTypes(context):
    topLevelTypes = MediaType.objects.filter(parent = None, active=True).order_by('name')
    types= []
    if 'type' in context:
        __loadTypeRows(context,context['type'], types) # load parents
        children = context['type'].children.all().order_by('name')
        if len(children) > 0:
            types.append(children)
        
    types.insert(0,topLevelTypes)
    context['media_types'] = types
    
    context['has_media_type'] = True
    #c['statuses'] = Status.objects.all().order_by('name')
    statuses = {}
    allTypes = MediaType.objects.all().order_by('name')
    for type in allTypes:
        statuses[type.id] = Status.objects.filter(type__id=type.id)
        context['status_%s' % type.id] = statuses[type.id]
        #print "Length : %s %d" % ("%s" % type.id, len (statuses[type.id]))
    context['statuses'] = statuses
    context['all_types'] = allTypes


def __loadTypeRows(c, currentType, types):
    if currentType.parent: 
        typeRow = currentType.parent.children.all().order_by('name')
        types.insert(0,typeRow)
        __loadTypeRows(c, currentType.parent, types)


def importFromSite(task):
    # TODO implement minimum import time interval!
    loader = getSiteLoader(task.source)
    if not loader:
        return "Cannot find loader for site"
    try:
        errors = loader.importFromRatingList(task.user, task.url) # TODO handle errors!
        task.lastImportDate = nowDateTimeString()
        task.save()
    except WebLoadError, e:
        return e.value
    

def nowDateTimeString():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def nowDateString():
    return datetime.datetime.now().strftime("%Y-%m-%d")

def dateToString(myDate):
    return time.strftime("%Y-%m-%d %H:%M:%S", myDate)

def deleteRatingFromPostVars(user, postVars):
    for umr_id in postVars.getlist("delrating"):
        try:
            # delete multiple ratings! (of course only of request's user, not of someone else)
            umr = RatingEvent.objects.get(pk=umr_id,user=user)
            deleteRating(umr)
            #print "Deleted umr %s" % umr_id
        except RatingEvent.DoesNotExist:
            print "Couldn't find umr item: %s" % umr_id
            #handle error here!


def deleteRating(ratingEvent):
    for rep in ratingEvent.ratingeventprogress_set.all():
        rep.delete()
    ratingEvent.delete()
    return None


def loadMediaRatings(request, media_id, context):
    # Load average
    queryString = "SELECT avg(rating.mr), count(rating.mr) FROM " \
                  "( SELECT max(re.rating) AS mr " \
                  "FROM ml_ratingevent re " \
                  "WHERE re.media_id = %s "\
                  "GROUP BY re.user_id) rating"
    cursor = connection.cursor()
    cursor.execute(queryString, [media_id])
    row = cursor.fetchone()
    cursor.close()
    
    # Create dummy average
    if row[0]:
        context['average'] = row[0]
        context['average_text'] = "%.1f" % row[0]
    else:
        context['average'] = 0
        context['average_text'] = 0
        
    if row[1]:
        context['unique_count'] = row[1]
    else:
        context['unique_count'] = 0
    
    
    # Load count
    queryString = "SELECT count(re.id) " \
                  "FROM ml_ratingevent re " \
                  "WHERE re.media_id = %s "
    cursor = connection.cursor()
    cursor.execute(queryString, [media_id])
    rowCount = cursor.fetchone()
    cursor.close()
    
    if rowCount[0]:
        context['total_count'] = rowCount[0]
    else:
        context['total_count'] = 0
    
    
def paginate(request, ratingList, context):
    paginator = Paginator(ratingList, 18) # ratings per page    
    try:
        page = int(request.GET.get("page", "1"))
    except ValueError:
        page = 1
    
    try:
        ratings = paginator.page(page)
    except (EmptyPage, InvalidPage):
        ratings = paginator.page(paginator.num_pages)
    context['ratings'] = ratings
    
    
def addRating(user, media_id, rating=0, date=nowDateString(), status_id=None, source=None):
    print "Adding rating for media: " + str(media_id) + " - " + str(date) + " - " + str(status_id)
        
    # Find media type
    try:
        media = Media.objects.get(pk=media_id)
        
        if status_id:
            status = Status.objects.get(pk=status_id)
            if media.type.id != status.type.id:
                return "Status invalid for given media"
        else:
            status = media.type.status_set.get(default=True)
    except Media.DoesNotExist:
        return "Could not find media: "+str(media_id)
    except Status.DoesNotExist:
        return "Could not find status: "+str(status_id)
    
    # Let user rate the same thing multiple times on the same day
    re = RatingEvent(media=media, date=date, rating=rating, user=user, source=source, status=status)
    re.save()
    updateStatus(re, status_id) # This will set the appropriate progress
    
    return None #no errors

def addSourceMedia(url):
    loader = getSiteLoaderFromUrl(url)
    
    if not loader:
        raise UnknownSourceError("[01] Unknown site")
    source = loader.getSource()
    
    sourceBusinessKey = loader.getSourceBusinessKey(url)
    if not sourceBusinessKey:
        raise WebLoadError("[02] Cannot parse url")
        
    # look up source business key in database, use existing object if available
    try:
        sourceMedia = SourceMedia.objects.get(source__id = source.id, businessKey=sourceBusinessKey)
        return sourceMedia
    except SourceMedia.DoesNotExist:
        # We must ask the loader to provide more information about the media
        media = loader.loadMedia(url) # potentially very very slow
        # We rely on the loader to save the media!
        if not media or not media.mediainfo:
            raise WebLoadError("[03] Cannot parse url") 
                 
        url = loader.getUrl(sourceBusinessKey) # safe url
        sourceMedia = SourceMedia(source=source, media=media, 
                                  businessKey=sourceBusinessKey, url=url)
        sourceMedia.save()  # TODO do all saves in a single transaction
        return sourceMedia


def getSiteLoaderFromUrl(url):
    domain = urlparse.urlparse(url)
    
    if not domain:
        return None
    
    domain = domain.hostname
    
    try:
        source = Source.objects.get(domain=domain)
        return getSiteLoader(source)
    except Source.DoesNotExist:
        print "Warning: Source not found for url: "+url
        return None


def getSiteLoader(source):
    try:
        C = __get_class(source.importClass)
        siteLoader = C()
        siteLoader.setSource(source)
        return siteLoader
    except ImportError: # loader did not exist
        return None 


def __get_class( kls ):
    parts = kls.split('.')
    module = ".".join(parts[:-1])
    m = __import__( module )
    for comp in parts[1:]:
        m = getattr(m, comp)            
    return m


def updateStatus(re, status_id):
    try:
        re.status = Status.objects.get(pk=status_id)
        
        if not re.status.allowRating:
            re.rating = 0
        
        re.save()
        
        renewProgress = False
        new_progress = 0
        if re.status.durationMaximum():
            new_progress = 'max'
            renewProgress = True
        elif not re.status.hasDuration():
            renewProgress = True
            new_progress = 0
        
        if renewProgress:
            error = updateProgress(re, new_progress, re.media.type.id) #intrinsic 
            if error:
                return error
            for type in re.media.type.getDescendants(): #extrinsic
                error = updateProgress(re, new_progress, type.id)
                if error:
                    return error
        
    except Status.DoesNotExist:
        return "Invalid status"
    return None


def updateRating(re, new_value):
    if re.status.allowRating:
        re.rating = new_value
    else:
        re.rating = 0
    re.save()
    return None


def updateProgress(re, new_value, type_id):
    #print "Updating progress: "+str(re.id)+" - "+str(new_value)+" - "+str(type_id)
    
    if new_value != 'max' and int(new_value) < 0:
        return "Invalid duration [01]"
    
    # Find previous rating if available
    try:
        type = MediaType.objects.get(pk=type_id)
        rep = RatingEventProgress.objects.get(ratingEvent=re,type=type)
    except MediaType.DoesNotExist:
        return "Invalid type"
    except RatingEventProgress.DoesNotExist:
        rep = RatingEventProgress(ratingEvent=re,type=type)
    
    if int(type_id) == int(re.media.type.id): # Update intrinsic duration (for re's media)
        if new_value == 'max':
            rep.progress = re.media.duration
        elif int(new_value) > int(re.media.duration):
            return "Invalid duration [02]"
        else:
            rep.progress = new_value
    else: # Update extrinsic duration (for re's child media)
        itemCount = re.media.recMediaCount(type)
        if new_value == 'max':
            rep.progress = itemCount
        elif int(new_value) > int(itemCount):
            return "Invalid duration [03]"
        else:
            rep.progress = new_value
           
        # child progress must be updated as well! (deleted)
        for childType in type.getDescendants():
            RatingEventProgress.objects.filter(ratingEvent=re,type=childType).delete()
        
    rep.save()
    return None # OK


def updateDate(ratingEvent, new_date):
    try:
        tmp_date = datetime.datetime.strptime(str(new_date),"%Y-%m-%d")
        
        if tmp_date > datetime.datetime.now():
            return "You can't add ratings for a future date"
        
        ratingEvent.date = tmp_date
        ratingEvent.save()
        return None
    except ValueError, e:
        return "Error: "+str(e)
    return "Something unexpected went wrong!"


def toAjaxDict(ratingEvent,media,dict={},type_id=-1):
    dict["media_id"] = media.id
    
    if ratingEvent:
        dict["id"] = ratingEvent.id
        dict["rating"] = ratingEvent.rating
        dict["status"] = ratingEvent.status.id
        dict["progressEditable"] = 1 if ratingEvent.status.durationEditable() else 0
        dict["base_status"] = ratingEvent.status.baseStatus.name
        dict["allow_rating"] = 1 if ratingEvent.status.allowRating else 0
        progress = {}
        for red in ratingEvent.ratingeventprogress_set.all():
            progress[red.type.id] = red.progress
        dict["progress"] = progress
        
        typeRatings = ml_extras.typeRatingsDict(ratingEvent, media)
        progressRangeMap = {}
        for (type,pi) in typeRatings.items():
            if type.id == type_id: 
                continue # don't return data for the type the user just modified
            if pi.isEmptyRange():
                progressRangeMap[type.id] = 0
            else:
                html = pi.htmlProgressOptions()
                progressRangeMap[type.id] = html
        dict["range"] = progressRangeMap
    else:
        dict["id"] = 0
        dict["rating"] = 0
        dict["status"] = 0
        dict["allow_rating"] = 1
        dict["progressEditable"] = 0
        dict["base_status"] = "unseen"
        progress = {}
        progress[media.type.id] = 0
        dict["progress"] = progress
        dict["range"] = progress
        
    return dict
    
        
        
        

    