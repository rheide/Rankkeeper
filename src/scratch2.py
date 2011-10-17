import re
               
from BeautifulSoup import *

class Loader:
    
    def getParentTag(self, parentTagName, searchTag):
        parent = searchTag
        while parent and parent.name != parentTagName:
            parent = parent.parent
            return parent
        
    def buildRatingMap(self, soup):
        ratings = {}
        tdTags = soup.findAll("td", {"class":"standard"})
        
        bkPattern = re.compile(".*(?P<key>tt[0-9]+).*", re.IGNORECASE)
        
        for tag in tdTags:
            aTags = tag.findAll("a", {"href":re.compile("title/tt[0-9]+",re.IGNORECASE)})
            for aTag in aTags:
                #print aTag['href']
                match = bkPattern.match(str(aTag['href']))
                title = match.group('key')
                #print "Title: "+str(title)
                rating = self.findRating(aTag)
                #print "Rating: "+str(rating)
                status = "Watched" # Default
                date = None #No idea
                ratings[title] = (rating,status,date)
                
        return ratings
    
    def findRating(self, aTag):
        mytd = self.getParentTag('td',aTag)
        row = self.getParentTag('tr',mytd)
        print row
        tds = row.findAll("td")
        for td in tds:
            if td == mytd:
                continue
            tmpRatings = td.findAll(text=re.compile("[0-9]{1,2}"))
            if len(tmpRatings) > 0:
                return int(tmpRatings[0])
            
            

loader = Loader()

htmlFile = "K:\\Workspace\\MLWorkspace\\imdb\\imdb_list_2_0.html"
f = open(htmlFile, 'r')
html = f.read()
f.close()

soup = BeautifulSoup(html)

map = loader.buildRatingMap(soup)

print ""
print map
            
        #ratings = row.td[2]
        
        #print ratings
    



