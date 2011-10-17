from django.db import models
from django.contrib.auth.models import User

# DataModel Version 1.5.0

class MediaType(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children')
    self_duration_unit = models.CharField(max_length=64, null=True)
    self_duration_unit_short = models.CharField(max_length=16, null=True)
    sub_duration_unit = models.CharField(max_length=64, null=True)
    sub_duration_unit_short = models.CharField(max_length=16, null=True)
    sub_duration_increment = models.IntegerField(default=1, null=True)
    allowComplexProgress = models.BooleanField() # implies displayed in parent
    allowIntrinsicProgress = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    
    def __unicode__(self):
        return self.name
    
    # returns a list of MediaTypes that are descendants (recursive) of self
    def getDescendants(self):
        return self.recGetDescendants(list=[], recStart=True)
    
    def recGetDescendants(self, list=[], recStart=True):
        #print str(self)+" getting descendants.. "
        if not recStart:
            #print "ExList"
            list.append(self)
        
        for type in self.children.all():
            #print str(self)+" recursing over "+str(type)
            type.recGetDescendants(list=list,recStart=False)
            
        return list


class Media(models.Model):
    type = models.ForeignKey(MediaType)
    name = models.CharField(max_length=255)
    businessKey = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children')
    order = models.IntegerField(default=0) #to specify order for the parent item
    duration = models.IntegerField(default=0)
    user = models.ForeignKey(User)
    meta_parent = models.ForeignKey('self', blank=True, null=True, related_name='meta_children')
    
    def __unicode__(self):
        return self.name
    
    def getDescendants(self,type):
        list = []
        self.recGetDescendants(type, list)
        return list
    
    def getRange(self, type): # get the total valid range for a given type that is a subtype of the media's type
        childMedia = self.getDescendants(type) # TODO put these lines in the model!
        localOffset = 0
        if len(childMedia) > 0:
            localOffset = childMedia[0].order
        return (0, len(childMedia), localOffset) 
    
    def getMostRecentRatingEvent(self, user):
        r = self.ratingevent_set.filter(user=user).order_by('-date','-id')[:1]
        if len(r) > 0:
            return r[0]
        else:
            return None # no rating available 
        
        
    def recGetDescendants(self, type, list):
        children = self.children.all().order_by('order')
        for child in children:
            if child.type.id == type.id:
                list.append(child)
        
        for child in children:
            if child.type.id != type.id:
                child.recGetDescendants(type, list)
        
    
    # Iterates over children recursively to find media count of specified type
    def recMediaCount(self,type):
        if self.type.id == type.id:
            return 1
        count = 0
        for childMedia in self.children.all():
            count += childMedia.recMediaCount(type)
        
        return count

    
    # Example: get a valid range for how many episodes the user could have watched of a TV show,
    # Given that he is currently watching season 4 (implying that he already watched s3 and hasn't watched s5 yet)
    def getSubTypeDurationRange(self, mainType, mainTypeProgress, myType):
        # Get ordered list of mainType's Media
        mediaList = self.getDescendants(mainType)  #Ex: TV Show->getDescendants(seasonType)
        if len(mediaList) == 0:
            return (0, 0, 0) # no progress available
        
        minProgress = 0
        
        #print str(self.id)+" - "+mainType.name+" items: "+str(len(mediaList))+" - progress: "+str(mainTypeProgress)
        maxIndex = mainTypeProgress - 1
        if len(mediaList) < maxIndex:
            maxIndex = len(mediaList)
        
        # Until mainTypeProgress, accumulate myType progress (recursive!)
        for i in range(maxIndex):
            #print "Range "+str(i)
            childMedia = mediaList[i] # Season i
            myMedias = childMedia.getDescendants(myType) # list of episodes
            minProgress += len(myMedias)
        
        # At mainTypeProgress, save min and max of myType progress --> that's the valid range
        myMedias = mediaList[maxIndex].getDescendants(myType)
        maxProgress = minProgress + len(myMedias) # cumulative number of eps until now + episodes in current season
        
        localRangeOffset = 0
        if len(myMedias) > 0:
            localRangeOffset = myMedias[0].order
        
        # (this doesn't work for intrinsic progress, eg. minutes of a tv show)
        # (should add a special case for that?)
        return (minProgress,maxProgress, localRangeOffset)
    

    
class MediaInfo(models.Model):
    key = models.CharField(max_length=255,null=False, blank=False)
    value = models.CharField(max_length=255,null=False, blank=False)
    media = models.ForeignKey(Media)
    def __unicode__(self):
        return self.media.name


class BaseStatus(models.Model):
    name = models.CharField(max_length=64)
    def __unicode__(self):
        return self.name


class Status(models.Model):
    NO_DURATION = 0
    PARTIAL_DURATION = 1
    FULL_DURATION = 2
    UNBOUND_DURATION = 3 # Might need this later?
    DURATION_CHOICES = (
        (NO_DURATION, 'No duration'),
        (PARTIAL_DURATION, 'Partial duration'),
        (FULL_DURATION, 'Full duration'),
        (UNBOUND_DURATION, 'Unbound duration'),
        )
    
    type = models.ForeignKey(MediaType)
    baseStatus = models.ForeignKey(BaseStatus)
    name = models.CharField(max_length=64)
    default = models.BooleanField()
    durationType = models.IntegerField(choices=DURATION_CHOICES, default=NO_DURATION)
    allowRating = models.BooleanField(default=True)
    def __unicode__(self):
        return self.name+" ["+self.baseStatus.name+"]"
    
    def durationEditable(self):
        return self.durationType == Status.PARTIAL_DURATION or self.durationType == Status.UNBOUND_DURATION
    
    def durationMaximum(self):
        return self.durationType == Status.FULL_DURATION
    
    def hasDuration(self):
        return self.durationType != Status.NO_DURATION
    

class Source(models.Model):
    name = models.CharField(max_length=255, unique=True)
    importClass = models.CharField(max_length=255)
    domain = models.CharField(max_length=255, unique=True)
    list_display = models.BooleanField(default=False)
    def __unicode__(self):
        return self.name


class SourceMedia(models.Model):
    source = models.ForeignKey(Source)
    media = models.ForeignKey(Media)
    businessKey = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    def __unicode__(self):
        return "[" + self.source.name + "] "+self.businessKey 


class RatingEvent(models.Model):
    date = models.DateTimeField()
    media = models.ForeignKey(Media)
    rating = models.IntegerField()
    progress = models.IntegerField()
    source = models.ForeignKey(Source, null=True)
    status = models.ForeignKey(Status)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='children')

    def __unicode__(self):
        return u"%s at %s : %s" % (self.media.name, str(self.date), str(self.rating))

    # Return a dictionary of progress ints for each media type
    def typeProgressDict(self):
        progMap = {}
        for red in self.ratingeventprogress_set.all():
            progMap[red.type] = red
        return progMap
    
        
    def getValidProgressRange(self, type):
        #TODO fix this!
        if type.id == self.media.type.id: #intrinsic progress
            return (0, self.media.duration, 0)
        
        # If we don't have a parent (or if the parent type is the media type)
        if not type.parent or type.parent.id == self.media.type.id:
            # Full range
            return (0, self.media.recMediaCount(type), 0)
        
        try:
            mainType = type.parent
            red = self.ratingeventprogress_set.get(type=mainType)
            mainTypeProgress = red.progress
            if mainTypeProgress == 0: # no progress
                return (0, 0, 0) # child can't have progress if parent doesn't have progress
            
            # Partial range based on parent progress
            return self.media.getSubTypeDurationRange(mainType, mainTypeProgress, type)
            
        except Exception: # RatingEventProgress.DoesNotExist:
            # Full range
            return (0, self.media.recMediaCount(type), 0)
    



class RatingImportTask(models.Model):
    RESULT_OK = 0
    RESULT_FAILED = 1
    RESULT_RUNNING = 2
    RESULT_FRESH = 3 #never imported before
    RESULT_CHOICES=(
                    (RESULT_FRESH,'Fresh'),
                    (RESULT_OK,'Ok'),
                    (RESULT_RUNNING,'Running'),
                    (RESULT_FAILED,"Failed"),
                    )
    
    user = models.ForeignKey(User)
    source = models.ForeignKey(Source)
    url = models.CharField(max_length=255)
    lastImportDate = models.DateTimeField(null=True)
    lastResult = models.IntegerField(choices=RESULT_CHOICES,default=RESULT_OK)
    def __unicode__(self):
        return u"%s - %s" % (self.user.username, self.source.name)

