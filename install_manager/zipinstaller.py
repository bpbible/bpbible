import os
import zipfile
from swlib.pysw import SW
from util.debug import dprint, WARNING, INSTALL_ZIP
from util import confparser
from cStringIO import StringIO

ZIPFILE_TMP = "zipfile.tmp"

class InvalidModuleException(Exception):
	pass

class BadMetadata(Exception):
	pass

class MultiMap(dict):
	def items(self):
		for item, values in self.iteritems():
			for value in values:
				yield SW.Buf(item), SW.Buf(value)
	
class ZipInstaller(object):
	def __init__(self, zip_path):
		self.zip_path = zip_path
		self.zip_file, conf_file = self.open_zipfile(zip_path)
		
		self.config_section, self.name = self.read_config(conf_file)
	
	def read_config(self, conf_file):
		config_parser = confparser.config()
		file_obj = StringIO(self.zip_file.read(conf_file))
		
		config_parser._read(file_obj, conf_file)
		
		sections = config_parser.sections()
	
		if not sections:
			raise BadMetadata("Cannot read book metadata in file %s" %
				self.zip_file)
		
		if len(sections) > 1:
			dprint(WARNING, 
            	"More than one section in module. Taking the first one:",
            	sections[0]
            )

		section_name = sections[0]
		config_section = MultiMap()
		
		for item in config_parser.options(section_name):
			config_section[item] = config_parser.get(section_name, item)

		return config_section, section_name
		
	def open_zipfile(self, zip_path):
		zip_file = self.read_zipfile(zip_path)
		file_list = zip_file.filelist
		module_name = None

		for zip_info in file_list:
			dprint(INSTALL_ZIP, "Has file %s" % zip_info.filename)
			if self.is_conf(zip_info):
				return zip_file, zip_info.filename
	
		raise InvalidModuleException("File does not appear to be a valid book")
	
	def extract_zipfile(self, dest="", progress=lambda percent, string:None):
		"""Extract a zip file.

		Rawzip layout looks like this
		modules/
			comments/
				rawfiles/
					personal/
						ot
						nt
						ot.vss
						nt.vss
		mods.d/
			personal.conf
		
		
		This doesn't bother about setting time stamps at all."""
		
		length = len(self.zip_file.filelist)

		for idx, zipinfo in enumerate(self.zip_file.filelist):
			# don't bother about directories
			item = zipinfo.filename
			progress((idx*100)/length, "Extracting %s" % item)
			dprint(INSTALL_ZIP, "Extracting %s" % item)
			

			if item.endswith("/"):
				continue

			filename = self.get_extracted_path(item)
			dprint(INSTALL_ZIP, "Extract to: %s" % filename)

			directory = os.path.dirname(filename)
			absolute_directory = os.path.join(dest, directory)
			
			if not os.path.exists(absolute_directory):
				os.makedirs(absolute_directory)

			outfile = open(os.path.join(dest, filename), "wb")
			outfile.write(self.zip_file.read(item))
			outfile.close()

	# These three functions are overridden to support Windows and Mac zips
	def read_zipfile(self, zip_path):
		return zipfile.ZipFile(zip_path)
	
	def is_conf(self, zip_info):
		item = zip_info.filename
		# we found a .conf file in the mods.d directory
		# this is the only check currently done to check whether this is a
		# valid module
		
		return os.path.dirname(item) == "mods.d" and item.endswith(".conf")
	
	def get_extracted_path(self, item):
		# for raw zips, the extract path is the path in the zip file
		return item
		

	# SWModule compatibility functions
	def Name(self):
		return self.name
	
	def Description(self):
		return self.getConfigEntry("Description")

	def getConfigEntry(self, key):
		if key in self.config_section:
			return self.config_section[key][0]

	def getConfigMap(self):
		return self.config_section

	def Encoding(self):
		mapping = {
			None:chr(SW.ENC_LATIN1),
			"UTF-8":chr(SW.ENC_UTF8),
			"Latin-1":chr(SW.ENC_LATIN1)
		}
		
		enc = self.getConfigEntry("Encoding")
		if enc in mapping:
			return mapping[enc]

		dprint(WARNING, 
			"Invalid encoding '%s' in module %s" % (enc,self.name)
		)
		return chr(SW.ENC_LATIN1)
	

class MacZipInstaller(ZipInstaller):
	def is_conf(self, zip_info):
		item = zip_info.filename
		dirname = os.path.dirname(item)

		# personal would be Personal.swd\mods.d\personal.conf
		
		# we found a .conf file in the mods.d directory
		# this is the only check currently done to check whether this is a
		# valid module
		
		return ".swd/mods.d" in dirname and item.endswith(".conf")

	def get_extracted_path(self, item):
		segments = []
		head = item

		# for Mac zips, chew off the starting *.swd
		while True:
			head, tail = os.path.split(head)
			segments.insert(0, tail)
			if not head:
				break
		
		if segments[0].endswith(".swd"):
			item = os.path.join(*segments[1:])

		return item

	
class WindowsZipInstaller(ZipInstaller):
	def read_zipfile(self, zip_path):
		zip = zipfile.ZipFile(zip_path)
		for item in zip.filelist:
			if item.filename == "data.zip":
				stringio = StringIO(zip.read(item.filename))
				return zipfile.ZipFile(stringio)

		raise InvalidModuleException(
			"File does not appear to be a valid Windows style book"
		)
	
	def is_conf(self, zip_info):
		item = zip_info.filename
		
		# we found a .conf file in the newmods directory
		# this is the only check currently done to check whether this is a
		# valid module
		return os.path.dirname(item) == "newmods" and item.endswith(".conf")
		
	def get_extracted_path(self, item):
		segments = []
		head = item

		# for Windows zips, change all starting newmods into mods.d
		while True:
			head, tail = os.path.split(head)
			segments.insert(0, tail)
			if not head:
				break
		
		if segments[0] == "newmods":
			segments[0] = "mods.d"
		
		item = os.path.join(*segments)

		return item
		
		

zip_installers = ZipInstaller, MacZipInstaller, WindowsZipInstaller

def find_zip_installer(filename):
	for zip_installer in zip_installers:
		dprint(INSTALL_ZIP, "Trying to load with", zip_installer)	
		try:
			return zip_installer(filename)
		except InvalidModuleException, e:
			# it might not be this type of installer...
			dprint(INSTALL_ZIP, "Exception thrown", e)
	
	dprint(INSTALL_ZIP, "Could not find handler for %s" % filename)
	raise InvalidModuleException("File does not appear to be a valid book")
	
			
