import re
import string
import math

import wx
import wx.wc


import guiconfig
import config


from swlib.pysw import GetBestRange, SW, VerseList
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate
from util import osutils, classproperty
from util.configmgr import config_manager
from tooltip import tooltip_settings, TextTooltipConfig, BibleTooltipConfig, TooltipDisplayer
from gui.menu import MenuItem, Separator
from gui.htmlbase import convert_language, convert_lgs
from gui import guiutil
import display_options
from util.debug import dprint, WARNING, TOOLTIP, MESSAGE
from protocols import protocol_handler
# XXX: This is just to force the protocol to be registered.
import gui.passage_tag
from events import LINK_CLICKED
import protocol_handlers

from gui import fonts

IN_POPUP = 1
IN_MENU = 2
IN_BOTH = IN_POPUP | IN_MENU

def process_html_for_module(module, text):
	# process lgs individually for each block.
	# this stops lgs flowing on to the next block
	text = convert_lgs(text, width=30)

	language_code, (font, size, gui) = \
		fonts.get_font_params(module)

	text = convert_language(text, language_code)
		
	return '<span module="%s" lang="%s">%s</span>' % (module.Name(), language_code, text)

html_settings = config_manager.add_section("Html")
html_settings.add_item("zoom_level", 0, item_type=int)

# some magic zoom constants
zoom_levels = {-2: 0.75, 
			   -1: 0.83, 
			   	0: 1, 
				1: 1.2, 
				2: 1.44, 
				3: 1.73, 
				4: 2,
				5: 2.5,
				6: 3,
				7: 3.5
				}

class DisplayFrameManager(object):
	active_display_frames = []

	@classmethod
	def zoom(cls, direction):
		cls.set_zoom_level(html_settings["zoom_level"] + direction)

	@classmethod
	def reset_zoom_level(cls):
		cls.set_zoom_level(0)

	@classmethod
	def set_zoom_level(cls, zoom_level):
		# Make sure the zoom level is within bounds.
		html_settings["zoom_level"] = max(min(zoom_level, 7), -2)
		for displayframe in cls.active_display_frames:
			displayframe.SetTextZoom(cls.xulrunner_zoom_level)

	@classproperty
	def xulrunner_zoom_level(cls):
		return zoom_levels[html_settings["zoom_level"]]

# Decorator to manage functions that cannot be called while the document is
# loading.
def defer_till_document_loaded(function_to_decorate):
	def function(self, *args, **kwargs):
		self.defer_call_till_document_loaded(function_to_decorate, *args, **kwargs)

	return function

