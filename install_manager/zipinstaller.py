import os
import zipfile
from swlib.pysw import SW
from util.debug import dprint, WARNING

ZIPFILE_TMP = "zipfile.tmp"
class InvalidModuleException(Exception):
	pass

class ZipInstaller(object):
	def __init__(self, zip_path):
		self.zip_path = zip_path
		self.zip_file, conf_file = self.open_zipfile(zip_path)
		
		self.name, self.config_section = self.read_config(conf_file)
	
	def read_config(self, conf_file):
		outfile = open(ZIPFILE_TMP, "wb")
		outfile.write(self.zip_file.read(conf_file))
		outfile.close()
		
		item = SW.Config(ZIPFILE_TMP)
		sections = item.getSections()
		it = sections.begin()
		if it == sections.end():
			raise InvalidModuleException("Cannot read module metadata")
		
		name, section = it.value()
		name = name.c_str()
		it += 1
		if it != sections.end():
			dprint(WARNING, 
				"More than one section in module. Taking the first one:",
				name
			)
		
		os.remove(ZIPFILE_TMP)
		return name, section

	def open_zipfile(self, zip_path):
		zip_file = zipfile.ZipFile(zip_path)
		file_list = zip_file.filelist
		module_name = None

		for zip_info in file_list:
			item = zip_info.filename
			if os.path.dirname(item) == "mods.d" and item.endswith(".conf"):
				# we found a .conf file in the mods.d directory
				# this is the only check currently done
				return zip_file, item
	
		raise InvalidModuleException("File does not appear to be a valid book")

	def extract_zipfile(self, zip_file, dest=""):
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
		
		for item in self.zip_file.filelist:
			# don't bother about directories
			if item.endswith("/"):
				continue

			directory = os.path.dirname(item)
			absolute_directory = dest + directory
			
			if not os.path.exists(absolute_directory):
				os.makedirs(absolute_directory)

			outfile = open(dest + item, "wb")
			outfile.write(self.zip_file.read(item))
			outfile.close()

	# SWModule compatibility functions
	def Name(self):
		return self.name
	
	def Description(self):
		return self.getConfigEntry("Description")

	def getConfigEntry(self, key):
		it = self.config_section.find(SW.Buf(key))
		if it == self.config_section.end():
			return None
		
		key, value = it.value()
		return value.c_str()

