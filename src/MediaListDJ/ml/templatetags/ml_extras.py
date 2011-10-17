from django import template
from django.utils.safestring import mark_safe
from MediaListDJ.ml.models import *
import re
import urllib

register = template.Library()


class ProgressInfo(object):
    
    def __init__(self,type=None,ratingEvent=None):
        '''
        Constructor
        '''
        self.type = type
        self.d_unit = None
        self.d_step = None
        self.d_range_start = 0
        self.d_range_end = None
        self.d_current = None
        self.d_local_range_offset = 0
    
    def isEmptyRange(self):
        return self.d_range_start == self.d_range_end == 0
    
    def __buildValue(self, i):
        selected = i == self.d_current or (i == self.d_range_start and self.d_current == 0)
        
        value = "<option value=\""+str(i)+"\" " + ("selected=\"selected\"" if selected else "") +">"
        
        if i > self.d_range_start: # First element should have empty name 
            value += str(i)+" "+self.d_unit
            if self.d_range_start > 0 or self.d_local_range_offset > 0: # also note the local index
                localIndex = (i-1) + self.d_local_range_offset
                localIndex -= self.d_range_start
                value += " (" + str(localIndex) + ")"
                
        value += "</option>"
        return value
    
    
    def htmlProgressOptions(self):
        # must return html
        valueList = []
        
        for i in range(self.d_range_start,self.d_range_end,self.d_step):
            valueList.append(self.__buildValue(i))
        
        # Exception: if last item does not correspond to step size (eg. 15 min intervals but movie is 213min)
        #valueList.append("<option value=\""+str(self.d_range_end)+"\" " + ("selected" if self.d_range_end == self.d_current else "") +">"+str(self.d_range_end)+" "+self.d_unit+"</option>")
        valueList.append(self.__buildValue(self.d_range_end))
        
        return mark_safe("\n".join(valueList))
    

@register.filter
def htmlProgressReadOnly(pi): #progressinfo
    value = str(pi.d_current) + " " + pi.d_unit
    
    if pi.d_range_start > 0 or pi.d_local_range_offset > 0: # also note the local index
        localIndex = (pi.d_current-1) + pi.d_local_range_offset
        localIndex -= pi.d_range_start
        value += " (" + str(localIndex) + ")"
    
    return mark_safe(value)


@register.filter
def hash(h, key):
    if key in h:
        return h[key]
    return None


@register.filter
def urlify(value):
    if not value:
        return ""
    
    value = value.lower()
    value = re.sub(' ','_', value)
    value = re.sub('\'','-', value)
    value = urllib.quote(value)
    #value = 
    #value = re.sub('[^a-z0-9-]','_', value)
    
    return value

@register.filter
def sourceLinks(ratingEvent,media=None):
    if not media:
        media = ratingEvent.media
    
    value = ""
    
    if ratingEvent and ratingEvent.source:
        sm = media.sourcemedia_set.get(source=ratingEvent.source)
        value += __srcLink(sm, True)
    
    validSources = media.sourcemedia_set.filter(source__list_display=True)
    for sm in validSources:
        if ratingEvent and ratingEvent.source and sm.source.id == ratingEvent.source.id: 
            continue
        value += __srcLink(sm)
    
    return mark_safe(value)


def __srcLink(sourceMedia, selected=False):
    value = ""
    if selected:
        value += "["
    
    value += "<a href=\"" + sourceMedia.url + "\" target=\"_blank\">"
    
    value += "<img src=\"/static/images/source/" + sourceMedia.source.name.lower() + ".gif\" />"
    
    value += "</a>"
    if selected:
        value += "]"
    return value


@register.filter
def typeRatings(ratingEvent, media=None):
    if ratingEvent:
        return typeRatingsDict(ratingEvent, ratingEvent.media).values()
    else:
        return typeRatingsDict(ratingEvent, media).values()