class DisplayFrame(TooltipDisplayer, wx.wc.WebControl):
	lg_width = 20
	do_convert_lgs = True

	def __init__(self, parent, logical_parent=None):
		super(DisplayFrame, self).__init__(parent)

		self.logical_parent = logical_parent
		self.handle_links = True

	def DomContentLoaded(self, event):
		document = self.GetDOMDocument()
		self.dom_loaded = True
		for function, args, kwargs in self.events_to_call_on_document_load:
			function(self, *args, **kwargs)
		self.events_to_call_on_document_load = []

	def defer_call_till_document_loaded(self, function, *args, **kwargs):
		if self.dom_loaded:
			print "DOM loaded, works fine."
			function(self, *args, **kwargs)
		else:
			print "Adding item to list of things to execute."
			self.events_to_call_on_document_load.append((function, args, kwargs))

	def setup(self):
		self.handle_links = True
		self.dom_loaded = False
		self.events_to_call_on_document_load = []
		
		self.current_target = None
		self.mouseout = False
		
		self.Bind(wx.wc.EVT_WEB_SHOWCONTEXTMENU, self.show_popup)
		
		self.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		self.Bind(wx.EVT_ENTER_WINDOW, self.MouseIn)
		self.Bind(wx.wc.EVT_WEB_OPENURI, self.OnOpenURI)
		self.Bind(wx.wc.EVT_WEB_DOMCONTENTLOADED, self.DomContentLoaded)
		self.Bind(wx.wc.EVT_WEB_MOUSEOVER, self.MouseOverEvent)
		self.Bind(wx.wc.EVT_WEB_MOUSEOUT, self.MouseOutEvent)
		self.Bind(wx.EVT_KEY_DOWN, self.on_char)
		self.DisableFavIconFetching()
		
		hover = protocol_handler.register_hover
		# TODO: move these out somewhere else
		hover("bible", self.on_hover_bible)
		hover("nbible", lambda *args, **kwargs:None)
		hover("", self.on_hover)
		click = protocol_handler.register_handler

		click("bible", self.on_link_clicked_bible)
		click("nbible", self.on_link_clicked_bible)

		click("", self.on_link_clicked)

		DisplayFrameManager.active_display_frames.append(self)
		self.SetTextZoom(DisplayFrameManager.xulrunner_zoom_level)

		super(DisplayFrame, self).setup()

	def __del__(self):
		DisplayFrameManager.active_display_frames.remove(self)
	
	#def KillFocus(self, event):
	#	self.tooltip.Stop()
	#	event.Skip()
		
	def MouseOut(self, event = None):
		if event: event.Skip()

		#if(self._tooltip is not None and self.tooltip.timer is not None and 
		#	self.tooltip.timer.IsRunning()):
		
		#	dprint(TOOLTIP, "Stopping on displayframe mouseout")
		#	self.tooltip.Stop()

		#self.current_target = None
		self.mouseout = True


	def GetViewStart(self):
		# XXX: Do better than this.
		return (0, 0)

	def MouseIn(self, event = None):
		if event: event.Skip()
	
		self.mouseout = False

		### children includes our own tooltip...
		exceptions = [item for item in self.tooltip.tooltip_children()]
		exceptions += [item for item in self.tooltip.tooltip_parents()]
		exceptions = [t for t in exceptions if t.IsShown()]

		guiconfig.mainfrm.hide_tooltips(exceptions=exceptions)

	def strip_text(self, word):
		return word.strip(string.whitespace + string.punctuation +
			u'\N{RIGHT DOUBLE QUOTATION MARK}' 
			u'\N{LEFT DOUBLE QUOTATION MARK}'
			u'\N{EM DASH}'
			u'\N{RIGHT SINGLE QUOTATION MARK}'
			u'\N{LEFT SINGLE QUOTATION MARK}'
		)

	def CellClicked(self, cell, x, y, event):
		if(self.select or event.Dragging()): 
			return

		if(event.ControlDown()):
			word = cell.ConvertToText(None)
			word = self.strip_text(word)
			if(word): 
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, word)
			return

		link = cell.GetLink()
		if link and self.handle_links: 
			self.LinkClicked(link, cell)

	def MouseOverEvent(self, event):
		event.Skip()
		self.current_target = None
		
		element = event.GetTargetNode()
		href = event.GetHref()
		if not href or not self.handle_links:
			return


		if guiconfig.mainfrm.lost_focus: return

		x, y = wx.GetMousePosition()
		self.current_target = href, wx.Rect(
			x, y, 0, 0
		), 4

		if self.current_target and self.tooltip.target and \
				self.tooltip.target == self.current_target[0]:
			return 

		
		protocol_handler.on_hover(self, href, element, x, y)

	@staticmethod
	def on_hover(frame, href, url, element, x, y):
		tooltip_config = TextTooltipConfig("", mod=frame.mod)
		def SetText(text):
			tooltip_config.text = text

		if url.getHostName() != "passagestudy.jsp":
			return
		action = url.getParameterValue("action")
		bible = biblemgr.bible
		dictionary = biblemgr.dictionary

		# set the tooltip's reference to this reference in case there is a
		# scripture note inside the note
		# e.g. first note in Matthew 2:1 in calvin's commentaries
		if not hasattr(frame, "reference"):
			dprint(WARNING, "Frame didn't have reference", frame)
			frame.reference = ""

		frame.tooltip.html.reference = frame.reference

		if action == "showStrongs":
			frame.tooltip.show_strongs_ref(frame, href, url, element, x, y)
			return

		elif action=="showMorph":
			type = url.getParameterValue("type") #Hebrew or greek
			types = type.split(":", 1)
			if types[0] not in ("robinson", "Greek"):
				tooltipdata = _("Don't know how to open this morphology type:")
				tooltipdata += "<br>%s" % type
			else:
				value = url.getParameterValue("value") #strongs number
				module = biblemgr.get_module("Robinson")
				if not value:
					return
				
				tooltip_config.mod = module
				if not module:
					tooltipdata = _("Module %s is not installed, so you "
					"cannot view details for this morphological code") % type
				else:
					tooltipdata = dictionary.GetReferenceFromMod(module, value)

			SetText(tooltipdata)


		elif(action=="showNote"):
			type = url.getParameterValue("type") #x or n
			value = url.getParameterValue("value") #number footnote in verse
			if((not type) or (not value)): 
				dprint(WARNING, "Not type or value in showNote", href)
				return
			module = biblemgr.get_module(url.getParameterValue("module"))
			passage = url.getParameterValue("passage")
			if not passage or not module:
				return

			tooltip_config.mod = module

			if type == "n":
				data = bible.GetFootnoteData(module, passage, value, "body")
				data = data or ""
				SetText(data)


			elif type == "x":
				#make this plain
				template = VerseTemplate(
					header="<a href='nbible:$internal_range'><b>$range</b></a><br>",
					body=(config.body % ''),
				)
				try:
					#no footnotes
					if tooltip_settings["plain_xrefs"]:
						biblemgr.temporary_state(biblemgr.plainstate)
					
					#apply template
					biblemgr.bible.templatelist.append(template)

					#find reference list
					reflist = bible.GetFootnoteData(module, passage, value, "refList")
					#it seems note may be as following - 
					#ESV: John.3.1.xref_i "See Luke 24:20"
					#treat as footnote then. not sure if this is intended behaviour
					#could lead to weird things
					data = ""
					if(not reflist):
						data = bible.GetFootnoteData(module, passage, value, "body")
					else:
						reflist = reflist.split("; ")
						# get refs - not from module as module is the module
						# the cross-reference is in - may be a
						# commentary, for example - use our primary bible
						verselist = bible.GetReferences(reflist)
						data += '<hr>'.join(
							process_html_for_module(bible.mod, ref)
							for ref in verselist
						)

					SetText(data)

				finally:
					#put it back how it was
					if tooltip_settings["plain_xrefs"]:
						biblemgr.restore_state()
					biblemgr.bible.templatelist.pop()


		elif action=="showRef":
			type = url.getParameterValue("type") 
			if type != "scripRef":
				dprint(WARNING, "unknown type for showRef", type, href)
				return
			value = url.getParameterValue("value") #passage
			module = biblemgr.get_module(url.getParameterValue("module"))
			if not module:
				module = biblemgr.bible.mod

			if not value:
				return

			tooltip_config.mod = module
			
			#make this plain
			#template = VerseTemplate(header = "$range<br>", 
			#body = '<font color = "blue"><small><sup>$versenumber</sup></small></font> $text')
			template = VerseTemplate(
				header="<a href='bible:$internal_range'><b>$range</b></a><br>", 
				body=u'<glink href="nbible:$internal_reference">'
					u'<small><sup>$versenumber</sup></small></glink> $text ')

			try:
				if tooltip_settings["plain_xrefs"]: 
					#no footnotes
					biblemgr.temporary_state(biblemgr.plainstate)
					#apply template
				biblemgr.bible.templatelist.append(template)

				value = value.split("; ")
				
				context = frame.reference
				
				# Gen books have references that are really tree keys...
				if not isinstance(context, basestring):
					context = "%s" % context

				
				#get refs
				refs = bible.GetReferencesFromMod(module, value, 
					context=context)

				data = '<hr>'.join(
					process_html_for_module(module, ref)
					for ref in refs
				)

				#set tooltip text
				SetText(data)

			finally:
				#put it back how it was
				if tooltip_settings["plain_xrefs"]:
					biblemgr.restore_state()
				biblemgr.bible.templatelist.pop()

		elif action == "showMultiRef":
			values = url.getParameterValue("values")
			if not values:
				return

			references = [
				url.getParameterValue("val%s" % value)
				for value in range(int(values))
			]
			tooltip_config = BibleTooltipConfig(references)

		elif action == "showImage":
			return
		else:
			dprint(WARNING, "Unknown action", action, href)
			return

		frame.show_tooltip(tooltip_config)
	
	@staticmethod
	def on_hover_bible(frame, href, url, element, x, y):
		screen_x, screen_y = wx.GetMousePosition()
	
		frame.tooltip.show_bible_refs(frame, href, url, screen_x, screen_y)

	def MouseOutEvent(self, event):
		event.Skip()
		if self.has_tooltip:
			self.tooltip.MouseOut(None)

		self.current_target = None

	def LinkClicked(self, link, cell):
		href = link.GetHref()

		protocol_handler.on_link_opened(self, href)

	@staticmethod
	def on_link_clicked(frame, href, url):
		host = url.getHostName()
		if host != "passagestudy.jsp":
			return
		action = url.getParameterValue("action")
		if action == "showStrongs":
			type = url.getParameterValue("type") #Hebrew or greek
			value = url.getParameterValue("value") #strongs number
			if not type or not value: 
				return
			#do lookup
			type = "Strongs"+type #as module is StrongsHebrew or StrongsGreek
			if biblemgr.dictionary.ModuleExists(type):
				guiconfig.mainfrm.set_module(type, biblemgr.dictionary)
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, value)
			return
		if action=="showMorph":
			type = url.getParameterValue("type") #Hebrew or greek
			value = url.getParameterValue("value") #strongs number
			if not type or not value: 
				return
			
			if type.split(":")[0] not in ("robinson", "Greek"):
				return

			#do lookup
			type = "Robinson"
			if biblemgr.dictionary.ModuleExists(type):
				guiconfig.mainfrm.set_module(type, biblemgr.dictionary)
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, value)


		if action=="showImage":
			value = url.getParameterValue("value") # path to image
			if not value:
				dprint(WARNING, "No URL value?", href)
				return
			else:
				assert value.startswith("file:")
				filepath = value[5:]
				dprint(MESSAGE, "Opening image", filepath)
				osutils.system_open_file(filepath)

		if action == "showRef":
			if url.getParameterValue("type") == "scripRef":
				ref = url.getParameterValue("value")
				guiconfig.mainfrm.set_bible_ref(ref, LINK_CLICKED)

	@staticmethod
	def on_link_clicked_bible(frame, href, url):
		host = url.getHostName()
		
		# if we are a list of links, we don't care about being clicked on
		if not host: 
			return

		guiconfig.mainfrm.set_bible_ref(host, LINK_CLICKED)

	def on_char(self, event):
		guiutil.dispatch_keypress(self.get_actions(), event)

	def get_menu_items(self):
		menu_items = (
			(self.make_search_text(), IN_POPUP),
			(self.make_lookup_text(), IN_POPUP),
			(Separator, IN_POPUP),
		
			(MenuItem(
				_("Select all"), 
				self.SelectAll,
				_("Select all the text in the frame")
			), IN_BOTH),
		)
		return menu_items

	def show_popup(self, event):
		event_object = event.EventObject
		
		self.popup_position = guiutil.get_mouse_pos(event_object)
		
		menu = guiconfig.mainfrm.make_menu(
			[x for (x, where_shown) in self.get_menu_items() 
				if where_shown & IN_POPUP],
			is_popup=True)
		
		#if osutils.is_gtk():
		#	self.popup_position = event_object.ScreenToClient(self.popup_position)

		event_object.PopupMenu(menu, self.popup_position)

	def get_popup_menu_items(self):
		return ((self.make_search_text(), self.make_lookup_text(), Separator) + 
			self.get_menu_items())

	def _get_text(self, lookup_text, is_search=False):
		def update_ui(event):
			text = self.SelectionToText()

			if not text and is_search:
				# only display text reference if 
				cell = self.FindCell(*self.popup_position)
				if cell:
					link = cell.GetLink()
					if link:
						match = re.match(u'n?bible:([^#]*)(#.*)?', 
							link.GetHref())
						if match:
							text = GetBestRange(match.group(1),
								userOutput=True)


						match = re.match(
							u'passagestudy.jsp\?action=showRef&type=scripRef&'
							'value=([^&]*)&module=.*', link.GetHref())
						if match:
							text = GetBestRange(
								SW.URL.decode(str(match.group(1))).c_str(),
								userOutput=True)
						
						if text:
							event.SetText(lookup_text % text)
							return
								
			if not text:
				text = self.get_clicked_cell_text()

			if text:
				text = self.strip_text(text)

			if not text:
				event.Enable(False)
				event.SetText(lookup_text % _("the selected word"))
				return

			event.Enable(True)
			item = "'%s'" % text
			if text.find(" ") != -1:
				item = _("the selected phrase")

			event.SetText(lookup_text % item)

		return update_ui

	def get_clicked_cell_text(self):
		cell = self.FindCell(*self.popup_position)
		if not cell: 
			return None

		return cell.ConvertToText(None)

	def make_lookup_text(self):
		update_ui = self._get_text(_("Look up %s in the dictionary"))

		def on_lookup_click():
			"""Lookup the selected text in the dictionary"""
			text = self.SelectionToText()
			if not text:
				text = self.get_clicked_cell_text()

			text = self.strip_text(text)
			guiconfig.mainfrm.UpdateDictionaryUI(text)

		assert hasattr(self, "mod"), self
		font = fonts.get_module_gui_font(self.mod, default_to_None=True)
		
		return MenuItem("Dictionary lookup", on_lookup_click, 
			update_ui=update_ui, font=font)


	def make_search_text(self):
		frame = self.get_frame_for_search()
		if frame.book == biblemgr.bible:
			search_text = _("Search for %s in the Bible")
		else:
			search_text = _("Search for %s in this book")
		update_ui = self._get_text(
			search_text,
			is_search=True)

		def on_search_click():
			"""Search for the selected word in the Bible"""
			cell = self.FindCell(*self.popup_position)
			link = cell.GetLink()
			strongs_number = None
			text = None
			if link:
				match = re.match(u'passagestudy.jsp\?action=showStrongs&type='
						  '(Greek|Hebrew)&value=(\d+)(!\w+)?', link.GetHref())
				if match:
					prefix, number, extra = match.group(1, 2, 3)
					strongs_number = "HG"[prefix=="Greek"] + number
					if extra:
						strongs_number += extra[1:]
			
					text = "strongs:" + strongs_number
				
				if not text:
					match = re.match(u'passagestudy.jsp\?action=showMorph&'
						'type=(\w*)((:|%3A)[^&]+)?&value=([\w-]+)',
						link.GetHref())
					if match:
						module, value = match.group(1, 4)
						if module == "Greek": module = "Robinson"
						text = "morph:%s:%s" % (module, value)

				if not text:
					match = re.match(u'n?bible:([^#]*)(#.*)?', link.GetHref())
					if match:
						vl = VerseList(match.group(1))	

						# only search on the first item or range
						text = 'ref:"%s"' % VerseList([vl[0]]).GetBestRange(
							userOutput=True)
				if not text:
					match = re.match(
						u'passagestudy.jsp\?action=showRef&type=scripRef&'
						'value=([^&]*)&module=.*', link.GetHref())
					if match:
						vl = VerseList(
							SW.URL.decode(str(match.group(1))).c_str()
						)

						# only search on the first item or range				
						text = 'ref:"%s"' % VerseList([vl[0]]).GetBestRange(
							userOutput=True)
							

			if not text:
				text = self.SelectionToText()
				if not text:
					text = self.get_clicked_cell_text()

				text = self.strip_text(text)

				# get rid of a few special characters
				text = re.sub(r'[\()"/:\-]', '', text)

				# if this is a phrase, put quotes around it.
				if " " in text:
					text = '"%s"' % text

			search_panel = frame.get_search_panel_for_frame()
			assert search_panel, "Search panel not found for %s" % self
			search_panel.search_and_show(text)

		assert hasattr(self, "mod"), self		
		font = fonts.get_module_gui_font(self.mod, default_to_None=True)
		return MenuItem("Search on word", on_search_click, 
			update_ui=update_ui, font=font)


	# XXX: These dummies are required to make all these menu items work correctly.
	# We should fix it so they are not needed.
	def FindCell(self, x,y):
		pass
	
	def get_actions(self):
		#actions = super(DisplayFrame, self).get_actions()
		# XXX: Have a standard collection of actions.
		actions = {}
		actions.update({
			wx.WXK_ESCAPE: guiconfig.mainfrm.hide_tooltips,
		})

		return actions

	def SelectionToText(self):
		return self.ExecuteScriptWithResult("window.getSelection();")

	def SetPage(self, page_content):
		assert hasattr(self, "mod"), self

		dprint(WARNING, "SetPage", self.__class__, len(page_content))
		self.OpenURI(protocol_handlers.FragmentHandler.register(page_content, self.mod))

	def Scroll(self, x, y):
		return

	def scroll_to_current(self):
		self.scroll_to_anchor("current")
	
	@defer_till_document_loaded
	def scroll_to_anchor(self, anchor):
		self.Execute('window.location.hash = "%s";' % anchor)
	
	def set_mod(self, value):
		self._mod = value
	
	def get_mod(self):
		if hasattr(self, "_mod"):
			return self._mod
		
		assert hasattr(self, "book"), self
		return self.book.mod
	
	mod = property(get_mod, set_mod)

	def get_frame_for_search(self):
		return guiconfig.mainfrm.bibletext

	def get_module_for_strongs_search(self, element):
		"""Gets the name of a particular module (with Strongs numbers) to
		use for the search, based on the current link that is being hovered
		over.

		If None is returned, then the current Bible will be used.
		"""
		return None

	def OpenURI(self, uri, flags=wx.wc.WEB_LOAD_NORMAL, post_data=None, grab_focus=False):
		# default to not grab focus
		super(DisplayFrame, self).OpenURI(uri, flags, post_data, grab_focus)

	def OnOpenURI(self, event):
		href = event.GetHref()
		dprint(WARNING, "Loading HREF", href)
		if href.startswith("bpbible"):
			self.dom_loaded = False
		else:
			protocol_handler.on_link_opened(self, href)
			event.Veto()

	def change_display_option(self, option_name):
		if not self.dom_loaded:
			return

		# It would theoretically be possible to do this DOM twiddling through
		# the WebConnect DOM API.  In practice, I haven't figured out how to.
		self.Execute("document.body.setAttribute('%s', %s);" %
				(option_name, display_options.get_js_option_value(option_name, quote_string=True)))

	def fonts_changed(self):
		if not self.dom_loaded:
			return

		self.Execute("force_stylesheet_reload('bpbible://content/fonts/');")

	@defer_till_document_loaded
	def size_intelligently(self, width, func, *args, **kwargs):
		max_height = kwargs.pop("max_height", 600)
		self.SetSize((width, 100))
		h = self.ExecuteScriptWithResult('window.getComputedStyle(document.body.parentNode, null).height')
		assert h.endswith("px")
		height = int(math.ceil(float(h[:-2])))
		if height > max_height: 
			height = max_height

		self.SetSize((width, height))

		func(width, height, *args, **kwargs)
		#return width, height
	
	@defer_till_document_loaded
	def copyall(self):
		self.SelectAll()
		self.CopySelection()

