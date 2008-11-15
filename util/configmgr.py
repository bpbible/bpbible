from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from observerlist import ObserverList
from debug import dprint, WARNING, MESSAGE
import os
import cPickle as pickle
import config
from swlib.pysw import SW

# This is the version of the configuration file, and should be updated
# whenever there is a need to because the configuration changed (though it
# might as well be kept roughly in sync with version numbers).
CONFIG_VERSION = "0.4"
	
class ConfigSection(object):
	def __init__(self, section):
		self.items = {}
		self.watches = {}
		self.section = section
		self.lazy_items = []
		self.item_types = {}
		#self.items_defined = []
	
	def __getitem__(self, item):
		if item in self.lazy_items:
			value = self.items[item]()
			#TODO: have initial value watchable for when set?
			self.items[item] = value
			self.lazy_items.remove(item)
			return value

		return self.items[item]
	
	def __setitem__(self, item, value):
		if item not in self.items:
			raise ValueError("Unknown config item %s.%s" 
				% (self.section, item))
		
		old_value = self.items[item]
		self.items[item] = value
		
		self.watches[item]((self.section, item), old_value, value)
	
	def add_item(self, item, initial_value=None, is_initial_lazy=False,
			item_type=str):

		assert item_type in (str, int, bool, float, "pickle"), "Can only handle items of type str, int, bool, float, pickle"
		self.items[item] = initial_value
		if is_initial_lazy:
			self.lazy_items.append(item)
		
		self.watches[item] = ObserverList()
		self.item_types[item] = item_type
	
	def watch(self, item, func):
		self.watches[item] += func

class ConfigManager(object):
	def __init__(self, write_path=None):
		self.sections = {}
		self.add_section("Internal")
		self.write_path = write_path
		self["Internal"].add_item("version", CONFIG_VERSION)
		
		self.before_save = ObserverList()
		
	
	def add_section(self, section):
		if section not in self.sections:
			self.sections[section] = ConfigSection(section)
		return self.sections[section]
	
	def __getitem__(self, item):
		return self.sections[item]
	
	def save(self):
		self.before_save()
		config_parser = RawConfigParser()
		#config_parser.readfp(
		for section_name, section in self.sections.items():
			config_parser.add_section(section_name)
			for item in section.items:
				type_process = {
					str: str,
					bool: str,
					int: str,
					float: str,
					"pickle": pickle.dumps
				}[section.item_types[item]]
				
				# look it up now. If this is a lazily evaluated item, find its
				# value before we close
				# TODO: is this what we really want to do?
				value = section[item]

				config_parser.set(section_name, item, type_process(value))
		
		directory = os.path.dirname(self.write_path)
		if not os.path.exists(directory):
			os.makedirs(directory)
		
		config_parser.write(open(self.write_path, "w"))
	
	def load(self, paths=()):
		config_parser = RawConfigParser()
		loaded = config_parser.read(self.write_path)
		loaded += config_parser.read(paths)
		if config_parser.has_option("Internal", "version"):
			version = config_parser.get("Internal", "version")

		elif loaded:
			version = "0.3"

		else:
			version = CONFIG_VERSION
		
		if SW.Version(version) < SW.Version(CONFIG_VERSION):
			self.upgrade(config_parser, SW.Version(version))

		for section_name in config_parser.sections():
			if section_name not in self.sections:
				dprint(WARNING, "Skipping unknown section '%s'" % section_name)
				continue

			section = self.sections[section_name]
			for option in config_parser.options(section_name):
				if option not in section.items:
					dprint(WARNING, "Skipping unknown item '%s.%s'" % (
						section_name, option))
					continue

				if option in section.lazy_items:
					section.lazy_items.remove(option)

				type_reader = {
					str: config_parser.get,
					bool: config_parser.getboolean,
					int: config_parser.getint,
					float: config_parser.getfloat,
					"pickle": lambda x, y:pickle.loads(config_parser.get(x, y))
				}[section.item_types[option]]

				section[option] = type_reader(section_name, option)

		self["Internal"]["version"] = CONFIG_VERSION
	
	def upgrade(self, config_parser, version_from):
		dprint(MESSAGE, "Upgrading from", version_from.getText())
		if version_from <= SW.Version("0.3"):
			self._upgrade_03_to_04(config_parser)

	def _upgrade_03_to_04(self, config_parser):
		try:
			# upgrade font
			font = config_parser.get("Html", "font_name")
			size = config_parser.getint("Html", "base_text_size")
			
			# only upgrade if it wasn't the same
			if font != "Arial" or size != 10:
				if not config_parser.has_section("Font"):
					config_parser.add_section("Font")

				config_parser.set("Font", "default_fonts", pickle.dumps(
					(font, int(size), False)
				))

		except (NoSectionError, NoOptionError):
			pass
		
def _test():
	"""\
>>> config = ConfigManager(write_path="data.conf")
>>> harmony_settings = config.add_section("Harmony")
>>> harmony_settings.add_item("last_harmony")
>>> def item_changed(item, old_value, new_value):
... 	print "%s.%s changed from %s to %s" % (item[0], item[1], 
... 				repr(old_value), repr(new_value))
...
>>> harmony_settings.watch("last_harmony", item_changed)
>>> harmony_settings["last_harmony"] = "Robinson"
Harmony.last_harmony changed from None to 'Robinson'
>>> harmony_settings["last_harmony"]
'Robinson'
>>> config.save()
>>> config2 = ConfigManager(write_path="data.conf")
>>> harmony_settings2 = config2.add_section("Harmony")
>>> harmony_settings2.add_item("last_harmony")
>>> config2.load()
>>> harmony_settings2["last_harmony"]
'Robinson'
"""
	import doctest
	doctest.testmod()

config_file = os.path.join(config.data_path, "data.conf")
config_manager = ConfigManager(write_path=config_file)

if __name__ == '__main__':
	_test()

