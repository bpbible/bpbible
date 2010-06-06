import re
import string

import wx
from wx import html
import wx.wc


import guiconfig
import config



from swlib.pysw import GetBestRange, SW, VerseList
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate
from util import osutils
from tooltip import Tooltip, tooltip_settings, TextTooltipConfig, TooltipDisplayer
from gui import htmlbase
from gui.menu import MenuItem, Separator
from gui.htmlbase import HtmlSelectableWindow, convert_language, convert_lgs
from gui import guiutil
from util.debug import dprint, WARNING, TOOLTIP, MESSAGE
from protocols import protocol_handler
from events import LINK_CLICKED

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
		
	# now put it in the right font				
	text = '<fontarea basefont="%s" basesize="%s">%s</fontarea>' % (
		font, size, text
	)
	return text

class DummyHtmlBase(object):
	loading_a_page = False
	override_loading_a_page = False
	do_convert_lgs = True
	lg_width = 20

	def __init__(self, *args, **kwargs):
		super(DummyHtmlBase, self).__init__(*args, **kwargs)
		self._setup()
		

	def setup(self):
		self._setup()

	def _setup(self):
		self.top_left_cell = None
		self._do_scroll_to_current = True
		
		self.Bind(wx.EVT_SIZE, self.on_size)
		self.Bind(wx.EVT_IDLE, self.on_idle)
		
	
	def on_idle(self, event):
		pass
	
	def on_size(self, event):
		pass
		
	def ScrollNow(self, x, y, disabler=None):
		pass
		
	
	def SetPage(self, *args, **kwargs):
		# don't handle sizing during loading
		# or it may crash due to an invalid top left cell
		pass
		"""
		self.Unbind(wx.EVT_SIZE)
		HtmlBase.loading_a_page = True
	
		try:
			self.set_page(*args, **kwargs)
		finally:
			def finish():
				HtmlBase.loading_a_page = False
				if self:
					self.Bind(wx.EVT_SIZE, self.on_size)
				

			wx.CallAfter(finish)
		"""
		
		
	
	def CalcScrolledPosition(self, x, y):
		pass

	def SetBorders(self, _border):
		pass

	def set_page(self, text, raw=False, text_colour=None, body_colour=None):
		"""Set the page with the given text and colour. 
		
		Either or neither of text_colour and body_colour can be specified"""
		self.top_left_cell = None

		assert isinstance(text, basestring), text
	
		#text = text.replace("<small>", "<font size=-1>")
		#text = text.replace("</small>", "</font>")

		# now put things back (not sure if this is needed...)
		# text = string_util.htmlify_unicode(text)

		if body_colour is None or text_colour is None:
			body_colour, text_colour = guiconfig.get_window_colours()

		# we only want properly indented lgs in the main bibleframe
		if self.do_convert_lgs:
			text = convert_lgs(text, self.lg_width)

		text = convert_language(text, self.language_code)

		text = HTML_TEXT % (
			body_colour, 			
			self.font, 
			self.size, 
			text_colour, 
			text
		)

		if raw:
			text = text.replace("&", "&amp;")
			text = text.replace(">", "&gt;")
			text = text.replace("<", "&lt;")
			text = text.replace("\n", "<br>\n")
		else:
			# apos is valid xml, but not valid html.
			# Jub seems to use it, and it is valid osis, but the osishtmlhref
			# filters don't get rid of it
			text = text.replace("&apos;", "&#39;")

			# remove whitespace around indent block starts and ends so that
			# whitespace doesn't push them to a different line or just 
			# look nasty
			text = INDENT_WITH_WHITESPACE.sub(
				r"\1",
				text
			)
			

		# reset internal state of tag handlers
		for item in tag_handlers:
			item.clear()

		# If the font size has changed by a reasonable amount, line-height
		# will be wrong. So set the font now, so that when we really set the
		# page it will be correct
		super(HtmlBase, self).SetPage(
			HTML_TEXT % (
				body_colour, 			
				self.font, 
				self.size, 
				text_colour, 
				""
			)
		)

		return super(DummyHtmlBase, self).SetPage(text)
	
	def suppress_scrolling(self, function):
		"""Suppress any scrolling in this frame while the function is called."""
		self._do_scroll_to_current = False
		#y = self.GetViewStart()[1]
		function()
		#self.Scroll(-1, y)
		self._do_scroll_to_current = True
		
	def scroll_to_current(self):
		if not self._do_scroll_to_current:
			return

		self.scroll_to("current")

	def scroll_to(self, anchor):
		pass
		
	
	def Find(self, cell, linktext):
		"""Find anchor in hierarchy. 
		
		This is used instead of	html.HtmlCell.Find, which doesn't work as it
		expects a 'void *'"""

	def ScrollTo(self, anchor, c):
		pass

