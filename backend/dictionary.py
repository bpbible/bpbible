#from Sword import *
from swlib.pysw import SW, TOP
from backend.book import Book
from util import classproperty
from util.unicode import to_str, to_unicode
from util.debug import dprint, WARNING
from util import string_util
import datetime
import display_options

current_year = datetime.date.today().year

topics_dict = dict()


class LazyTopicList(object):
	# these are the sizes of entries in SWORD dictionaries. Dividing total
	# index length by entry size gives number of entries.
	entry_sizes = {
		SW.RawLD:  6, 
		SW.RawLD4: 8, 
		SW.zLD:    8
	}
	
	# how many items do we grab around the one we are asked for?
	# TODO: tune this value
	GRAB_AROUND = 10

	"""Implement a lazy topic list. This precomputes its length, and caches
	any topics found"""
	def __init__(self, module):
		self.mod = module


		self.cardinality = 0
		self.entry_size = 0

		success = False
		try:
			success = self.read_entry_count()
		except Exception, e:
			dprint(WARNING, "Exception trying to read entry count", e)

		if not success:
			# Work this out the slow way
			topics = []
			self.mod.setPosition(TOP)

			while not ord(self.mod.Error()):
				try:
					topics.append(
						to_unicode(self.mod.getKeyText(), self.mod)
					)
				except UnicodeDecodeError, e:
					dprint(WARNING, "Error on ", e)
				self.mod.increment(1)
			
			self.topics = topics
		

	def read_entry_count(self):
		swld = SW.LD.castTo(self.mod)
		if not swld:
			dprint("WARNING", "Dictionary wasn't a SWLD!!!")
			entry_items = {}
		else:
			entry_items = self.entry_sizes
	
		for ld_class, value in entry_items.items():
			mod = ld_class.castTo(swld)
			if not mod:
				continue

			self.entry_size = value
			
			self.mod = mod
			self.cardinality = mod.getEntryCount()
			return True
	
	def __len__(self):
		if not self.entry_size:
			return len(self.topics)
		else:
			return self.cardinality
	
	def __getitem__(self, item):
		return to_unicode(self.mod.getKeyForEntry(item), self.mod)

class ListDataWrapper(object):
	def __init__(self, object):
		self.object = object
	
	def __len__(self):
		return len(self.object)
	
	def __getitem__(self, item):
		raise NotImplementedError
	
	@property
	def mod(self):
		return self.object.mod

class DateConverterLazyTopicList(ListDataWrapper):
	def __getitem__(self, item):
		return mmdd_to_date(self.object[item]) or self.object[item]

class TitleCaseConverterLazyTopicList(ListDataWrapper):
	def __getitem__(self, item):
		return string_util.titlecase(self.object[item])

def is_date_conversion_supported():
	# vietnamese under windows doesn't complete the loop
	#return wx.DateTime.Now().ParseFormat(wx.DateTime.Now().Format("%B %d"), "%B %d") != -1
	# True for now.
	return True

def date_to_mmdd(date, return_formatted=True):
	if not return_formatted and not is_date_conversion_supported():
		try:
			month, day = map(int, date.split(".", 1))
		except ValueError:
			pass
		else:
			return datetime.date(current_year, month, day)

	# tack the following bits on the end to see if they help give us dates
	# the second is February -> February 1
	additions = ["", " 1"]

	for addition in additions:
		try:
			date = datetime.datetime.strptime(date + addition, "%B %d")
			if return_formatted:
				return date.strftime("%m.%d")
			return datetime.date(current_year, date.month, date.day)
		except ValueError:
			pass
		
	return None

def mmdd_to_date(date):
	if not is_date_conversion_supported():
		return None

	try:
		month, day = map(int, date.split(".", 1))
	except ValueError:
		return None
	else:
		date = datetime.date(2008, month, day)

	return date.strftime("%B ") + str(date.day)

		
class Dictionary(Book):
	type = "Lexicons / Dictionaries"
	noun = "dictionary"
	is_dictionary = True
	categories_to_exclude = ["Daily Devotional"]

	def __init__(self, parent, version):
		super(Dictionary, self).__init__(parent, version)

		#self.SetModule(version)
		parent.on_before_reload += self.clear_cache


	def format_ref(self, module, ref, snap=True):
		if snap: 
			ref = self.snap_text(ref, module=module)

		if self.has_feature("DailyDevotion", module=module):
			ref = mmdd_to_date(ref) or ref
		else:
			ref = string_util.titlecase(ref)
			
		return ref
		
	
	def GetReference(self, ref, context = None, max_verses = 500,
			stripped=False, raw=False, end_ref=None):
		if not self.mod:
			return None

		assert not end_ref, "Dictionaries don't support ranges"

		raw = raw or display_options.options["raw"]

		render_text, render_start, render_end = self.get_rendertext()
		#TODO: use render_start and render_end?
		
		template = self.templatelist[-1]
		key = self.mod.getKey()
		key.setText(to_str(ref, self.mod))
		self.mod.setKey(key)
		
		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		
		if stripped:
			text = self.mod.StripText().decode("utf-8", "replace")
		else:
			text = render_text().decode("utf-8", "replace")
		
		d = dict(
			# render text so that we convert utf-8 into html
			range=to_unicode(self.mod.getKeyText(), self.mod),
			description=to_unicode(self.mod.Description(), self.mod),
			version=self.mod.Name(),
			reference_encoded=SW.URL.encode(self.mod.getKeyText()).c_str(),
			
		)
		d["reference"] = self.format_ref(self.mod, d["range"], snap=False)
		verses = template.header.safe_substitute(d)

		d1 = d
		if raw:
			d1["text"] = self.process_raw(self.mod.getRawEntry(), text,
											self.mod.getKey(), self.mod)
		else:
			d1["text"] = text

		verses += template.body.safe_substitute(d1)

		verses += template.footer.safe_substitute(d) #dictionary name
		return verses
	
	def clear_cache(self, parent=None):
		topics_dict.clear()
			
	def GetTopics(self, user_output=False):
		if not self.mod:
			return []
		
		# cache the topic lists
		name = self.mod.Name()
		if name not in topics_dict:
			topics = LazyTopicList(self.mod)
			topics_dict[name] = topics
		else:
			topics = topics_dict[name]

		if user_output:
			if self.is_daily_devotional:
				return DateConverterLazyTopicList(topics)
			else:
				return TitleCaseConverterLazyTopicList(topics)

		return topics

	def snap_text(self, text, module=None):
		mod = module or self.mod
		if mod is None:
			return text
		k = mod.getKey()
		k.setText(to_str(text, mod))
		mod.setKey(k)
		
		# snap to entry
		mod.getRawEntryBuf()
		return to_unicode(mod.getKeyText(), mod)

	@property
	def is_daily_devotional(self):
		return self.has_feature("DailyDevotion")

class DailyDevotional(Dictionary):
	category = "Daily Devotional"
	categories_to_exclude = ()

	@classproperty
	def noun(cls):
		return _("daily devotional")
