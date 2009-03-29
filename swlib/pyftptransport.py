import ftplib
import Sword
import cStringIO

def removeTrailingSlash(buf):
	if buf[-1] in '\\/':
		buf = buf[:-1]
	
	return buf

class StatusReporter(object):
	def preStatus(self, totalBytes, completedBytes, message):
		pass

	def statusUpdate(self, dtTotal, dlNow):
		pass

if not hasattr(Sword, "FTPTransport"):
	# we may not have built this with FTP support,
	# as this just takes up space at the moment.
	Sword.FTPTransport = object

class PyFTPTransport(Sword.FTPTransport):
	def __init__(self, host, statusReporter=None):
		super(PyFTPTransport, self).__init__(host, statusReporter)
		self.host = host
		print "HOST", self.host
		self.passive = True
		self.term = False
		self.statusReporter = statusReporter
		self._ftp = None
	
	@property
	def ftp(self):
		if self._ftp is None:
			self._ftp = ftplib.FTP(self.host)
			self._ftp.login()

		return self._ftp
	
	def getURL(self, destPath, sourceURL, destBuf=None):
		host_string = "ftp://" + self.host
		if sourceURL.startswith(host_string):
			sourceURL = sourceURL[len(host_string):]

		self.ftp.set_pasv(self.passive)

		#size = self.ftp.size(sourceURL)
		print "sourceURL", sourceURL
		if destBuf is not None:
			print "Using destBuf"
			f = cStringIO.StringIO()
		else:
			print "Using destPath", destPath
			f = open(destPath, "wb")



		directory_listing = sourceURL[-1] in "\\/"
		
				

		if directory_listing:
			def callback(data):
				f.write(data + "\n")
		
			cmd = "LIST %s" % sourceURL
			self.ftp.retrlines(cmd, callback)
			
		else:
			cmd = "RETR %s" % sourceURL
			self.ftp.retrbinary(cmd, f.write)
			


		if destBuf is not None:
			destBuf.set(f.getvalue())
		else:
			f.close()

		return 0

		
	
#	def copyDirectory(self, urlPrefix, dir, dest, suffix):
#		retVal = 0
#		
#		url = urlPrefix + dir
#		url = removeTrailingSlash(url)
#		url += '/'
#		
#		SWLog.getSystemLog().logWarning("FTPCopy: getting dir %s\n", url);
#		dirList = self.getDirList(url);
#	
#		if (!dirList.size()) {
#			SWLog.getSystemLog().logWarning("FTPCopy: failed to read dir %s\n", url);
#			return -1;
#		}
#					
#		totalBytes = 0
#		for i in dirList:
#			(i = 0; i < dirList.size(); i++)
#			totalBytes += dirList[i].size;
#		long completedBytes = 0;
#		for (i = 0; i < dirList.size(); i++) {
#			struct DirEntry &dirEntry = dirList[i];
#			SWBuf buffer = (SWBuf)dest;
#			removeTrailingSlash(buffer);
#			buffer += "/";
#			buffer += dirEntry.name;
#			if (!strcmp(&buffer.c_str()[buffer.length()-strlen(suffix)], suffix)) {
#				SWBuf buffer2 = "Downloading (";
#				buffer2.appendFormatted("%d", i+1);
#				buffer2 += " of ";
#				buffer2.appendFormatted("%d", dirList.size());
#				buffer2 += "): ";
#				buffer2 += dirEntry.name;
#				if (statusReporter)
#					statusReporter.preStatus(totalBytes, completedBytes, buffer2.c_str());
#				FileMgr::createParent(buffer.c_str());	// make sure parent directory exists
#				SWTRY {
#					SWBuf url = (SWBuf)urlPrefix + (SWBuf)dir;
#					removeTrailingSlash(url);
#					url += "/";
#					url += dirEntry.name; //dont forget the final slash
#					if (!dirEntry.isDirectory) {
#						if (getURL(buffer.c_str(), url.c_str())) {
#							SWLog.getSystemLog().logWarning("FTPCopy: failed to get file %s\n", url.c_str());
#							return -2;
#						}
#						completedBytes += dirEntry.size;
#					}
#					else {
#						SWBuf subdir = (SWBuf)dir;
#						removeTrailingSlash(subdir);
#						subdir += (SWBuf)"/" + dirEntry.name;
#						if (copyDirectory(urlPrefix, subdir, buffer.c_str(), suffix)) {
#							SWLog.getSystemLog().logWarning("FTPCopy: failed to get file %s\n", subdir.c_str());
#							return -2;
#						}
#					}
#				}
#				SWCATCH (...) {}
#				if (term) {
#					retVal = -3;
#					break;
#				}
#			}
#		}
#		return retVal;
#	}
	

#	def getDirList(self, dirURL):
#		pass
	
#	def setPassive(self, passive):	
#		self.passive = passive
#	
#	def terminate(self): 
#		self.term = True
		
	
#	def getDirList(dir
	