class DisplayFrameXRC(DisplayFrame):
	def __init__(self):
		pre = wx.wc.PreWebControl()
		self.PostCreate(pre)
		self.setup()


class AUIDisplayFrame(DisplayFrame):
	def restore_pane(self):
		self.maximize_pane(False)
	
	def maximize_pane(self, to=True):
		main = guiconfig.mainfrm
		pane = self.aui_pane
		maximized_pane = main.get_maximized_pane()
		if to:
			if not maximized_pane:
				main.maximize_pane(pane)
				
		else:
			if maximized_pane:
				main.restore_maximized_pane(pane)
		main.aui_mgr.Update()
		wx.CallAfter(main.update_all_aui_menu_items)

	def get_actions(self):
		actions = super(AUIDisplayFrame, self).get_actions()
		actions.update({
			(wx.WXK_F5, wx.MOD_CMD): self.restore_pane,
			(wx.WXK_F10, wx.MOD_CMD): self.maximize_pane,
		})		
		
		return actions

	def toggle_frame(self):
		pane = guiconfig.mainfrm.get_pane_for_frame(self)
		guiconfig.mainfrm.show_panel(pane.name, not pane.IsShown())
	
	def is_hidable(self):
		return self.aui_pane.HasCloseButton()

	@property
	def aui_pane(self):
		"""Gets the AUI pane for this frame."""
		return guiconfig.mainfrm.get_pane_for_frame(self)

	@property
	def title(self):
		return _(self.id)
	
	def get_window(self):
		return self
	
		
