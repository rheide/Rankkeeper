'''
Created on Sep 16, 2010

@author: Randy
'''
from webloader import WebLoader, WebLoadError
from MediaListDJ.ml.models import *
from MediaListDJ.ml import mediakey, mediamanager
from MediaListDJ import settings
from BeautifulSoup import *
import re
import time
from MediaListDJ.ml.loaders.webloader import MediaTypeNotSupportedError
from urllib2 import URLError

class ImdbLoader(WebLoader):
    '''
    classdocs
    '''
    
    urlPattern = re.compile("(http://)?(www\.)?imdb\.com/title/(?P<key>tt[0-9]+)/?", re.IGNORECASE)
    titlePattern = re.compile("(?P<title>[^\(]*)(\((?P<version>I+)\)\s+)?\([a-zA-z ]*(?P<year>[0-9]{4}).*\)", re.IGNORECASE)
    durationPattern = re.compile("(?P<length>[0-9]+) min",re.IGNORECASE)
    listPattern = re.compile("http://www.imdb.com/mymovies/list\?l=[0-9]+$", re.IGNORECASE)
    
    debugDir = "K:\\Workspace\\MLWorkspace\\imdb\\"
    
    
    def __init__(self):
        self.last_url = None
        self.last_import_count = 0
    
        
    def getSourceBusinessKey(self, url):
        # use the regex specified in the source
                
        match = self.urlPattern.match(url)
        if not match:
            raise WebLoadError("Invalid url")
        
        key = match.group('key')
        
        return key
    
    
    def importFromRatingList(self, user, summary_url):
        
        self.last_import_count = 0
        
        allRatings = {}
        
        offset = 0
        hasRatings = True
        while (hasRatings):
            url = summary_url + "&o=" + str(offset)
            
            self.last_url = url #for debug
            
            html = mediakey.getUrl(url)
            
            if settings.IMDB_DEBUG:
                tmpFile = self.debugDir + "IMDb_list_" + str(user.id) + "_" + str(offset) + ".html"
                f = open(tmpFile, 'w')
                f.write(html)
                f.close()
            
            soup = BeautifulSoup(html)
            ratings = self.__buildRatingMap(soup)
            oldSize = len(allRatings)
            allRatings.update(ratings)
            newSize = len(allRatings)
            
            # If same ratings are added over and over, size does not increase
            # If no ratings are found (eg. on an empty page) the size does not increase
            hasRatings = oldSize < newSize
            print "Page increment: "+str(newSize-oldSize)+" ("+str(len(allRatings))+")"
            offset += newSize - oldSize #(== # of ratings on page)
        
        # Now we must import each rating
        errors = []
        for key, (rating,status,date) in allRatings.items():
            try:
                self.last_import_count += 1
                self.__importRating(user, key, rating, status, date)
            except WebLoadError, e:
                errors.append(str(key)+" - "+str(e.value))
            
        if len(errors) > 0:
            return errors
        else:
            return None
    
    
    def __importRating(self, user, key, rating, status, date):
        # Import ratings to database, check if previous ratings exists
        # and maintain a proper event history of everything
        
        # First, resolve the media
        url = self.getUrl(key)
        self.last_url = url #for debug
        try:
            sourceMedia = mediamanager.addSourceMedia(url)
        except MediaTypeNotSupportedError:
            #print "Unsupported media type for url: "+url
            return # Nothing to do yet
        
        #print "Source media " + key + " - " + sourceMedia.media.name
        
        # Then find existing ratings for our media type
        # (IMDB only supports the simple kind of rating)
        ratings = RatingEvent.objects.filter(user=user, 
                                             source=sourceMedia.source,
                                             media=sourceMedia.media,
                                             complex=False).order_by('-date','-id')
        
        addNewRating = True
        if len(ratings) > 0 and ratings[0].rating == rating:
            addNewRating = False # don't add new rating if previous rating already exists
        
        # Special rules for imdb: we ignore statuses (since IMDb doesn't have them)
        # and we only check if the rating changed. duration is ignored completely
        if addNewRating:
            re = RatingEvent()
            re.user = user
            re.media = sourceMedia.media
            re.source = sourceMedia.source
            re.rating = rating
            re.date = mediamanager.nowDateString()
            re.complex = False
            # Always use 'watched' for the status, as IMDB does not offer any choice
            re.status = Status.objects.get(type=sourceMedia.media.type, name="Watched")
            re.save()
            # Get mediamanager to update duration:
            mediamanager.updateStatus(re, re.status.id)
            
        
    
    def isValidRatingListUrl(self, summary_url):
        match = self.listPattern.match(summary_url)
        return True if match else False
    
    
    def loadMedia(self, url):
        try:
            html = mediakey.getUrl(url)
        except URLError, e:
            raise WebLoadError("Http error getting "+url+" - "+str(e))
        
        if settings.IMDB_DEBUG:
            tmpFile = self.debugDir + self.getSourceBusinessKey(url) +".html"
            f = open(tmpFile, 'w')
            f.write(html)
            f.close()
        
        # I love soup
        soup = BeautifulSoup(html)
        
        media = Media()
        media.mediainfo = MediaInfo(media=media)
        
        self.__loadMediaType(soup, media, url)
        self.__loadTitle(soup, media, url)
        
        if media.type.name == 'Movies':
            media = self.__loadMovie(soup, media, url)
        elif media.type.name == 'TV Shows':
            media = self.__loadTvShow(soup,media,url)
        elif media.type.name == 'TV Show Episodes':
            media = self.__loadTvShowEpisode(soup,media,url)
        
        return media
    
    
    def __loadMovie(self, soup, media, url):
        if not media.mediainfo.date:
            raise WebLoadError("Could not find year in movie title")
        self.__loadDirectors(soup, media, url)
        self.__loadDuration(soup, media, url)
        
        if len(media.mediainfo.author) == 0:
            # For the logic behind this check, see __loadTvShow
            media.businessKey = "IMDB#"+self.getSourceBusinessKey(url)
            media.name += " @ IMDB"
            #raise WebLoadError("Could not read directors - "+url)
        else:
            media.businessKey = mediakey.generateMovieKey(media)
            
        try:
            dbMedia = Media.objects.get(type=media.type,businessKey=media.businessKey)
            # Update missing/outdated information
            
            # TODO
            return dbMedia
        except Media.DoesNotExist: # no worries
            media.save()
            media.mediainfo.media = media
            media.mediainfo.save()
            return media
    
    def __loadTvShow(self, soup, media, url):
        if not media.mediainfo.date:
            raise WebLoadError("Could not find year in tv show title")
        
        self.__loadCreators(soup, media, url)
        if len(media.mediainfo.author) == 0:
            # This is a serious problem, because we cannot generate a unique business key
            # for this item, meaning that we cannot cross-link it with the same entry
            # in other websites. 
            # We circumvent this problem by adding an IMDB-specific businesskey
            # and adding the imdb keyword in the title, so that this entry can later
            # be merged manually with the same entry from another site
            media.businessKey = "IMDB#" + self.getSourceBusinessKey(url)
            media.name += " @ IMDB"
            #raise WebLoadError("Could not read creators - "+url)
        else:
            media.businessKey = mediakey.generateTvSeriesKey(media)
        
        
        try:
            dbMedia = Media.objects.get(type=media.type, businessKey=media.businessKey)
            media = dbMedia # Don't alter any properties (name,date) of the show if it already exists
        except Media.DoesNotExist: # No worries
            media.save()
            media.mediainfo.media = media
            media.mediainfo.save()
        
        #Load child items:
        self.__loadSeasons(soup, media, url)
        return media
    
    
    def __loadTvShowEpisode(self, soup, media, url):
        # This is very troublesome
        # We must first load the whole tv show, then the season, and only then the episode
        # for now, let's just see if we can find the parent and give up if we can't
        epInfo = self.__getTvShowEpisodeInfo(soup, url)
        
        parentMediaKey = re.search("tt[0-9]+",epInfo['parent'],re.IGNORECASE).group(0)
        
        try:
            sm_show = SourceMedia.objects.get(businessKey=parentMediaKey,source=self.getSource())
            m_show = sm_show.media
        except SourceMedia.DoesNotExist:
            # We should load the tv show first, (slow)
            parentUrl = self.getUrl(parentMediaKey)
            m_show = self.loadMedia(parentUrl)
            if not m_show or not m_show.mediainfo:
                raise WebLoadError("[09] Cannot parse url: "+parentUrl) 
            m_show.save()
            m_show.mediainfo.media = m_show
            m_show.mediainfo.save()
            
            #also add source media!
            sm_show = SourceMedia(source=self.getSource())
            sm_show.businessKey=parentMediaKey
            sm_show.media=m_show
            sm_show.url = parentUrl
            sm_show.save()
            
        
        # Now find the season (or add it)
        seasonIndex = epInfo['season']
        seasonKey = mediakey.generateTvSeriesSeasonKey(m_show, seasonIndex)
        try:
            seasonType = MediaType.objects.get(name="TV Show Seasons")
            m_season = Media.objects.get(parent=m_show, businessKey=seasonKey)
        except MediaType.DoesNotExist:
            raise WebLoadError("Fatal error - media type not found")
        except Media.DoesNotExist: # Create a new season object
            m_season = Media(parent=m_show, type=seasonType,
                             name = unicode(m_show.name+" season "+str(seasonIndex)),
                             businessKey=seasonKey, order=seasonIndex)
            m_season.mediainfo = MediaInfo(author=unicode(m_show.mediainfo.author),
                                           date=None)
            m_season.save()
            m_season.mediainfo.media = m_season
            m_season.mediainfo.save()
           
        # Load the last bits of info for our media
        media.parent = m_season
        media.order = epInfo['episode']
        media.businessKey = mediakey.generateTvSeriesEpisodeKey(m_season, media.order)
        
        # (We don't need directors for the business key of a child item)
        self.__loadDirectors(soup, media, url)
        self.__loadDuration(soup, media, url)
        
        # now we can compare with the database object, if it exists
        try:
            dbMedia = Media.objects.get(type=media.type,businessKey=media.businessKey)
            # Update items only if necessary
            if dbMedia.name.lower() == "episode "+str(media.order):
                dbMedia.name = unicode(media.name)
            if int(media.duration) > int(dbMedia.duration): 
                dbMedia.duration = media.duration
            
            if not dbMedia.mediainfo.author or len(dbMedia.mediainfo.author) == 0:
                dbMedia.mediainfo.author = unicode(media.mediainfo.author)
            if not dbMedia.mediainfo.date:
                dbMedia.mediainfo.date = media.mediainfo.date
            
            dbMedia.save()
            dbMedia.mediainfo.save()
            return dbMedia
        
        except Media.DoesNotExist: # No worries
            media.save()
            media.mediainfo.media = media
            media.mediainfo.save()
            return media
    
    
    def __getTvShowEpisodeInfo(self, soup, url):
        infoTags = soup.findAll("h5")
        data = {}
        for tag in infoTags:
            
            if re.search("tv series", str(tag), re.IGNORECASE):
                ic = tag.parent.find("div",{"class":"info-content"})
                a = ic.find("a")
                
                data['parent'] = str(a['href'])
            elif re.search("original air date", str(tag), re.IGNORECASE):
                ic = tag.parent.find("div",{"class":"info-content"})
                
                datePattern = re.compile("(?P<day>[0-9]{1,2} )?(?P<month>[a-z]+ )?(?P<year>[0-9]{4})", re.IGNORECASE)
                seasonPattern = re.compile("season ([0-9]+)", re.IGNORECASE)
                episodePattern = re.compile("episode ([0-9]+)", re.IGNORECASE)
                
                text = ic.contents[0]
                dateMatch = datePattern.search(text)
                if dateMatch:
                    year = dateMatch.group('year').strip()
                    
                    if dateMatch.group('month'):
                        month = dateMatch.group('month').strip()
                    else:
                        month = "january"
                    
                    if dateMatch.group('day'):
                        day = dateMatch.group('day').strip()
                    else:
                        day = "1"
                    
                    date = str(day) + " " + str(month) + " " + str(year)      
                    
                    try:
                        realDate = time.strptime(date,"%d %B %Y")
                        date = mediamanager.dateToString(realDate)
                    except TypeError:
                        raise WebLoadError("Strange date encountered: "+str(date)+" @ "+url)               
                else:
                    date = None 
                    #it's not a problem if a tv show episode has no date
                    #because the business key does not use the date
                
                seasonMatch = seasonPattern.search(text)
                if seasonMatch:
                    season = seasonMatch.group(1)
                else:
                    season = 0
                
                episodeMatch = episodePattern.search(text)
                if episodeMatch:
                    episode = episodeMatch.group(1)
                else: #find total episode number!
                    epNavDiv = soup.find("div",{"id":"tn15epnav"})
                    epRegex = re.compile("([0-9]+) of ", re.IGNORECASE)
                    epMatch= epRegex.search(str(epNavDiv))
                    if epMatch:
                        episode = epMatch.group(1)
                    else:
                        # big fail
                        raise WebLoadError("Can't find season/episode info for url: "+url)
                        episode = "Unknown episode"
                
                data['date'] = date
                data['season'] = season
                data['episode'] = episode
                
        
        return data
    
    
    def __loadSeasons(self, soup, media, url):    
        #seasonTags = soup.findAll("a", {"href":re.compile("episodes#season-[0-9]+")})
        #media.mediainfo.duration = len(seasonTags) #length measured in seasons
        if url[-1] != '/':
            url += '/'
        html = mediakey.getUrl(url + "episodes")
        
        if settings.IMDB_DEBUG:
            tmpFile = self.debugDir + self.getSourceBusinessKey(url) +"_eps.html"
            f = open(tmpFile, 'w')
            f.write(html)
            f.close()
        
        soup = BeautifulSoup(html)
        
        # Find the max number of eps for each season
        pattern = re.compile("Season ([0-9+]), Episode ([0-9]+)",re.IGNORECASE)
        tags = soup.findAll("h3",text=pattern)
        seasonEps = {}
        for tag in tags:
            match = pattern.search(str(tag))
            season = int(match.group(1))
            episode = int(match.group(2))
            if not season in seasonEps:
                seasonEps[season] = 0
            elif episode > seasonEps[season]:
                seasonEps[season] = episode
                #print tag
        
        # Create dummy eps - we are not going to add SourceMedia
        # So that the source can be added by someone else
        seasonType = MediaType.objects.get(name='TV Show Seasons')
        episodeType = MediaType.objects.get(name='TV Show Episodes')
        
        for seasonIndex in seasonEps:
            season = Media(name=media.name+" season "+str(seasonIndex), type=seasonType, 
                           businessKey=mediakey.generateTvSeriesSeasonKey(media, seasonIndex),
                           parent=media, order=seasonIndex)
            season.mediainfo = MediaInfo(author=None,date=None,location=None)
            
            try:
                dbSeason = Media.objects.get(type=seasonType,businessKey=season.businessKey)
                # We don't have any information about the season at this point, 
                # (except the number of episodes which we will handle later),
                # so we just use the existing db media without modifying/updating it
                season = dbSeason
            except Media.DoesNotExist: # no worries
                season.save()
                season.mediainfo.media = season
                season.mediainfo.save()
            
            
            episodeCount = seasonEps[seasonIndex]
            for epix in range(1,episodeCount+1):
                episode = Media(name="Episode "+str(epix), type=episodeType,
                                businessKey=mediakey.generateTvSeriesEpisodeKey(season, epix),
                                parent=season, order=epix)
                # Check if the episode exists so we can update it if necessary
                try:
                    dbEpisode = Media.objects.get(type=episodeType, businessKey=episode.businessKey)
                    # We have no episode info at this point, so the only thing we find out 
                    # by looking up the ep in the db is that we don't have to save it
                except Media.DoesNotExist: # no worries
                    episode.mediainfo = MediaInfo(author=None,date=None,location=None)
                    episode.save()
                    episode.mediainfo.media = episode
                    episode.mediainfo.save()
                    # Note that we don't add source media for the episodes at this point,
                    # as that would take a lot of effort to find out and would increase
                    # the database size needlessly
       
    
    def __loadMediaType(self, soup, media, url):
        ogTypeTag = soup.findAll("meta", {"property":"og:type"})[0]
        mediaType = ogTypeTag['content']
        if mediaType == 'tv_show':
            infoTags = soup.findAll("h5")
            for tag in infoTags:
                if re.search("tv series", str(tag), re.IGNORECASE):
                    # Only the single episodes hold a link to their parent tv series
                    media.type = MediaType.objects.get(name="TV Show Episodes")
                    return
            # If no link to parent tv series was found, this must be the parent
            media.type = MediaType.objects.get(name="TV Shows")
        elif mediaType == 'movie':
            media.type = MediaType.objects.get(name="Movies")
        else:
            raise MediaTypeNotSupportedError("Unknown media type: "+str(mediaType)+" - "+url)
   

    def getUrl(self, businessKey):
        if not businessKey:
            return None
        return "http://www.imdb.com/title/" + businessKey
        
        
    def __loadDuration(self, soup, media, url):
        infoDivs = soup.findAll("div", {"class":"info"})
        maxDuration = 0
        for id in infoDivs:
            text = id.find(text=re.compile("runtime",re.IGNORECASE))
            if text:
                infoContent = id.find("div", {"class":"info-content"})
                duration = infoContent.contents[0]
                
                # find the longest duration (some people will ask at this point: "WHY?!?!?) -> because it's the easiest solution"
                for duration in self.durationPattern.findall(duration):
                    #print "Duration: "+str(duration)
                    if duration > maxDuration:
                        maxDuration = duration
                #print "Max duration: "+str(maxDuration)
        
        media.duration = maxDuration
            

    def __loadTitle(self, soup, media, url):
        ogTitleTag = soup.findAll("meta", {"property":"og:title"})[0]
        item = ogTitleTag['content']
        
        # video games are marked as movies too - check for video game!
        litem = item.lower()
        if litem.count('(vg)') > 0 or litem.count('(video game') > 0:
            raise MediaTypeNotSupportedError("Video games are not supported yet")
            
        
        match = self.titlePattern.search(item)
        if match: #found title and year
            media.name = unicode(match.group("title"))
            media.mediainfo.date = match.group("year") + "-01-01"
        else:
            # we didn't find the date, but that's not a problem for tv show episodes
            media.name = unicode(str(item))
         
    
    def __loadDirectors(self, soup, media, url):
        divTags = soup.findAll("div", {"id":"director-info"})
        directors = []
        for tag in divTags:
            aTags = tag.findAll("a")
            for atag in aTags:
                for content in atag.contents:
                    directors.append(content)
        directors.sort()
        
        # Error handling for missing director is done elsewhere
        media.mediainfo.author = unicode(",".join(directors))
    
    
    def __loadCreators(self, soup, media, url):
        hTags = soup.findAll("h5")
        creators = []
        crPattern = re.compile("creator",re.IGNORECASE) 
        for tag in hTags:
            if crPattern.search(tag.contents[0]):
                aTags = tag.parent.find("div",{"class":"info-content"}).findAll("a")
                for atag in aTags:
                    for content in atag.contents:
                        content = content.strip()
                        if content.lower() == 'see more': continue
                        creators.append(content)
        creators.sort()
        
        # The check if creators exist or not will be done elsewhere
        media.mediainfo.author = unicode(",".join(creators))
    
    
    def __getParentTag(self, parentTagName, searchTag):
        parent = searchTag
        while parent and parent.name != parentTagName:
            parent = parent.parent
            return parent
    
    
    def __buildRatingMap(self, soup):
        ratings = {}
        tdTags = soup.findAll("td", {"class":"standard"})
        
        bkPattern = re.compile(".*(?P<key>tt[0-9]+).*", re.IGNORECASE)
        
        for tag in tdTags:
            aTags = tag.findAll("a", {"href":re.compile("title/tt[0-9]+",re.IGNORECASE)})
            for aTag in aTags:
               
                match = bkPattern.match(str(aTag['href']))
                title = match.group('key')
               
                rating = self.__findRating(aTag)
                
                status = "Watched" # Default
                date = None #No idea
                ratings[title] = (rating,status,date)
                
        return ratings
    
    
    def __findRating(self, aTag):
        mytd = self.__getParentTag('td',aTag)
        row = self.__getParentTag('tr',mytd)
        tds = row.findAll("td")
        for td in tds:
            if td == mytd:
                continue
            tmpRatings = td.findAll(text=re.compile("[0-9]{1,2}"))
            if len(tmpRatings) > 0:
                return int(tmpRatings[0])
    