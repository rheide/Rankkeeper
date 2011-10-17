#!/python27/bin/python
import sys, os

sys.path.insert(0, "/.local/lib/python2.7/site-packages")
sys.path.insert(0, "/.local/lib/python2.7/site-packages/flup-1.0.2-py2.7.egg")


os.chdir("/.local/lib/python2.7/site-packages/MediaListDJ")

os.environ['DJANGO_SETTINGS_MODULE'] = "MediaListDJ.settings"


os.system("python -V")


import MediaListDJ.manage
try:
    import MediaListDJ.settings
except ImportError:
    sys.stderr.write("Can't find settings.py!")
    sys.exit(1)
    
from django.core.management import execute_manager
execute_manager(MediaListDJ.settings,argv=['manage.py','update_index'])

