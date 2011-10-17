#!/home/colorfv2/python27/bin/python
import sys, os, datetime

db = "rankkeeper"
user = "rankkeeper"
pw = "rankkeeper"

target = "/mldb/"

target_file = target + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".sql.gz"

cmd = "mysqldump --single-transaction -u "+user+" --password=\""+pw+"\" "+db+" | gzip -9 -c >"+target_file

#print cmd

res = os.system(cmd)
if res != 0:
    print "Error occurred in MySQLDUMP!"
    sys.exit(1)

size = os.path.getsize(target_file)
if size < 2048:
    print "Error occurred in backup: file not written correctly: "+target_file
    sys.exit(1)

print "Done! - target size: "+str(size)
sys.exit(0)



