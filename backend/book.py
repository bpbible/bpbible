#from swlib.pysw import *
import re
import passage_list
from swlib.pysw import VK, SW, GetBestRange, GetVerseStr, TOP
from backend.verse_template import VerseTemplate
from util import observerlist
from util import classproperty
from util.debug import dprint, WARNING, ERROR
from util.unicode import to_str, to_unicode

import config

#ERR_OK = '\x00'

class Book(object):
	type = None
	def __init__(self, parent, version = ""):
		self.parent = parent
		self.mod = None
		self.observers = observerlist.ObserverList()
		self.template = VerseTemplate(body = "$text")
		self.templatelist = [self.template]
		self.vk = VK()
		self.headings = False
		if self.ModuleExists(version):
			self.SetModule(version)
		else:
			mods = self.GetModuleList()
			if mods:
				self.SetModule(mods[0])
			else:
				dprint(WARNING, "No modules of type", self.type)
				self.SetModule(None)

	def SetModule(self, modname, notify=True):
		"""Sets the module to modname"""
		oldmod = self.mod

		# No book at all
		if modname is None:
			self.mod = None

		elif isinstance(modname, SW.Module):
			self.mod = modname
		
		else:
			# look up the book
			new_mod = self.parent.get_module(modname)	
			if not new_mod:
				return False
			
			self.mod = new_mod
				
		self.features = None
		
		if self.mod != oldmod and notify:
			self.observers(self.mod)

		return True
	
	def ModuleExists(self, modname):
		return modname in self.GetModuleList()

	@property
	def version(self):
		if self.mod:
			return self.mod.Name()

		#return "<No module>"

	def GetModuleList(self):
		return sorted([name for name, mod in self.parent.modules.iteritems()
				if mod.Type() == self.type or self.type is None])
	
	def GetModules(self):
		return sorted([mod for name, mod in self.parent.modules.iteritems()
				if mod.Type() == self.type or self.type == None], 
				key = lambda mod: mod.Name())
	
	@staticmethod
	def get_template_options():
		items = {
			"$":			"A $ sign", 
			"range":		"The range of verses", 
			"version":		"The version this is taken from",
			"description":	"A description of the version",
		}

		body_items = {			
			"text":			"The text of a verse",
			"versenumber":	"The versenumber",
			"reference": 	"The reference for each verse",
			"bookname":		"The name of the current book",
			"bookabbrev":	"A shorter abbreviation of the book name",
			"chapternumber":"The number of the chapter in the book"
		}

		heading_items = {
			"heading":		"The text of the heading"
		}

		body_items.update(items)
		heading_items.update(body_items)

		return dict(body=body_items, headings=heading_items, 
					header=items, footer=items)

	
	def GetReference(self, ref, specialref="",
			specialtemplate=None, context="", max_verses=177, raw=False,
			stripped=False, template=None, display_tags=None,
			exclude_topic_tag=None, end_ref=None, headings=False):
		"""GetReference gets a reference from a Book.
		
		specialref is a ref (string) which will be specially formatted 
		according to specialtemplate.

		exclude_topic_tag: If this is not None, then it is a topic that
		should not have a tag generated, because it is obvious from the
		context (for example, the topic window for that topic).
		"""
		#only for bible keyed books
		if not self.mod:
			return None
		
		if template is None and self.templatelist:
			template = self.templatelist[-1]
		if context:
			lastverse = context
		else:
			lastverse = ""

		if display_tags is None:
			display_tags = passage_list.settings.display_tags
	
		if end_ref:
			ref += " - " + end_ref

		old_headings = self.vk.Headings(headings)

		verselist = self.vk.ParseVerseList(to_str(ref), to_str(lastverse), True)
		rangetext = GetBestRange(verselist.getRangeText())
		if rangetext == "":
			self.vk.Headings(old_headings)
			#if invalid reference, return empty string
			return u""
			
		
		if specialref:
			specialref = GetVerseStr(specialref)
		
		description = to_unicode(self.mod.Description(), self.mod)
		d = dict(range=rangetext, 
				 version=self.mod.Name(), 
				 description=description)

		text = template.header.safe_substitute(d)
		verses = []
		
		
		for body_dict, headings in self.GetReference_yield(
			verselist, max_verses, raw, stripped,
			exclude_topic_tag=exclude_topic_tag,
		):
			# if we have exceeded the verse limit, body_dict will be None
			if body_dict is None:
				verses.append(config.MAX_VERSES_EXCEEDED % max_verses)
				break

			body_dict.update(d)
			
			t = template

			if specialref == body_dict["reference"]:
				t = specialtemplate

			verse = u""
			for heading_dict in headings:
				verse += t.headings.safe_substitute(heading_dict)
			
			verse += t.body.safe_substitute(body_dict)

			verses.append(verse)
		
		self.vk.Headings(old_headings)

		text += template.finalize(''.join(verses))
		text += template.footer.safe_substitute(d)
		return text
		
			
	def GetReference_yield(self, verselist, max_verses=177, 
			raw=False, stripped=False, module=None, exclude_topic_tag=None):
		"""GetReference_yield: 
			yield the body dictionary and headings dictinoary
			for each reference.

		Preconditions:
			one of module or self.mod is not None
			verselist is valid"""
		#only for bible keyed books
		verselist.setPosition(TOP)
		#verselist.Persist()
		mod = module or self.mod
		mod.SetKey(verselist)
		verses_left = max_verses

		ERR_OK = chr(0)
		render_text = self.get_rendertext(mod)

		while verselist.Error() == ERR_OK:
			if verses_left == 0:
				yield None, None
				return

			
			mod.SetKey(verselist)
			key = mod.getKey()
			versekey = VK.castTo(key)
			#if(self.headings):
			#	versekey.Headings(1)
			reference = versekey.getText()



			if raw:
				text = mod.getRawEntry().decode("utf-8", "replace")
			
			elif stripped:
				text = mod.StripText().decode("utf-8", "replace")
				
				
			else:
				text = render_text()
			
			# XXX: This needs to be done better than this.  Move into
			# subclass somehow.
			if isinstance(self, Bible):
				tags = self.insert_tags(versekey, exclude_topic_tag)
			else:
				tags = ""
 
			body_dict = dict(text=text,
						  versenumber = versekey.Verse(), 
						  chapternumber = versekey.Chapter(), 
						  booknumber = ord(versekey.Book()),
						  bookabbrev = versekey.getBookAbbrev(),
						  bookname = versekey.getBookName(),
						  reference = reference,
						  tags = tags,
			)	

					  
			headings = self.get_headings(reference, mod)
			versekey = VK.castTo(key)
			heading_dicts = []
			for heading, canonical in headings:
				if not raw:
					if stripped:
						heading = mod.StripText(heading).decode(
							"utf8",
							"replace"
						)
					else:
						heading = render_text(heading)

				heading_dict = dict(heading=heading, canonical=canonical)
				heading_dict.update(body_dict)
				heading_dicts.append(heading_dict)
				
			yield body_dict, heading_dicts	

			verselist.increment(1)
			verses_left -= 1

	
	def insert_tags(self, verse_key, exclude_topic_tag):
		"""Generates and returns all the passage tags for the given verse."""
		manager = passage_list.get_primary_passage_list_manager()
		return "".join(
				self._insert_tags_for_topic(verse_key, topic, exclude_topic_tag)
				for topic in manager.subtopics
			)

	def _insert_tags_for_topic(self, verse_key, topic, exclude_topic_tag):
		if topic != exclude_topic_tag:
			result = self._topic_tags(verse_key, topic)
		else:
			result = ""

		for subtopic in topic.subtopics:
			result += self._insert_tags_for_topic(verse_key, subtopic, exclude_topic_tag)

		return result
	
	def _topic_tags(self, verse_key, topic):
		result = ""
		for passage in topic.passages:
			if passage.contains_verse(verse_key):
				result += "<passage_tag topic_id=%d passage_entry_id=%d> &nbsp;" \
					% (topic.get_id(), passage.get_id())
		return result
	
	def get_headings(self, ref, mod=None):
		"""Gets an array of the headings for the current verse. Must have just
		called RenderText on the verse you want headings for"""
		mod = mod or self.mod

		heading = SW.Buf("Heading")
		preverse = SW.Buf("Preverse")
		interverse = SW.Buf("Interverse")
		canonical = SW.Buf("canonical")
		headings = []
		heading_types = [preverse, interverse]
		attrmap = mod.getEntryAttributesMap()#[SW.Buf("Heading")
		if heading in attrmap:
			h = attrmap[heading]
			if preverse in h:
				i = 0
				p = h[preverse]
				while True:
					is_canonical = "false"
					i_buf = SW.Buf(str(i))

					# try to see if this is a canonical heading
					# unfortunately, if there happens to be a interverse
					# heading after a canonical heading, it will overwrite it
					# so we may not get the correct answer. This oughtn't to
					# matter overly much
					if i_buf in h:
						attributes = h[i_buf]
						if(canonical in attributes and
							attributes[canonical].c_str() == "true"):
							is_canonical = "true"
						
					if i_buf in p:
						headings.append((p[i_buf].c_str(), is_canonical))

					else: break
					i += 1
			
				if not headings:
					dprint(WARNING, "no heading found for", ref)

		return headings
				
	def GetReferences(self, ref, context="", max_verses = -1):
		"""Gets a list of references.
		
		In: ref - list of references
			context: context of first in list
		Out: A list of verses
		"""
		# TODO: If we have a list passed in like this:
		# ref= ['104:6', '8, 10, 105:1', '3'], context = 'PS 104:14'
		# for second item, GetVerseStr will return Psalms 104:8, instead
		# of Psalms 105:1, so the third retrieved will be 104:3, not 105:3
		# Fixes:
		# Make GetVerseStr take last in list, not first as optional parameter
		results = []
		lastref = context
		for j in ref:
			#get text
			results.append(self.GetReference(j, context=lastref, 
							max_verses = max_verses))
			# set context for next ref
			lastref = GetVerseStr(j, lastref)

		return results

	def GetFootnoteData(self, mod, passage, number, field):
		if mod != self.mod:
			mod = self.parent.get_module(mod)
			if mod is None:
				return None

		else:
			mod = self.mod

		vk = SW.Key(passage)
		mod.SetKey(vk) #set passage
		mod.RenderText() # force entry attributes to get set	
		data = mod.getEntryAttributesMap()[SW.Buf("Footnote")] \
			[SW.Buf(number)][SW.Buf(field)].c_str()

		# put it through the render filter before returning it
		return mod.RenderText(data)


	def GetReferenceFromMod(self, modname, ref, max_verses = -1):
		if not self.ModuleExists(modname):
			return None
		
		oldmod = self.version
		try:
			self.SetModule(modname, notify=False)
			verses = self.GetReference(ref, max_verses=max_verses)
		finally:
			self.SetModule(oldmod, notify=False)

		return verses


	def GetReferencesFromMod(self, modname, ref, context="", max_verses=-1):
		oldmod = self.version
		try:
			self.SetModule(modname, notify=False)
			verses = self.GetReferences(ref, context, max_verses = max_verses)
			
		finally:
			self.SetModule(oldmod, notify=False)
		
		return verses

	def GetChapter(self, ref, specialref="", specialtemplate = None, 
			context="", raw=False):
		#vk = self.mod.getKey()
		self.vk.setText(to_str(ref, self.mod))
		
		#get first ref
		text = self.vk.getText()

		match = re.match("([\w\s]+) (\d+):(\d+)", text)
		if match:
			book, chapter, verse = match.group(1, 2, 3)

			# include the introduction
			text = "%s %s:0-%s %s" % (book, chapter, book, chapter)

		else:
			dprint(ERROR, "Couldn't parse verse text", text)

		return self.GetReference(text, specialref, specialtemplate, context,
				raw=raw, headings=True)

	def get_rendertext(self, mod=None):
		"""Return the text render function.

		This makes sure that plaintext modules render whitespace properly"""
		module = mod or self.mod
		render_text = module.RenderText

		if module.getConfigEntry("SourceType") in (None, "Plaintext"):
			def render_text(*args):
				text = module.RenderText(*args)
				text = text.replace("\n", "<br />")
				return re.sub(" ( +)", lambda x:"&nbsp;"*len(x.group(1)), text)

		return render_text
	
	def has_feature(self, feature):
		if not self.mod:
			return False
		
		if self.features is None:
			self.features = []
			mod = self.mod
		
			map = mod.getConfigMap()
			feature_buf = SW.Buf("Feature")
			featureBegin = map.lower_bound(feature_buf)
			featureEnd = map.upper_bound(feature_buf)
			while featureBegin != featureEnd:
				v = featureBegin.value()
				self.features.append(v[1].c_str())

				featureBegin += 1

		return feature in self.features
		
				
class Commentary(Book):
	type = "Commentaries"

	@classproperty
	def noun(cls):
		return _("commentary")


class Bible(Book):
	type = "Biblical Texts"
	@classproperty
	def noun(cls):
		return _("Bible")


