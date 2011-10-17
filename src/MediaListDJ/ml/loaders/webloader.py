'''
Created on Sep 16, 2010

@author: Randy
'''

class WebLoader(object):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''
        self.source = None
        self.last_url = None
        self.last_import_count = 0
        
        
    def getSource(self): 
        return self.source
    
    def setSource(self, source):
        self.source = source
    
    def getSourceBusinessKey(self, url):
        return "-"
    
    # Returns a Media object that has a SourceMedia object or None if failed
    # Implementations of this function should save new media to the database (and parent/child media as well if necessary)
    def loadMedia(self, url):
        raise WebLoadError("Cannot load media from url")
    
    def getUrl(self, businessKey):
        raise WebLoadError("Cannot build url")
    
    # Can access the db and save things, using special business logic unique to each site
    # should return a list of error messages if any part of the import failed
    def importFromRatingList(self, user, summary_url):
        raise WebLoadError("Cannot load rating list")
    
    def isValidRatingListUrl(self, summary_url):
        raise WebLoadError("Cannot load rating list")


class WebLoadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class UnknownSourceError(WebLoadError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class MediaTypeNotSupportedError(WebLoadError):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
