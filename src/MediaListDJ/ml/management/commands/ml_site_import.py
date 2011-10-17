from django.core.management.base import BaseCommand, CommandError
from MediaListDJ.ml.models import *
from MediaListDJ.ml import mediamanager
from MediaListDJ.ml.loaders.webloader import WebLoadError
import sys
import traceback

class Command(BaseCommand):
	args = "None"
	help = "Synchronize all user ratings with the sites they set up for import"
	
	siteLoaders = {}
	
	def handle(self, *args, **options):
		self.__out("Syncing ML users")
		
		#prefetch site loaders
		for src in Source.objects.all():
			self.siteLoaders[src] = mediamanager.getSiteLoader(src)
			if not self.siteLoaders[src]:
				self.__err("Error: loader not found for source: "+src.name)
		
		# Sync our active users, the most recently logged in first
		# (cause he'll be the first to notice that the sync is running slow >_<; )
		for user in User.objects.filter(is_active=True).order_by('-last_login'):
			self.__syncUser(user)
		
		self.__out("Done!")
	
	def __err(self,message,user=None):
		self.__msg(message,self.stderr, user)
		
	def __out(self,message,user=None):
		self.__msg(message,self.stdout, user)
		
	def __msg(self,message,out,user=None):
		if user:
			out.write(mediamanager.nowDateTimeString() + " [" + str(user.id) + "] "  + message + "\n")
		else:
			out.write(mediamanager.nowDateTimeString() + " " + message + "\n")
	
	def __syncUser(self, user):
		for rit in RatingImportTask.objects.filter(user=user):
			self.__syncSource(rit)
			
	def __syncSource(self, rit):
		rit.lastImportDate = mediamanager.nowDateTimeString()
		loader = self.siteLoaders[rit.source]
		if not loader:
			rit.lastResult = RatingImportTask.RESULT_FAILED
		elif not loader.isValidRatingListUrl(rit.url):
			self.__err("invalid url for source "+str(rit.source.id), rit.user)
			rit.lastResult = RatingImportTask.RESULT_FAILED
		else:
			try:
				errors = loader.importFromRatingList(rit.user, rit.url)
				itemCount = loader.last_import_count
				errorCount = 0
				if errors:
					errorCount = len(errors)
								
				self.__out("synchronized "+str(itemCount)+" items, "+str(errorCount)+" errors", rit.user)
				
				if errors:
					for e in errors: # non-fatal errors
						self.__out(str(e), rit.user)
				
				rit.lastResult = RatingImportTask.RESULT_OK
			except WebLoadError, e:
				self.__err("fatal error: "+str(e.value), rit.user)
				rit.lastResult = RatingImportTask.RESULT_FAILED
			except:
				rit.lastResult = RatingImportTask.RESULT_FAILED
				e = sys.exc_info()[1]
				
				url = "-"
				if loader.last_url:
					url = str(loader.last_url)
				
				self.__err("unexpected error: "+str(e)+" in "+url, rit.user)
				
				if sys.exc_info()[2]:
					traceback.print_tb(sys.exc_info()[2])
				
			
		rit.save()
