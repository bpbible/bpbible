"""
bibleinterface.py

Exposes an interface onto a manager for bibles, commentaries, dictionaries and
generic books
"""
import os
import sys

from swlib.pysw import SW

from backend.book import Bible, Commentary
from backend.dictionary import Dictionary

from util import util
from util import confparser
from util.observerlist import ObserverList
from util.debug import dprint, MESSAGE
from backend.filter import MarkupInserter
from backend.genbook import GenBook
import config

if util.is_py2exe():
	# py2exe may get paths wrong
	if os.path.dirname(sys.argv[0]):
		os.chdir(os.path.dirname(sys.argv[0]))

class BibleInterface(object):
	def __init__(self, biblename="ESV", commentaryname="TSK",
	  		dictionaryname="ISBE", genbook="Josephus"):

		self.on_before_reload = ObserverList()
		self.on_after_reload = ObserverList()
		
		dprint(MESSAGE, "Creating manager")
		self.make_manager()
		dprint(MESSAGE, "/Creating manager")
		self.paths = set()

		self.bible = Bible(self, biblename) 
		self.commentary = Commentary(self, commentaryname)
		self.dictionary = Dictionary(self, dictionaryname)
		self.genbook = GenBook(self, genbook) 
		
		self.state = util.PushPopList()
		self.options = {}
		self.init_options()
	
	def init_options(self):
		for option, values in self.get_options():
			self.options[option] = self.mgr.getGlobalOption(option)
		
		#if people want no extras, here it is
		self.temporary_state()
		for option, values in self.get_options():
			self.set_option(option, values[0])

		self.plainstate = self.save_state()
		self.restore_state()
   

	def set_option(self, option, value=True):
		processed_value = value
		if type(value) == bool:
			processed_value = {True:"On", False:"Off"}[value]

		self.mgr.setGlobalOption(str(option), str(processed_value))
		self.options[option] = processed_value
	
	def temporary_state(self, options = None):
		self.state.push(dict(self.options))
		if(options):
			for key, value in options.items():
				self.set_option(key, value)
		
	
	def restore_state(self):
		state = self.state.pop()
		if not state: 
			return

		#restore state
		for key, value in state.items():
			self.set_option(key, value)

	def save_state(self):
		return dict(self.options)
	
	def GetModule(self, mod):
		return self.mgr.getModule(mod)

	def get_options(self):
		option_names = []
		for option_name in self.mgr.getGlobalOptionsVector():
			text = option_name.c_str()
			option_values = []
			for option_value in self.mgr.getGlobalOptionValuesVector(text):
				option_values.append(option_value.c_str())
			option_names.append((text, option_values))
		return option_names
	
	def get_tip(self, option):
		return self.mgr.getGlobalOptionTip(option)
			
	def augment_path(self, path):
		self.mgr.augmentModules(path, True)
		self.paths.add(path)
	
	def load_paths(self, filename=config.sword_paths_file):
		config_parser = confparser.config()
		try:
			f = open(filename)
			config_parser._read(f, filename)
		except EnvironmentError:
			return ["."]

		data_path = config_parser.get("Install", "DataPath")[0]
		if config_parser.has_option("Install", "AugmentPath"):
			paths = config_parser.get("Install", "AugmentPath")[::-1]
			if data_path not in paths:
				paths.append(data_path)
		else:
			paths = [data_path]

		return paths
	
	def write_paths(self, paths, filename=config.sword_paths_file):
		paths = paths[::-1]
		config_parser = confparser.config()
		config_parser.read(filename)
		if not config_parser.has_section("Install"):
			config_parser.add_section("Install")
		
		config_parser.set("Install", "DataPath", paths[0])
		config_parser.set("Install", "AugmentPath", [])
		augment_paths = config_parser.get("Install", "AugmentPath")
		del augment_paths[0]
		augment_paths.extend(paths[1:])

		config_parser.write(open(filename, "w"))
	
	def set_new_paths(self, paths):
		bible       = self.bible.version
		dictionary  = self.dictionary.version
		commentary  = self.commentary.version
		genbook     = self.genbook.version
		
		items = [(self.bible, bible), 
				 (self.dictionary, dictionary), 
				 (self.commentary, commentary), 
				 (self.genbook, genbook)
		]

		del self.mgr
		self.write_paths(paths)

		self.make_manager()
			
		self.paths = paths

		for item, module in items:
			# put the items on hold so that they don't fire until all modules
			# are changed
			item.observers.hold()
			
		for item, module in items:
			if item.ModuleExists(module):
				item.SetModule(module)
				continue

			mods = item.GetModuleList()
			if mods:
				item.SetModule(mods[0])
			else:
				item.SetModule(None)
		
		# turn our items on again
		for option, value in self.options.iteritems():
			self.set_option(option, value)

		self.init_options()

		for item, module in items:
			item.observers.finish_hold()
				
		
	def make_manager(self):
		#if hasattr(self, "dictionary"):
		#	self.dictionary.clear_cache()
		# turn off logging
		system_log = SW.Log.getSystemLog()
		log_level = system_log.getLogLevel()
		system_log.setLogLevel(0)
		try:
			self.markup_inserter = MarkupInserter(self)
			markup = SW.MyMarkup(self.markup_inserter, 
				SW.FMT_HTMLHREF, SW.ENC_HTML)
			#markup = SW.MarkupFilterMgr(SW.FMT_HTMLHREF, SW.ENC_HTML)
			markup.thisown = False
			self.on_before_reload(self)


			paths = self.load_paths()[::-1]
	
			
			mgr = SW.Mgr(paths[0], False, markup)
			
			#TODO: test this
			ansa = mgr.Load()
			
			item_upto = 1

			# keep on trying to load the paths until we hit the first one we
			# could load
			while ansa == -1 and item_upto < len(paths):
				mgr.configPath = paths[item_upto]
				ansa = mgr.Load()
				item_upto += 1

			# and then augment the rest
			for item in paths[item_upto:]:
				mgr.augmentModules(item)
			
			self.mgr = mgr
			
			self.on_after_reload(self)
			
			return mgr
		finally:
			# reset it to what it was
			system_log.setLogLevel(log_level)

biblemgr = BibleInterface("ESV", "TSK", "ISBE") 

biblemgr.dictionary.templatelist.push(config.other_template)
biblemgr.commentary.templatelist.push(config.other_template)
biblemgr.bible.templatelist.push(config.bible_template)
