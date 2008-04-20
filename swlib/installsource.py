import urlparse

def split_source_directory(url):
	protocols = "ftp",
	for protocol in protocols:
		if url.startswith(protocol):
			protocol_string = "%s://" % protocol
			if not url.startswith(protocol_string):
				url = protocol_string + url
		
			_, netloc, path, _, _, _ = urlparse.urlparse(url)
			
			# Strip off slash
			path = path[1:]
			return netloc, path
	
	assert False, "Couldn't match url %s" % url

class InstallSource(object):
	def __init__(self, type="FTP", confEnt=None):
		self.type = ""
		self.source = ""
		self.directory = ""
		self.caption = ""
		self.localShadow = ""
		self.mgr = None
		

		if confEnt:
			self.caption, self.source, self.directory = confEnt.split("|")
			self.directory = removeTrailingSlash(self.directory)


	
	def getConfEnt(self):
		return "|".join(self.caption, self.source, self.directory)
	
	def flush(self):
		self.mgr = None

	def getMgr(self):
		if not self.mgr:
			# ..., False = don't augment ~home directory.
			self.mgr = Sword.SWMgr(self.localShadow, True, None, False, False)
		
		return self.mgr

	def set_url(self, url):
		self.source, self.directory = split_source_directory(url)

	def get_url(self):
		return self.source + "/" + self.directory

	url = property(get_url, set_url)

