from django import forms
from haystack.forms import SearchForm, FacetedSearchForm, ModelSearchForm
from haystack.query import SearchQuerySet
from django.forms.models import ModelChoiceField
from MediaListDJ.ml.models import MediaType

class MediaSearchForm(SearchForm):
    
    t = ModelChoiceField(queryset=MediaType.objects.filter(active=True), required=False)
    
    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(MediaSearchForm, self).search()
        
        # Then filter by media type
        if self.cleaned_data['t']:
            try:
                type = MediaType.objects.get(name=self.cleaned_data['t'])
                sqs = sqs.filter(type=type.id)
                sqs.type = type.id
            except MediaType.DoesNotExist:
                pass # Meh
        
        return sqs
