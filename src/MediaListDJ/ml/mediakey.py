import re
import urllib2
from MediaListDJ.ml.models import *
from urllib2 import URLError
from MediaListDJ.ml.loaders.webloader import WebLoadError

url_timeout = 30 #seconds
url_retry_count = 3 #times

def generateMovieKey(media):
	key = []
	key.append(media.name)
	if media.mediainfo.author and len(media.mediainfo.author) > 0:
		key.append(media.mediainfo.author)
	key.append(str(media.mediainfo.date))
	
	return buildKey(key) 


def generateTvSeriesKey(media):
	return generateMovieKey(media) # same


def generateTvSeriesSeasonKey(tvSeriesMedia,seasonIndex):
	key = []
	key.append(generateTvSeriesKey(tvSeriesMedia))
	key.append("_")
	key.append(str(seasonIndex))
	return buildKey(key) # same


def generateTvSeriesEpisodeKey(tvSeriesSeasonMedia, episodeIndex):
	key = []
	key.append(generateTvSeriesSeasonKey(tvSeriesSeasonMedia.parent, tvSeriesSeasonMedia.order))
	key.append("_")
	key.append(str(episodeIndex))
	return buildKey(key) # same



def buildKey(itemList):
	key = "".join(itemList)
	return re.sub(r'\W+', '', key).lower()

def getUrl(url):
	tryCount = 1
	lastError = None
	
	while tryCount < url_retry_count:
		try:
			request = urllib2.Request(url)
			request.add_header('User-Agent', 'MediaList/0.1')
			opener = urllib2.build_opener()
			f = opener.open(request, None, url_timeout)
			data = f.read()
			f.close()
			return data
		except URLError, e:
			lastError = WebLoadError("Http error getting "+url+" - "+str(e))
			print "Warning: try "+str(tryCount)+"/"+str(url_retry_count)+" for url "+url+" failed: "+str(e)
		tryCount += 1
		
	raise lastError
