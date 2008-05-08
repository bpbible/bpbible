#from Sword import *
from swlib.pysw import SW
from backend.book import Book
from util.unicode import to_str, to_unicode
from util.debug import dprint, WARNING

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
		self.mod = SW.LD.castTo(module)
		if not self.mod:
			dprint("WARNING", "Dictionary wasn't a SWLD!!!")
			entry_items = {}
		else:
			entry_items = self.entry_sizes

		self.cardinality = 0
		self.entry_size = 0
		self.upper = Upper(self)

		success = False
		try:
			success = self.read_entry_count(entry_items)
		except Exception, e:
			dprint(WARNING, "Exception trying to read entry count", e)

		if not success:
			# Work this out the slow way
			topics = []
			pos = SW.SW_POSITION(1)
			
			self.mod.setPosition(pos)

			while(not ord(self.mod.Error())):
				try:
					topics.append(
						to_unicode(self.mod.getKeyText(), self.mod)
					)
				except UnicodeDecodeError, e:
					dprint(WARNING, "Error on ", e)
				self.mod.increment(1)
			
			self.topics = topics
		

	def read_entry_count(self, entry_items):
		for ld_class, value in entry_items.items():
			mod = ld_class.castTo(self.mod)
			if not mod:
				continue
			
			p = "%s%s.idx" % (
				mod.getConfigEntry("PrefixPath"),
				mod.getConfigEntry("DataPath"))

			self.entry_size = value
			f = open(p)
			
			# goto end of file
			f.seek(0, 2)
			
			# and find what we are upto
			self.cardinality = f.tell() / self.entry_size

			f.close()
			self.topics = [None for x in range(self.cardinality)]
			return True

	
	def __len__(self):
		if not self.entry_size:
			return len(self.topics)
		else:
			return self.cardinality
	
	def __getitem__(self, item):
		if self.entry_size and self.topics[item] is None:
			myrange = [x for x in 
				xrange(item - self.GRAB_AROUND, item + self.GRAB_AROUND + 1)
				if 0 <= x < self.cardinality]
		
			self.mod.setPosition(SW.SW_POSITION(1))

			# go to first item we need to
			first = myrange.pop(0)
			self.mod += first
			self.topics[first] = to_unicode(
				self.mod.getKeyText(), self.mod
			)
			

			# and then any additional ones
			for additional_item in myrange:
				self.mod += 1
				self.topics[additional_item] = to_unicode(
					self.mod.getKeyText(), self.mod
				)
				

		return self.topics[item]
		
class Upper(object):
	def __init__(self, object):
		self.object = object
	
	def __len__(self):
		return len(self.object)
	
	def __getitem__(self, item):
		return self.object[item].upper()
	
class Dictionary(Book):
	type = "Lexicons / Dictionaries"
	def __init__(self, parent, version):
		super(Dictionary, self).__init__(parent, version)

		#self.SetModule(version)
		parent.on_before_reload += self.clear_cache


	def GetReference(self, ref, context = None, max_verses = 500, raw=False):
		if not self.mod:
			return None
		template = self.templatelist()
		key = self.mod.getKey()
		key.setText(to_str(ref, self.mod))
		self.mod.setKey(key)
		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		text = self.mod.RenderText()
		
		d = dict(
			# render text so that we convert utf-8 into html
			range=self.mod.RenderText(self.mod.KeyText()), 
			description=self.mod.RenderText(self.mod.Description()),
			version=self.mod.Name(),
		)

		verses = template.header.safe_substitute(d)
		d1 = d
		if raw:
			d1["text"] = self.mod.getRawEntry()
		else:
			d1["text"] = text

		verses += template.body.safe_substitute(d1)

		verses += template.footer.safe_substitute(d) #dictionary name
		return verses
	
	def clear_cache(self, parent=None):
		topics_dict.clear()
			
	def GetTopics(self):#gets topic lists
		topics = []
		if(self.mod):
			name = self.mod.Name()
			if name in topics_dict:
				return topics_dict[name]
			
			topics = LazyTopicList(self.mod)
		else:
			return []
		topics_dict[name] = topics
		return topics
	
	def snap_text(self, text):
		mod = self.mod
		if mod is None:
			return text
		k = mod.getKey()
		k.setText(to_str(text, mod))
		mod.setKey(k)
		
		# snap to entry
		mod.getRawEntryBuf()
		return to_unicode(mod.getKeyText(), mod)