class DummyHtmlSelectableWindow(DummyHtmlBase):
	"""Handle the fact (among other things) that you can't get at the
	selection. This handles selection and copying
	
	Lots of this code comes from the wxhtml sources"""
	def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
	  		size=wx.DefaultSize, style = html.HW_DEFAULT_STYLE):
		#super(DummyHtmlSelectableWindow, self).__init__(parent,id,pos,size,style)  
		super(DummyHtmlSelectableWindow, self).__init__(parent)
		#self.buffer = wx.TextCtrl(self)
		#self.buffer.Hide()
		self.setup()

	def setup(self):
		# XXX: Change to handle the selection.
		self.m_selection = None
		self.Bind(wx.EVT_KEY_UP, self.on_char)

	def on_char(self, event):
		guiutil.dispatch_keypress(self.get_actions(), event)
		
	def OnCopy(self, event=None, with_links=True):
		pass

	#@html_source
	def SelectAll(self):
		pass

	def MouseMove(self, event):
		pass

	def MouseDown(self, event):
		pass


	def FindCell(self, x,y):
		pass

	def MouseUp(self, event):
		pass

	def CellMouseUp(self, cell, x, y, event):
		pass

	def PutMeIn(self):
		pass


	def Idle(self, event):
		pass

	#trap link clicks
	def OnLinkClicked(self, *args): pass

	"""
	def SetPage(self, text, raw=False, text_colour=None, body_colour=None):
		self.m_selection = None
		return super(DummyHtmlSelectableWindow, self).SetPage(text, raw=raw,		
		text_colour=text_colour, body_colour=body_colour)
	"""
				
WX_MOUSE_OVER_EVENT = 999991
WX_MOUSE_OUT_EVENT = 999992

