#from swlib.pysw import *
import re
from swlib.pysw import VK, SW, GetBestRange, GetVerseStr
from util.util import PushPopList, VerseTemplate
from util import observerlist
from util.debug import dprint, WARNING
from util.unicode import to_str, to_unicode

import config

#ERR_OK = '\x00'

vk = VK()

class Book(object):
	type = None
	def __init__(self, parent, version = ""):
		self.parent = parent
		self.mod = None
		self.observers = observerlist.ObserverList()
		self.template = VerseTemplate(body = "$text")
		self.templatelist = PushPopList(self.template)
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
		return [name for name, mod in self.parent.modules.iteritems()
				if mod.Type() == self.type or self.type is None]
	
	def GetModules(self):
		return [mod for name, mod in self.parent.modules.iteritems()
				if mod.Type() == self.type or self.type == None]
	
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
			specialtemplate=None, context="", max_verses=176, raw=False):
		"""GetReference gets a reference from a Book.
		
		specialref is a ref (string) which will be specially formatted 
		according to specialtemplate"""
		#only for bible keyed books
		if not self.mod:
			return None
		vk = VK()
		if context:
			lastverse = context
		else:
			lastverse = ""
	
		verselist = vk.ParseVerseList(to_str(ref), to_str(lastverse), True)
		rangetext = GetBestRange(verselist.getRangeText())
		if rangetext == "":
			return rangetext #if invalid reference, return empty string
		
		#verselist.SetPosition(SW_POSITION(1))
		#verselist.Persist()
		self.mod.SetKey(verselist)
		template = self.templatelist()
		description = to_unicode(self.mod.Description(), self.mod)
		d = dict(range=rangetext, 
				 version=self.mod.Name(), 
				 description=description)

		verses = template.header.safe_substitute(d)
		if specialref:
			specialref = GetVerseStr(specialref)

		verses_left = max_verses

		ERR_OK = chr(0)
		render_text = self.get_rendertext()

				

		while verselist.Error() == ERR_OK:
			if verses_left == 0:
				verses += config.MAX_VERSES_EXCEEDED % max_verses
				break

			
			self.mod.SetKey(verselist)
			key = self.mod.getKey()
			versekey = VK.castTo(key)
			verse = ""
			#if(self.headings):
			#	versekey.Headings(1)
			reference = versekey.getText()



			if not raw:
				text = render_text()
			else:
				text = self.mod.getRawEntry()
 
			body_dict = dict(text=text,
						  versenumber = versekey.Verse(), 
						  chapternumber = versekey.Chapter(), 
						  booknumber = ord(versekey.Book()),
						  bookabbrev = versekey.getBookAbbrev(),
						  bookname = versekey.getBookName(),
						  reference = reference,
			)	

					  
			body_dict.update(d)
			
			t = template
			if specialref == reference:
				t = specialtemplate

			verse = ""
			headings = self.get_headings(reference)

			for heading in headings:
				if not raw:
					heading = self.mod.RenderText(heading)

				heading_dict = dict(heading=heading)
				heading_dict.update(body_dict)
				
				verse += t.headings.safe_substitute(heading_dict)
			
			verse += t.body.safe_substitute(body_dict)
			#verse = self.ReplaceFootnote(verse)

			verses += verse
			verselist.increment(1)
			verses_left -= 1

		verses += template.footer.safe_substitute(d)
		return verses
	
	def get_headings(self, ref):
		"""Gets an array of the headings for the current verse. Must have just
		called RenderText on the verse you want headings for"""

		heading = SW.Buf("Heading")
		preverse = SW.Buf("Preverse")
		interverse = SW.Buf("Interverse")
		headings = []
		heading_types = [preverse, interverse]
		attrmap = self.mod.getEntryAttributesMap()#[SW.Buf("Heading")
		if heading in attrmap:
			h = attrmap[heading]
			for item in heading_types:
				if item in h:
					i = 0
					p = h[item]
					while True:
						i_buf = SW.Buf(str(i))
						if i_buf in p:
							headings.append(p[i_buf].c_str())
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
			if not self.ModuleExists(mod):
				return None
			mod = self.parent.get_module(mod)

		else:
			mod = self.mod

		vk = VK(passage)
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
		index = text.find(":")
		if(not index == -1):
			text = text[:index]
		return self.GetReference(text, specialref, specialtemplate, context,
				raw=raw)

	def get_rendertext(self):
		"""Return the text render function.

		This makes sure that plaintext modules render whitespace properly"""
		render_text = self.mod.RenderText

		if self.mod.getConfigEntry("SourceType") in (None, "Plaintext"):
			def render_text(*args):
				text = self.mod.RenderText(*args)
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

class Bible(Book):
	type = "Biblical Texts"


