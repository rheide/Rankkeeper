import re                
from BeautifulSoup import *

htmlFile = "K:\\Workspace\\MLWorkspace\\imdb\\episodes.htm"
f = open(htmlFile, 'r')
html = f.read()
f.close()

soup = BeautifulSoup(html)

print "Finding"
pattern = re.compile("Season ([0-9+]), Episode ([0-9]+)",re.IGNORECASE)
tags = soup.findAll("h3",text=pattern)

seasonEps = {}

print "Iterating"

for tag in tags:
    match = pattern.search(str(tag))
    season = int(match.group(1))
    episode = int(match.group(2))
    
    if not season in seasonEps:
        seasonEps[season] = 0
    elif episode > seasonEps[season]:
        seasonEps[season] = episode
    print tag
    
print "Eps: "+str(seasonEps)

for season in seasonEps:
    print "Season: "+str(seasonEps[season])
