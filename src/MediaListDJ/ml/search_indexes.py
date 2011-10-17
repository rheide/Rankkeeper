from haystack.indexes import *
from haystack import site
from MediaListDJ.ml.models import Media

class MediaIndex(SearchIndex):
    name = CharField(document=True, model_attr='name')
    type = IntegerField(model_attr='type_id')
    
site.register(Media, MediaIndex)