# Return a dictionary of type|ProgressInfo objects
def typeRatingsDict(re, media):
    typeRatings = {}
    
    if re:
        progDict = re.typeProgressDict()
    else:
        progDict = {}
    
    # intrinsic type:
    if media.type.allowIntrinsicProgress:
        pi = ProgressInfo(type=media.type)
        pi.d_unit = media.type.sub_duration_unit_short
        pi.d_step = media.type.sub_duration_increment
        pi.d_range_start = 0
        pi.d_range_end = media.duration
        
        if media.type in progDict:
            pi.d_current = progDict[media.type].progress
        
        if re and re.status.durationMaximum():
            pi.d_current = pi.d_range_end
        
        typeRatings[media.type] = pi
        
        
    # extrinsic types
    for type in media.type.getDescendants():
        pi = ProgressInfo(type=type)
        pi.d_unit = type.self_duration_unit_short
        pi.d_step = 1 #always 1 when iterating over sub-media
        
        if re:
            (pi.d_range_start, pi.d_range_end, pi.d_local_range_offset) = re.getValidProgressRange(type)
        else: # no rating yet, we must figure out the valid range
            if type.parent == media.type: #immediate child:
                (pi.d_range_start, pi.d_range_end, pi.d_local_range_offset) = media.getRange(type)
            else: # parent progress should be set first, this is not editable
                (pi.d_range_start, pi.d_range_end, pi.d_local_range_offset) = (0,0,0) 
        
        if re and re.status.durationMaximum():
            pi.d_current = pi.d_range_end
        elif type in progDict:
            pi.d_current = progDict[type].progress
        else:
            pi.d_current = 0
         
        typeRatings[type] = pi
    
    return typeRatings


def unurlify(value):
    if not value:
        return ""
    
    value = urllib.unquote(value)
    value = re.sub('-','\'', value)
    value = re.sub('_',' ', value)
    
    return value


@register.filter 
def multiply(value, arg):
    if not value:
        return 0
    return int(value) * int(arg)


@register.filter 
def divide(value, arg):
    if not value:
        return 0
    return float(value) / float(arg)


@register.filter
def ratingWidth(value):
    if not value:
        return 0
    return int(float(value) * 8.0)  #(/ 2) * 16)


@register.filter
def ratingId(value):
    if not value:
        return -1
    return value


@register.filter
def star(objOne, objTwo = -5):
    if isinstance(objOne, RatingEvent):
        return star_maker(objOne.rating, objOne.id)
    return star_maker(objOne, objTwo)


@register.filter
def star_ro(objOne, objTwo = -5):
    if isinstance(objOne, RatingEvent):
        return star_maker_ro(objOne.rating, objOne.id)
    return star_maker_ro(objOne, objTwo)


@register.filter
def media_star(media, ratingEvent):
    if ratingEvent:
        return star_maker(ratingEvent.rating, media.id, "setMediaItemRating")
    else:
        return star_maker(0, media.id, "setMediaItemRating")
        

def star_maker(rating, item_id, methodName=None):
    if not methodName:
        methodName = "setItemRating"
    
    value = "<ul class='star-rating'>" \
            + star_ro_li(rating, item_id) + \
            "<li><a href='javascript:" + methodName + "({0}, 1);'  title='0.5 star out of 5'  class='half-star'      >1</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 2);'  title='1 star out of 5'    class='one-star'       >2</a></li> " \
            "<li><a href='javascript:" + methodName + "({0}, 3);'  title='1.5 star out of 5'  class='onehalf-star'   >3</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 4);'  title='2 stars out of 5'   class='two-stars'      >4</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 5);'  title='2.5 stars out of 5' class='twohalf-stars'  >5</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 6);'  title='3 stars out of 5'   class='three-stars'    >6</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 7);'  title='3.5 stars out of 5' class='threehalf-stars'>7</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 8);'  title='4 stars out of 5'   class='four-stars'     >8</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 9);'  title='4.5 stars out of 5' class='fourhalf-stars' >9</a></li>" \
            "<li><a href='javascript:" + methodName + "({0}, 10);' title='5 stars out of 5'   class='five-stars'     >10</a></li>" \
            "<li id='ml_loader_{0}' style='padding-left: 80px; background:none; width:16px; min-width:16px;'>&nbsp;</li>" \
            "</ul>"
    
    value = value.replace('{0}',str(item_id))
    
    return mark_safe(value)

def star_maker_ro(rating, item_id = -5): # read-only stars, using dummy id per default
    value = "<ul class='star-rating'>" \
            + star_ro_li(rating, item_id) + \
            "</ul>" 
    return mark_safe(value)

def star_ro_li(rating, item_id = -5):
    rw = ratingWidth(rating)
    value = "<li class='current-rating' " \
            "style='width:{0}px;' id='ml_rating_{1}' " \
            "title='{2} stars out of 5'>" \
            "Currently {2} Stars. " \
            "</li>"
    value = value.replace('{0}', str(rw))
    value = value.replace('{1}', str(item_id))
    value = value.replace('{2}', str(float(rating) / 2.0))
    
    return value
