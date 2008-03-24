from ConfigParser import RawConfigParser
from observerlist import ObserverList
from debug import dprint, WARNING
import os
import cPickle as pickle
	
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

		assert item_type in (str, int, bool, float, "pickle"), "Can only handle items of type str, int, bool, float, picklke"
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
		self["Internal"].add_item("path", write_path)
		self.before_save = ObserverList()
		
	
	def add_section(self, section):
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

		config_parser.write(open(self["Internal"]["path"], "w"))
	
	def load(self, paths=(os.path.expanduser('~/bpbible/data.cfg'),)):
		config_parser = RawConfigParser()
		config_parser.read(self["Internal"]["path"])
		config_parser.read(paths)
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

config_manager = ConfigManager(write_path="data/data.conf")

if __name__ == '__main__':
	_test()

