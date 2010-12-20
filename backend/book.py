import re
import passage_list
from swlib.pysw import VK, SW, GetBestRange, GetVerseStr, TOP, process_digits
from swlib import pysw
from backend.verse_template import VerseTemplate, SmartBody
from backend import osisparser
from util import observerlist
from util import classproperty
from util.debug import dprint, WARNING, ERROR
from util.unicode import to_str, to_unicode
import cgi
import os
import display_options

import config

#ERR_OK = '\x00'
class FileSaveException(Exception):
	pass

class Book(object):
	is_verse_keyed = False
	is_dictionary = False
	is_genbook = False
	chapter_view = False
	type = None
	category = None
	categories_to_exclude = ()
	def __init__(self, parent, version = ""):
		self.parent = parent
		self.mod = None
		self.observers = observerlist.ObserverList()
		self.cleanup_module = observerlist.ObserverList()
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
				if (mod.Type() == self.type or self.type is None) and
				(not self.category or (self.category and mod.getConfigEntry("Category") == self.category)) and
				mod.getConfigEntry("Category") not in self.categories_to_exclude], 
				key=lambda name:name.lower())
	
	def GetModules(self):
		return sorted([mod for name, mod in self.parent.modules.iteritems()
				if (mod.Type() == self.type or self.type is None) and
				(not self.category or (self.category and mod.getConfigEntry("Category") == self.category)) and
				mod.getConfigEntry("Category") not in self.categories_to_exclude], 
				key = lambda mod: mod.Name().lower())
	
	@staticmethod
	def get_template_options():
		items = {
			"$":			_("A $ sign"), 
			"range":		_("The range of verses"), 
			"version":		_("The version this is taken from"),
			"description":	_("A description of the version"),
		}

		body_items = {			
			"text":			_("The text of a verse"),
			"versenumber":	_("The verse number"),
			"reference": 	_("The reference for each verse"),
			"bookname":		_("The name of the current book"),
			"bookabbrev":	_("A shorter abbreviation of the book name"),
			"chapternumber":_("The number of the chapter in the book")
		}

		heading_items = {
			"heading":		_("The text of the heading")
		}

		body_items.update(items)
		heading_items.update(body_items)

		return dict(body=body_items, headings=heading_items, 
					header=items, footer=items)

	
	def GetReference(self, ref, specialref="",
			specialtemplate=None, context="", max_verses=177, raw=False,
			stripped=False, template=None, display_tags=None,
			exclude_topic_tag=None, end_ref=None, headings=False,
			verselist=None, remove_extra_whitespace=False):
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

		raw = raw or display_options.options["raw"]
		
		if template is None and self.templatelist:
			template = self.templatelist[-1]
		if context:
			lastverse = context
		else:
			lastverse = ""

		if display_tags is None:
			# if we don't have tags in, don't calculate them as it can be
			# expensive
			if "$tags" not in template.body.template:
				display_tags = False
			else:
				display_tags = passage_list.settings.display_tags
	
		assert not (verselist and end_ref), \
			"No end ref with a listkey!!!"

		if end_ref:
			ref += " - " + end_ref

		old_headings = self.vk.Headings(headings)

		if not verselist:
			verselist = self.vk.ParseVerseList(to_str(ref), to_str(lastverse), True)

		# if they pass in a verselist, they can also pass in the ref they
		# would like to go along with it. This can be useful if it also
		# includes headings that shouldn't be seen
		rangetext = GetBestRange(ref, 
			userInput=False, userOutput=True, headings=headings)

		internal_rangetext = GetBestRange(ref, headings=headings)
			
		if rangetext == "":
			self.vk.Headings(old_headings)
			#if invalid reference, return empty string
			return u""
			
		
		if specialref:
			specialref = GetVerseStr(specialref)
		
		description = to_unicode(self.mod.Description(), self.mod)
		d = dict(range=rangetext, 
				 internal_range=internal_rangetext,
				 version=self.mod.Name(), 
				 description=description)

		text = template.header.safe_substitute(d)
		verses = []
		
		
		for body_dict, headings in self.GetReference_yield(
			verselist, max_verses, raw, stripped,
			exclude_topic_tag=exclude_topic_tag,
			display_tags=display_tags,
		):
			# if we have exceeded the verse limit, body_dict will be None
			if body_dict is None:
				verses.append(config.MAX_VERSES_EXCEEDED() % max_verses)
				break

			body_dict.update(d)
			
			t = template

			if specialref == body_dict["internal_reference"]:
				t = specialtemplate

			verse = t.preverse.safe_substitute(body_dict)

			for heading_dict in headings:
				verse += t.headings.safe_substitute(heading_dict)
			
			verse += t.body.safe_substitute(body_dict)

			verses.append(verse)
		
		self.vk.Headings(old_headings)

		text += template.finalize(u''.join(verses))
		text += self.end_of_render
		text += template.footer.safe_substitute(d)
		if remove_extra_whitespace:
			text = SmartBody.incl_whitespace_end.sub(u'', text)
		return text
		
			
	def GetReference_yield(self, verselist, max_verses=177, 
			raw=False, stripped=False, module=None, exclude_topic_tag=None,
			display_tags=True, skip_linked_verses=True):
		"""GetReference_yield: 
			yield the body dictionary and headings dictinoary
			for each reference.

		Preconditions:
			one of module or self.mod is not None
			verselist is valid"""
		#only for bible keyed books
		verselist.setPosition(TOP)
		verselist.Persist(1)
		u_vk = pysw.UserVK()
		u_vk.Headings(1)
		versekey = SW.VerseKey()
		versekey.Headings(1)
		mod = module or self.mod
		old_mod_skiplinks = mod.getSkipConsecutiveLinks()
		mod.setSkipConsecutiveLinks(True)
		mod.SetKey(verselist)
		verses_left = max_verses

		ERR_OK = chr(0)
		render_text, render_start, render_end = self.get_rendertext(mod)
		if render_start: render_start()

		try:
			incrementer = mod if skip_linked_verses else verselist
			while incrementer.Error() == ERR_OK:
				if verses_left == 0:
					yield None, None
					break
				
				if not skip_linked_verses:
					mod.SetKey(verselist)
				key = mod.getKey()
				#versekey = VK.castTo(key)
				versekey.setText(key.getText())
				#if(self.headings):
				#	versekey.Headings(1)
				osisRef = versekey.getOSISRef()
				internal_reference = versekey.getText()
				
				rawentry = mod.getRawEntryBuf()
				if skip_linked_verses and not rawentry.length():
					# don't include empty text; typically this may be at the
					# start of the chapter or something...
					incrementer.increment(1)
					continue

				start_verse = end_verse = versekey.Verse()
				
				# a patch adds isLinked, not in SWORD trunk yet
				# if not there, we will only see the first number
				if hasattr(mod, "isLinked"):
					# look forwards and backwards to see what the linked verse
					# number is (e.g. 3-5). Note: currently this won't cross
					# chapter boundaries
					vk = versekey.clone()
					vk = versekey.castTo(vk)
					vk.thisown=True
					vk.Headings(0)
					while(vk.Error() == '\x00' 
						and vk.Chapter() == versekey.Chapter() 
						and mod.isLinked(vk, versekey)):
						end_verse = vk.Verse()
						vk.increment(1)
				
					vk.copyFrom(versekey)
					vk.Headings(0)

					# hopefully we won't see anything backwards, but it is
					# possible (i.e. if we start in the middle of a linked
					# verse
					while(vk.Error() == '\x00'
						and vk.Chapter() == versekey.Chapter() 
						and mod.isLinked(vk, versekey)):				
						start_verse = vk.Verse()

						vk.decrement(1)
				
				if start_verse == end_verse:
					verse = "%d" % start_verse
				else:
					verse = "%d-%d" % (start_verse, end_verse)
				
				u_vk.setText(internal_reference)				
				if internal_reference.endswith(":0"):
					if start_verse != end_verse:
						print "WARNING: unhandled linked verse with verse 0"
						
					if versekey.Chapter() == 0:
						reference = u_vk.getBookName()
					else:
						reference = u_vk.get_book_chapter()

				else:
					reference = u_vk.get_book_chapter()
					reference += ":" + verse
					
				body_dict = dict(
					# text comes later
					versenumber = process_digits(verse,
						userOutput=True), 
					chapternumber = process_digits(
						str(versekey.Chapter()),
						userOutput=True),
					booknumber = ord(versekey.Book()),
					bookabbrev = versekey.getBookAbbrev(),
					bookname = versekey.getBookName(),
					reference = reference,
					internal_reference = internal_reference,
					osisRef = osisRef,
				)	
				
				# usually RenderText flushes this out, but we haven't called
				# that yet - but we definitely don't want extraneous headings
				mod.getEntryAttributesMap().clear()

				# we want to do our pre-verse content first, but we can't
				# without running it through the optionFilter first.
				# we'll then have to run it through again after, otherwise our
				# entryattributes may go walkabout
				if raw: rawentry_str = rawentry.c_str()
				mod.optionFilter(rawentry, versekey)
				if raw: option_filtered = rawentry.c_str()
				
				headings = self.get_headings(internal_reference, mod)
				#versekey = VK.castTo(key)
				heading_dicts = []
				raw_headings = []
				for heading, canonical in headings:
					# the new-style pre-verse content lives wrapped up in
					# <div>'s - it will contain the <title>, but the div will
					# be stripped out.
					# the old-style pre-verse content lives in <title>'s,
					# which will also be stripped out. Unfortunately, it isn't
					# that easy to tell whether it did have a title, so we
					# employ a heuristic - if it starts with an <, it is a new
					# one...
					nh = heading.startswith("<")
					if stripped:
						heading = mod.StripText(heading).decode(
							"utf8",
							"replace"
						)
					else:
						heading = render_text(heading).decode("utf8", "replace")

					if not nh:
						heading = '<h2 class="heading" canonical="%s">%s</h2>\n' % (canonical, heading)

					if raw:
						raw_headings.append(heading)
					heading_dict = dict(heading=heading, canonical=canonical)
					heading_dict.update(body_dict)
					heading_dicts.append(heading_dict)
					



				
				if stripped:
					text = mod.StripText(rawentry.c_str(), rawentry.length()).decode("utf-8", "replace")			

				else:
					# we can't use rawentry due to a static local buffer in
					# swmodule.c; breaks gospel harmonies
					text = (render_text(#rawentry.c_str(), rawentry.length()
									   ).decode("utf8", "replace"))
				
				# get our actual text
				if raw:
					text = self.process_raw(rawentry_str, text, versekey, mod,
						raw_headings, option_filtered)

				user_comments = self.get_user_comments(osisRef, versekey)

				# XXX: This needs to be done better than this.  Move into
				# subclass somehow.
				if isinstance(self, Bible) and display_tags:
					tags = self.insert_tags(osisRef, versekey, exclude_topic_tag)
				else:
					tags = ""
				
				body_dict.update(dict(text=text,
									  tags=tags,
									  usercomments=user_comments))

						  
				yield body_dict, heading_dicts

				incrementer.increment(1)
				verses_left -= 1

		finally:
			mod.setKey(SW.Key())
			mod.setSkipConsecutiveLinks(old_mod_skiplinks)
		
		self.end_of_render = ""
		if render_end:
			self.end_of_render = render_end()

	def get_user_comments(self, osis_ref, verse_key):
		if not isinstance(self, Bible):
			return u""

		manager = passage_list.get_primary_passage_list_manager()

		comments = u"".join(
			self.get_user_comment_div(passage_entry)
			for passage_entry in manager.get_all_passage_entries_for_verse(verse_key)
			if (self.get_tag_type_to_show(passage_entry) == "usercomment")
		)
		return u'<span class="usercomment_container" osisRef="%s">%s</span>' % (osis_ref, comments)

	def get_user_comment_div(self, passage):
		passage_id = passage.get_id()
		return '<a class="usercomment" href="usercomment://%(passage_id)d" passageEntryId="%(passage_id)d"><sup>&dagger;</sup></a>' % locals()
	
	def insert_tags(self, osis_ref, verse_key, exclude_topic_tag):
		"""Generates and returns all the passage tags for the given verse."""
		manager = passage_list.get_primary_passage_list_manager()
		passage_tags = "".join(
			self.get_passage_topic_div(passage)
			for passage in manager.get_all_passage_entries_for_verse(verse_key)
			if (self.get_tag_type_to_show(passage, exclude_topic_tag) == "passage_tag")
		)
		return u'<span class="passage_tag_container" osisRef="%s">%s</span>' % (osis_ref, passage_tags)

	def get_tag_type_to_show(self, passage, exclude_topic_tag=None):
		topic = passage.parent
		if (topic is not None
				and topic.parent is not None
				and topic is not exclude_topic_tag):
			if topic.can_display_tag:
				return "passage_tag"
			elif topic is passage_list.get_primary_passage_list_manager().comments_special_topic:
				return "usercomment"

		return None

	def get_passage_topic_div(self, passage):
		from gui import passage_tag
		topic_text = " > ".join(passage.parent.topic_trail)
		look, colour = passage.parent.resolve_tag_look()
		look_scheme, look_white_text, border = passage_tag.looks[look]
		colour_id, colour_white_text, default_look = passage_tag.colours[colour]
		white_text = look_white_text and colour_white_text
		_rgbSelectOuter,_rgbSelectInner,_rgbSelectTop, _rgbSelectBottom = passage_tag.get_colours(colour_id, look_scheme)
		border_radius_style = "-moz-border-radius: %dpx;" % border
		outer_border_style = "border-color: rgb(%d, %d, %d);" % _rgbSelectOuter.Get()
		inner_border_style = "border-color: rgb(%d, %d, %d);" % _rgbSelectInner.Get()

		# Only use gradients if the colours are different.
		if _rgbSelectTop == _rgbSelectBottom:
			passage_tag_style = "background-color: rgb(%d, %d, %d);" % _rgbSelectTop.Get()
			# We get weird artefacts if all the divs are the same colour and we
			# apply rounded corners to them, so we only apply to the outmost one.
			outer_border_style += border_radius_style
			border_radius_style = ""
		else:
			passage_tag_style = "background-image: -moz-linear-gradient(top center, rgb(%d, %d, %d) 20%%, rgb(%d, %d, %d) 80%%);" % (_rgbSelectTop.Get() + _rgbSelectBottom.Get())

		if white_text:
			passage_tag_style += "color:white;"

		passage_tag_style += border_radius_style
		outer_border_style += border_radius_style
		inner_border_style += border_radius_style

		topic_id = passage.parent.get_id()
		passage_id = passage.get_id()

		return """
			<a class="passage_tag" href="passagetag://passage/%(topic_id)d/%(passage_id)d" passageEntryId="%(passage_id)d">
				<div style="%(outer_border_style)s">
					<div style="%(inner_border_style)s">
						<div style="%(passage_tag_style)s">%(topic_text)s</div>
					</div>
				</div>
			</a> &nbsp;
		""" % locals()
	
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
			if not isinstance(mod, SW.Module):
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
		return mod.RenderText(data).decode("utf8", "replace")


	def GetReferenceFromMod(self, mod, ref, max_verses = -1):
		oldmod = self.mod
		if not self.SetModule(mod, notify=False): return None
		try:
			verses = self.GetReference(ref, max_verses=max_verses)
		finally:
			self.SetModule(oldmod, notify=False)

		return verses


	def GetReferencesFromMod(self, mod, ref, context="", max_verses=-1):
		oldmod = self.mod
		if not self.SetModule(mod, notify=False): return None
		
		try:
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

			# include introductions - book introduction if necessary
			ref = "%s %s" % (book, chapter)
			text = "%s %s:0-%s %s" % (book, chapter, book, chapter)
			vk = SW.VerseKey()
			vk.Headings(1)
			list = vk.ParseVerseList(text, "", True)
			if chapter == "1":
				vk.setText("%s 0:0" % book)
				list.add(vk)
				#text = "%s 0:0-%s %s" % (book, book, chapter)
			
				if book == "Genesis":
					vk.Testament(0)
					list.add(vk)
					vk.Testament(1)
					list.add(vk)

				elif book == "Matthew":
					# set it to 0 first so that we come back to the testament
					# heading
					vk.Testament(0)
					vk.Testament(2)
					list.add(vk)

				list.sort()

		else:
			dprint(ERROR, "Couldn't parse verse text", text)
			return ""

		return self.GetReference(ref, specialref, specialtemplate, context,
				raw=raw, headings=True, verselist=list)

	def get_rendertext(self, mod=None):
		"""Return the text render function.

		This makes sure that plaintext modules render whitespace properly"""
		module = mod or self.mod
		render_text = module.RenderText

		start = finish = None
		if module.getConfigEntry("SourceType") in (None, "Plaintext"):
			def render_text(*args):
				text = module.RenderText(*args)
				text = cgi.escape(text)
				return '<span class="plaintext">%s</span>' % text

		else:
			if ord(module.Markup()) == SW.FMT_OSIS:
				start = osisparser.p.block_start
				finish = osisparser.p.block_end


		return render_text, start, finish
	
	def has_feature(self, feature, module=None):
		if module is not None:
			oldmod = self.mod			
			try:
				self.SetModule(module, notify=False)
				return self.has_feature(feature)
			finally:
				self.SetModule(oldmod, notify=False)
			
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
	
	def get_cipher_code(self, mod):
		"""Return the cipher key for the module.
		This will be empty if locked, non-empty if unlocked and None if not
		enciphered"""
		return mod.getConfigEntry("CipherKey")

	def unlock(self, mod, key):
		assert self.get_cipher_code(mod) != None
		cm = mod.getConfigMap()
		cm[SW.Buf("CipherKey")] = SW.Buf(key)

		mgr = self.get_mgr(mod)
		mgr.setCipherKey(mod.Name(), key)

		conf = self.get_config(mod)
		conf.set(mod.Name(), "CipherKey", key)
		conf.Save()

		# send a refresh through for this book
		# TODO: do this better
		self.observers(self.mod)
		
		conf = self.get_config(mod)
		if conf.get(mod.Name(), "CipherKey") != key:
			raise FileSaveException(
				_("Couldn't save cipher key. You will have to set it again when you restart"))

		
	def get_mgr(self, mod):
		for path, mgr, modules in self.parent.mgrs:
			if mod in [m for name, m in modules]:
				return mgr

		return None
	
	def get_config(self, mod):
		pp = mod.getConfigEntry("PrefixPath")
		pp += "mods.d/%s.conf" % mod.Name().lower()
		
		# make sure it exists
		os.stat(pp)
		
		return SW.Config(pp)
	
	def process_raw(self, text, rendered_text, key, module, 
		headings=(), option_filtered=""):
		kt = key.getOSISRefRangeText() or key.getText()
		kt = to_unicode(kt, module)
		if headings:
			headings = "<ul class='raw-headings'>%s</ul>" % (
				'\n'.join("<li>%s</li>" % cgi.escape(heading) for heading in headings))
		else:
			headings = ""

		if option_filtered:
			option_filtered = "<pre class='raw-option-filtered'>%s</pre>" % cgi.escape(option_filtered.decode("utf-8", "replace"))
		return u"""
%s
<div class='debug-raw-details' key='%s'>
	<pre class='raw-rendered'>%s</pre>
	%s
	<pre class='raw'>%s</pre>
	%s
</div>""" % (rendered_text, cgi.escape(kt), cgi.escape(rendered_text), headings, cgi.escape(text.decode("utf-8", "replace")), option_filtered)
				
class Commentary(Book):
	type = "Commentaries"
	is_verse_keyed = True

	@classproperty
	def noun(cls):
		return _("commentary")


class Bible(Book):
	type = "Biblical Texts"
	is_verse_keyed = True
	chapter_view = True

	@classproperty
	def noun(cls):
		return _("Bible")


