import re
import string
import math
import json
import urllib

import wx
import wx.wc


import guiconfig
import config


from swlib.pysw import GetBestRange, SW, VerseList
from backend.bibleinterface import biblemgr
from backend.verse_template import SmartVerseTemplate
from util import osutils, classproperty
from util.configmgr import config_manager
from tooltip import tooltip_settings, TextTooltipConfig, BibleTooltipConfig, TooltipDisplayer
from gui.menu import MenuItem, Separator
from gui.htmlbase import convert_language
from gui import guiutil
import display_options
from util.debug import dprint, WARNING, TOOLTIP, MESSAGE
from protocols import protocol_handler
# XXX: This is just to force the protocol to be registered.
import gui.passage_tag
import events
import protocol_handlers

from gui import fonts

IN_POPUP = 1
IN_MENU = 2
IN_BOTH = IN_POPUP | IN_MENU

def process_html_for_module(module, text):
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
	allow_search = True
	has_startup_completed = False

	def __init__(self, parent, logical_parent=None):
		super(DisplayFrame, self).__init__(parent)

		self.logical_parent = logical_parent
		self.handle_links = True

	def DomContentLoaded(self, event):
		# By default, wxWebConnect will show the spinning busy cursor on startup
		# and leave it spinning until the mouse is moved.
		# This forces the cursor to change to the standard cursor after the
		# first display frame has been fully loaded.
		if not DisplayFrame.has_startup_completed:
			DisplayFrame.has_startup_completed = True
			guiconfig.mainfrm.SetCursor(wx.StockCursor(wx.CURSOR_ARROW))

		document = self.GetDOMDocument()
		for event_name, (handler, event_id) in self.custom_dom_event_listeners.iteritems():
			document.AddEventListener(event_name, self, event_id, True)

		self.dom_loaded = True
		for function, args, kwargs in self.events_to_call_on_document_load:
			function(self, *args, **kwargs)
		self.events_to_call_on_document_load = []

	def defer_call_till_document_loaded(self, function, *args, **kwargs):
		if self.dom_loaded:
			function(self, *args, **kwargs)
		else:
			print "Adding item to list of things to execute."
			self.events_to_call_on_document_load.append((function, args, kwargs))

	def setup(self):
		self.handle_links = True
		self.dom_loaded = False
		self.events_to_call_on_document_load = []
		self.custom_dom_event_listeners = {}
		self.custom_dom_event_id_handlers = {}
		self.custom_dom_event_id_counter = 999991
		
		self.current_target = None
		self.force_next_uri_to_open = False
		
		self.Bind(wx.wc.EVT_WEB_SHOWCONTEXTMENU, self.show_popup)
		
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
		self.add_custom_dom_event_listener('DropFiles', self.on_drop_files_from_javascript)

	def __del__(self):
		DisplayFrameManager.active_display_frames.remove(self)
	
	def add_custom_dom_event_listener(self, event_name, handler):
		if not self.custom_dom_event_listeners:
			self.Bind(wx.wc.EVT_WEB_DOMEVENT, self.DomEventReceived)

		event_id = self.custom_dom_event_id_counter 
		self.custom_dom_event_id_counter += 1
		self.custom_dom_event_listeners[event_name] = (handler, event_id)
		self.custom_dom_event_id_handlers[event_id] = handler
		
	def DomEventReceived(self, event):
		event_id = event.GetId()
		try:
			handler = self.custom_dom_event_id_handlers[event_id]
			handler()
		except KeyError:
			pass

	def MouseOut(self, event = None):
		if event: event.Skip()

		self.mouseout = True

	def MouseIn(self, event = None):
		if event: event.Skip()
	
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
				#find reference list
				reflist = bible.GetFootnoteData(module, passage, value, "refList")
				#it seems note may be as following - 
				#ESV: John.3.1.xref_i "See Luke 24:20"
				#treat as footnote then. not sure if this is intended behaviour
				#could lead to weird things
				if(not reflist):
					data = bible.GetFootnoteData(module, passage, value, "body")
					SetText(data)
				else:
					reflist = reflist.split("; ")
					tooltip_config = BibleTooltipConfig(reflist)


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

			refs = value.split("; ")
			tooltip_config = BibleTooltipConfig(refs)

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
				wx.CallAfter(guiconfig.mainfrm.dictionarytext.UpdateUI, value)
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
				wx.CallAfter(guiconfig.mainfrm.dictionarytext.UpdateUI, value)


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
				guiconfig.mainfrm.set_bible_ref(ref, events.LINK_CLICKED)

	@staticmethod
	def on_link_clicked_bible(frame, href, url):
		host = url.getHostName()
		
		# if we are a list of links, we don't care about being clicked on
		if not host: 
			return

		guiconfig.mainfrm.set_bible_ref(host, events.LINK_CLICKED)

	def on_char(self, event):
		if osutils.is_msw():
			self.force_alt_key_to_work_correctly(event)
		guiutil.dispatch_keypress(self.get_actions(), event)
	
	def force_alt_key_to_work_correctly(self, event):
		# Under MSW, the menu accelerators (e.g. Alt+F for the file menu) do
		# not work when a display frame has focus.
		# Therefore, if we detect any of these combinations we put focus on
		# the main frame.
		if event.Modifiers == wx.MOD_ALT:
			guiconfig.mainfrm.SetFocus()

	def get_menu_items(self, event=None):
		href = event.GetHref() if event else u""

		search_menu_item = ()
		if self.allow_search:
			search_menu_item = ((self.make_search_text(href), IN_POPUP),)

		menu_items = search_menu_item + (
			(self.make_lookup_text(href), IN_POPUP),
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
			[x for (x, where_shown) in self.get_menu_items(event) 
				if where_shown & IN_POPUP],
			is_popup=True)
		
		event_object.PopupMenu(menu, self.popup_position)

	def _get_text(self, lookup_text, href, is_search=False):
		def update_ui(event):
			text = self.SelectionToText()

			if not text and is_search:
				# only display text reference if 
				if href:
					match = (re.match(u'n?bible:([^#]*)(#.*)?', href) or
						re.match(
							u'passagestudy.jsp\?action=showRef&type=scripRef&'
							'value=([^&]*)&module=.*', href))
					if match:
						ref = SW.URL.decode(str(match.group(1))).c_str()
						text = GetBestRange(ref, userOutput=True)
						
					if text:
						event.SetText(lookup_text % text)
						return

			if (not text) and (href.startswith('strongs') or href.startswith('morph')):
				text = self.get_link_text_from_href(href)
								
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

	def get_link_text_from_href(self, href):
		return self.ExecuteScriptWithResult('encode_utf8(document.querySelector(\'a[href="%s"]\').textContent)' % href)

	def get_clicked_cell_text(self):
		return self.ExecuteScriptWithResult('window.right_click_word ? encode_utf8(window.right_click_word): ""')

	def make_lookup_text(self, href):
		update_ui = self._get_text(_("Look up %s in the dictionary"), href)

		def on_lookup_click():
			"""Lookup the selected text in the dictionary"""
			text = self.SelectionToText()
			if not text:
				text = self.get_clicked_cell_text()

			text = self.strip_text(text)
			guiconfig.mainfrm.dictionarytext.UpdateUI(text)

		assert hasattr(self, "mod"), self
		font = fonts.get_module_gui_font(self.mod, default_to_None=True)
		
		return MenuItem("Dictionary lookup", on_lookup_click, 
			update_ui=update_ui, font=font)


	def make_search_text(self, href):
		frame = self.get_frame_for_search()
		if frame.book == biblemgr.bible:
			search_text = _("Search for %s in the Bible")
		else:
			search_text = _("Search for %s in this book")
		update_ui = self._get_text(
			search_text,
			href,
			is_search=True)

		def on_search_click():
			"""Search for the selected word in the Bible"""
			strongs_number = None
			text = None
			if href:
				match = re.match(u'strongs://(Greek|Hebrew)/(\d+)(!\w+)?', href)
				if match:
					prefix, number, extra = match.group(1, 2, 3)
					strongs_number = "HG"[prefix=="Greek"] + number
					if extra:
						strongs_number += extra[1:]
			
					text = "strongs:" + strongs_number
				
				if not text:
					match = re.match(u'morph://(\w*)((:|%3A)[^/]+)/([\w-]+)', href)
					if match:
						module, value = match.group(1, 4)
						if module == "Greek": module = "Robinson"
						text = "morph:%s:%s" % (module, value)

				ref = None
				if not text:
					match = (re.match(u'n?bible:([^#]*)(#.*)?', href) or
						re.match(
							u'passagestudy.jsp\?action=showRef&type=scripRef&'
							'value=([^&]*)&module=.*', href))
					if match:
						ref = match.group(1)

				if ref:
					ref = SW.URL.decode(str(ref)).c_str()
					vl = VerseList(ref)
					first_ref = VerseList([vl[0]]).GetBestRange(userOutput=True)

					# only search on the first item or range				
					text = 'ref:"%s"' % first_ref

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

	def SetPage(self, page_content, include_stock_stylesheets=True):
		assert hasattr(self, "mod"), self

		self.OpenURI(protocol_handlers.FragmentHandler.register(page_content, self.mod, include_stock_stylesheets))

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

	def OpenURI(self, uri, flags=wx.wc.WEB_LOAD_NORMAL, post_data=None, grab_focus=False, force_uri_open=False):
		# default to not grab focus
		self.force_next_uri_to_open = force_uri_open
		super(DisplayFrame, self).OpenURI(uri, flags, post_data, grab_focus)

	def OnOpenURI(self, event):
		href = event.GetHref()
		dprint(WARNING, "Loading HREF", href)
		if href.startswith("bpbible") or self.force_next_uri_to_open:
			self.dom_loaded = False
			self.force_next_uri_to_open = False
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
	
	@defer_till_document_loaded
	def copyall(self):
		self.SelectAll()
		self.CopySelection()
		self.SelectNone()

	def on_drop_files_from_javascript(self):
		dropped_file_urls = json.loads(self.ExecuteScriptWithResult(
			'JSON.stringify(dropped_file_urls)'
		))
		# The string gets automatically turned into a Unicode by the JSON
		# reading functionality.  However, it is really UTF-8, so we have to
		# encode with cp1252 to recover the original UTF-8 string before
		# decoding it.
		filenames = [urllib.url2pathname(re.sub('^file:\/+', '', filename)).encode('cp1252').decode('utf8')
			for filename in dropped_file_urls
		]
		from install_manager.install_drop_target import ModuleDropTarget
		ModuleDropTarget.handle_dropped_files(filenames, guiconfig.mainfrm)

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
	
		