class DisplayFrame(TooltipDisplayer, wx.wc.WebControl, DummyHtmlSelectableWindow):
	#def __init__(self, parent, style=html.HW_DEFAULT_STYLE,
	#		logical_parent=None):
	def __init__(self, parent, logical_parent=None, style=None):
		#super(DisplayFrame, self).__init__(parent, -1, style=wx.WANTS_CHARS) # XXX: What's the -1 for?
		super(DisplayFrame, self).__init__(parent)

		self.logical_parent = logical_parent
		self.handle_links = True
		
	def DomContentLoaded(self, event):
		document = self.GetDOMDocument()
		#document.AddEventListener("mouseover", self, WX_MOUSE_OVER_EVENT, True)
		#document.AddEventListener("mouseout", self, WX_MOUSE_OUT_EVENT, True)

	def DomEventReceived(self, event):
		pass
		event_id = event.GetId()
		if event_id not in (WX_MOUSE_OVER_EVENT, WX_MOUSE_OUT_EVENT):
			return

		if event_id == WX_MOUSE_OVER_EVENT:
			print "Mouse over"
		elif event_id == WX_MOUSE_OUT_EVENT:
			print "Mouse out"

	def setup(self):
		self.handle_links = True
		import displayframe
		self.html_type = displayframe.DisplayFrame

		self.current_target = None
		self.mouseout = False
		
		self.Bind(wx.wc.EVT_WEB_SHOWCONTEXTMENU, self.show_popup)
		
		self.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		self.Bind(wx.EVT_ENTER_WINDOW, self.MouseIn)
		self.Bind(wx.wc.EVT_WEB_OPENURI, self.OnOpenURI)
		self.Bind(wx.wc.EVT_WEB_DOMCONTENTLOADED, self.DomContentLoaded)
		self.Bind(wx.wc.EVT_WEB_DOMEVENT, self.DomEventReceived)
		self.Bind(wx.wc.EVT_WEB_MOUSEOVER, self.MouseOverEvent)
		self.Bind(wx.wc.EVT_WEB_MOUSEOUT, self.MouseOutEvent)
		
		hover = protocol_handler.register_hover
		# TODO: move these out somewhere else
		hover("bible", self.on_hover_bible)
		hover("nbible", lambda *args, **kwargs:None)
		hover("", self.on_hover)
		click = protocol_handler.register_handler

		click("bible", self.on_link_clicked_bible)
		click("nbible", self.on_link_clicked_bible)

		click("", self.on_link_clicked)


		super(DisplayFrame, self).setup()
	
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

		# Removed complex code to find the full extent of the link.
		# Something like this to get the right position to display the
		# tooltip should be created.
		"""
		parent = cell.Parent
		assert parent

		first = None
		last = None
		last_iterated = None
		in_block = False
		cell_found = False
		y_level = cell.GetPosY()

		child = parent.FirstChild
		while child:
			# skip over non-terminals, these will include font tags and colour
			# tags
			if child.IsTerminalCell():
				# check we are at the right link and y level
				#TODO: will all of a link be at the same level if sup or
				# <font> in link? Anyway, I'm assuming it is...
				if child.GetLink() and child.GetLink().GetHref() == href \
					and y_level == child.GetPosY(): 
					if not in_block:
						first = child
				
					in_block = True

					if cell.this == child.this:
						cell_found = True

				else:
					if cell_found:
						last = last_iterated
						break
					
					in_block = False

			last_iterated = child
			child = child.Next
		else:
			assert False, "Didn't find cell!?!"
		
		rect = wx.Rect(first.GetPosX(), first.GetPosY(), 
			last.GetPosX() - first.GetPosX() + last.GetWidth(),
			last.GetPosY() - first.GetPosY() + last.GetHeight()
		)

		xx, yy = 0, 0
		while parent:
			rect.Offset((
				parent.GetPosX(),
				parent.GetPosY()
			))
			parent = parent.Parent

		# now this value refers to somewhere on the scrolled page.
		# so we need to find the value on the client, then turn it to a screen
		# value...
		xx, yy = rect.TopLeft
		xx, yy = self.ClientToScreen(self.CalcScrolledPosition(xx, yy))
		self.current_target = href, wx.Rect(
			xx, yy, rect.GetWidth(), rect.GetHeight()
		), 4
		"""
		x, y = wx.GetMousePosition()
		self.current_target = href, wx.Rect(
			x, y, 0, 0
		), 4

		if self.current_target and self.tooltip.target and \
				self.tooltip.target == self.current_target[0]:
			return 

		
		protocol_handler.on_hover(self, href, x, y)

	@staticmethod
	def on_hover(frame, href, url, x, y):
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
			frame.tooltip.show_strongs_ref(frame, href, url, x, y)
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
				body=u'<glink href="nbible:$internal_reference">'
					u'<small><sup>$versenumber</sup></small></glink> $text ')
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

		elif action == "showImage":
			return
		else:
			dprint(WARNING, "Unknown action", action, href)
			return

		frame.show_tooltip(tooltip_config)
	
	@staticmethod
	def on_hover_bible(frame, href, url, x, y):
		#scrolled_values = frame.CalcScrolledPosition(x, y) 
		#screen_x, screen_y = frame.ClientToScreen(scrolled_values)
	
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

	@staticmethod
	def on_link_clicked_bible(frame, href, url):
		host = url.getHostName()
		
		# if we are a list of links, we don't care about being clicked on
		if not host: 
			return

		guiconfig.mainfrm.set_bible_ref(host, LINK_CLICKED)

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
			(MenuItem(
				_("Copy selection (with links)"), 
				self.copy_text_with_links,
				enabled=lambda:bool(self.m_selection),
				doc=_("Copy the selected text with links")
				
			), IN_BOTH),
			(MenuItem(
				_("Copy selection (without links)"), 
				self.copy_text_no_links,
				enabled=lambda:bool(self.m_selection),
				doc=_("Copy the selected text, removing all links")
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


	def copy_text_no_links(self):
		pass
		#self.OnCopy(with_links=False)

	def copy_text_with_links(self):
		pass
		#self.OnCopy(with_links=True)
	
	def get_actions(self):
		#actions = super(DisplayFrame, self).get_actions()
		# XXX: Have a standard collection of actions.
		# All there is in DummyHtmlSelectableWindow is copy.
		actions = {}
		actions.update({
			wx.WXK_ESCAPE: guiconfig.mainfrm.hide_tooltips,
		})

		return actions

	def SelectionToText(self):
		return ""

	def SetPage(self, *args, **kwargs):
		assert hasattr(self, "mod"), self

		self.language_code, (self.font, self.size, gui) = \
			fonts.get_font_params(self.mod)

		#super(DisplayFrame, self).SetPage(*args, **kwargs)
		# XXX: Hack.  Deprecated.
		if kwargs:
			print "SetPage: kwargs discarded:", kwargs
		dprint(WARNING, "SetPage", self.__class__, len(args[0]))
		self.SetContent("test://123.456.com", args[0]) # XXX: FixMe: Give a proper URL.

	"""
	def SetPageSource(self, *args):
		dprint(WARNING, "setPageSource begin")
		super(DisplayFrame, self).SetPageSource(*args)
		dprint(WARNING, "setPageSource end")
	"""

	def Scroll(self, x, y):
		return

	def scroll_to_current(self):
		# XXX: This doesn't actually seem to scroll the window.
		dprint(WARNING, "scroll_to_current", self.__class__)
		#raise Error('a')
		# XXX: This causes the application to crash on start up.
		#self.RunScript('window.location.hash = "current";')
	
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

	def OnOpenURI(self, event):
		dprint(WARNING, "Loading HREF", event.GetHref())
		if event.GetHref().startswith('test'):
			return
		protocol_handler.on_link_opened(self, event.GetHref())
		event.Veto()

class DisplayFrameXRC(DisplayFrame):
	def __init__(self):
		pre = html.PreHtmlWindow()
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
	
		
