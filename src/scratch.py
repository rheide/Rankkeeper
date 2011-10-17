import re                
from BeautifulSoup import *
import datetime

#htmlFile = "K:\\Workspace\\MLWorkspace\\imdb\\tt0966897.html"
htmlFile = "K:\\Workspace\\MLWorkspace\\imdb\\tt0929425.html"

print "Start: "+str(datetime.datetime.now())

f = open(htmlFile, 'r')
html = f.read()
f.close()

print "HtmlRead: "+str(datetime.datetime.now())

soup = BeautifulSoup(html)

print "SoupBuilt: "+str(datetime.datetime.now())

divTags = soup.findAll("div", {"id":"director-info"})

directors = []
for tag in divTags:
    aTags = tag.findAll("a")
    for atag in aTags:
        for content in atag.contents:
            directors.append(content)

directors.sort()
print "Directors: "+(",".join(directors))

ogTypeTag = soup.findAll("meta", {"property":"og:type"})[0]
mediaType = ogTypeTag['content']

print "Media type: "+mediaType

ogTitleTag = soup.findAll("meta", {"property":"og:title"})[0]
mediaTitle = ogTitleTag['content']

print "Media title: "+mediaTitle

#pattern = re.compile("(?P<title>[^\(]*)(\((?P<version>I+)\))?\s?(\(?P<year>[0-9]{4}\))")
pattern = re.compile("(?P<title>[^\(]*)(\((?P<version>I+)\)\s+)?\((?P<year>[0-9]{4})\)") #\s?(\(?P<year>[0-9]{4}\))")

#match = pattern.search("House MD Test (I) (2001) hfdhdf") #
match = pattern.search(mediaTitle) #

groups = match.groupdict()
name = groups["title"]
version = groups["version"] if "version" in groups else ""
year = groups["year"] if "year" in groups else ""

if version is None: version = ""
if year is None: year = ""


print "Name: "+name
print "Version: "+version
print "Year: "+year



# Runtime
infoDivs = soup.findAll("div", {"class":"info"})
durationPattern = re.compile("(?P<length>[0-9]+) min",re.IGNORECASE)
maxDuration = 0
for id in infoDivs:
    text = id.find(text=re.compile("runtime",re.IGNORECASE))
    if text:
        infoContent = id.find("div", {"class":"info-content"})
        duration = infoContent.contents[0]
        
        # find the longest duration (some people will ask at this point: "WHY?!?!?) -> because it's the easiest solution"
        for duration in durationPattern.findall(duration):
            print "Duration: "+str(duration)
            if duration > maxDuration:
                maxDuration = duration
        
        print "Max duration: "+str(maxDuration)


seasonTags = soup.findAll("a", {"href":re.compile("episodes#season-[0-9]+")})
for aTag in seasonTags:
    season = aTag.contents[0]
    #print season

     
infoTags = soup.findAll("h5")
for tag in infoTags:
    #print "Tag: "+str(tag)
    if re.search("tv series", str(tag), re.IGNORECASE):
        ic = tag.parent.find("div",{"class":"info-content"})
        a = ic.find("a")
        print "Parent: " + str(a['href'])
        print "This is a tv episode: "+tag.contents[0]
    elif re.search("original air date", str(tag), re.IGNORECASE):
        ic = tag.parent.find("div",{"class":"info-content"})
        
        datePattern = re.compile("[0-9]{1,2} [a-z]+ [0-9]{4}", re.IGNORECASE)
        seasonPattern = re.compile("season [0-9]+", re.IGNORECASE)
        episodePattern = re.compile("episode [0-9]+", re.IGNORECASE)
        
        text = ic.contents[0]
        date = datePattern.search(text).group(0)
        season = seasonPattern.search(text).group(0)
        episode = episodePattern.search(text).group(0)
        
        print "AirDate: "+date+" - "+season+" - "+episode
        
        
print str(datetime.datetime.now())
