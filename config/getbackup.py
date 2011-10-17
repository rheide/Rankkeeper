import sys,os, re
import datetime

from ftplib import FTP

regex = re.compile("([0-9]{4}.[0-9]{1,2}.[0-9]{1,2})",re.IGNORECASE)

lastFile = None
lastDate = None

class Meh(object):
	def __init__(self):
		self.lastDate = None
		self.lastFile = None
	
	def handle_line(self,line):
		match = regex.search(line)
		if match:
			print "Match: " + match.group(1)
			date = datetime.datetime.strptime(match.group(1),"%Y-%m-%d")
			print "Date: "+str(date.toordinal())
			if not self.lastFile:
				self.lastDate = date
				self.lastFile = line
			elif date > self.lastDate:
				self.lastDate = date
				self.lastFile = line

		print "Line: " + str(line)


print "Retrieving backup"
ftp_host = ""
ftp_user = ""
ftp_pass = ""
ftp_port = 21

local_path = "N:\\rankkeeper\\Db\\"

meh = Meh()

ftp = FTP(ftp_host, ftp_user, ftp_pass)

lines = ftp.retrlines('NLST', meh.handle_line).split("\n")

if meh.lastFile:
	target_file = local_path + meh.lastFile
	print "Target: "+target_file
	if os.path.exists(target_file):
		print "Already copied: "+meh.lastFile
		sys.exit(0)
	else:
		# copy
		tar = open(target_file, 'wb')
		ftp.retrbinary("RETR " + meh.lastFile, tar.write, 1024)
		tar.close()
		print "Done"
	sys.exit(0)
else:
	print "No backup found!"
	sys.exit(1)
