#!/home/colorfv2/python27/bin/python
import sys, os

sys.path.insert(0, "/home/colorfv2/.local/lib/python2.7/site-packages")
sys.path.insert(0, "/home/colorfv2/.local/lib/python2.7/site-packages/flup-1.0.2-py2.7.egg")


os.chdir("/home/colorfv2/.local/lib/python2.7/site-packages/MediaListDJ")

os.environ['DJANGO_SETTINGS_MODULE'] = "MediaListDJ.settings"

from django.core.servers.fastcgi import runfastcgi
runfastcgi(method="threaded", daemonize="false")
