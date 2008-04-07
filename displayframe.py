import re
import string

import wx
from wx import html


import guiconfig
import config



from backend.bibleinterface import biblemgr
from util import util
from util import osutils
from tooltip import Tooltip, tooltip_settings
from gui import htmlbase
from gui.menu import MenuItem, Separator
from gui.htmlbase import HtmlSelectableWindow
from gui import guiutil
from util.debug import dprint, WARNING, TOOLTIP
from protocols import protocol_handler
from events import LINK_CLICKED

IN_POPUP = 1
IN_MENU = 2
IN_BOTH = IN_POPUP | IN_MENU


class DisplayFrame(HtmlSelectableWindow):
	def __init__(self, parent, style=html.HW_DEFAULT_STYLE,
			logical_parent=None):
		super(DisplayFrame, self).__init__(parent, style=style)
		self.logical_parent = logical_parent

	def setup(self):
		if not hasattr(self, "logical_parent"):
			self.logical_parent = None
		self._tooltip = None
		self.current_target = None
		self.mouseout = False
		
		self.Bind(wx.EVT_CONTEXT_MENU, self.show_popup)
		self.Bind(wx.EVT_RIGHT_UP, self.show_popup)
		
		self.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		self.Bind(wx.EVT_ENTER_WINDOW, self.MouseIn)
		
		hover = protocol_handler.register_hover
		hover("bible", self.on_hover_bible)
		hover("nbible", lambda *args, **kwargs:None)
		hover("", self.on_hover)
		click = protocol_handler.register_handler

		click("bible", self.on_link_clicked_bible)
		click("nbible", self.on_link_clicked_bible)

		click("", self.on_link_clicked)


		super(DisplayFrame, self).setup()
	
	@property
	def tooltip(self):
		if not self._tooltip:
			self._tooltip = Tooltip(guiutil.toplevel_parent(self), 
				style=wx.NO_BORDER,
				html_type=DisplayFrame, logical_parent=self)
			#self.Bind(wx.EVT_KILL_FOCUS, self.KillFocus)
			
			guiconfig.mainfrm.add_toplevel(self._tooltip)

		return self._tooltip
		
	#def KillFocus(self, event):
	#	self.tooltip.Stop()
	#	event.Skip()
		
	def MouseOut(self, event = None):
		if(self._tooltip is not None and self.tooltip.timer is not None and 
			self.tooltip.timer.IsRunning()):
		
			self.tooltip.Stop()

		#self.current_target = None
		self.mouseout = True


	def MouseIn(self, event = None):
		self.mouseout = False
		if self._tooltip:
			exceptions = [self._tooltip]
		else:
			exceptions = []
			
		item = self
		while item.logical_parent:
			item = item.logical_parent
			if item._tooltip:
				exceptions.append(item._tooltip)

			
		guiconfig.mainfrm.hide_tooltips(exceptions=exceptions)

	def strip_text(self, word):
		word = util.ReplaceUnicode(word)
		
		return word.strip(string.whitespace + string.punctuation)

	def CellClicked(self, cell, x, y, event):
		if(self.select or event.Dragging()): 
			return

		if(event.ControlDown()):
			word = cell.ConvertToText(None)
			#word = util.ReplaceUnicode(word)
			word = self.strip_text(word)
			if(word): 
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, word)
			return

		link = cell.GetLink()
		if(link): 
			self.LinkClicked(link, cell)

	def OnCellMouseEnter(self, cell, x, y):
		self.current_target = None
		
		if cell.GetLink() is None:
			return


		if guiconfig.mainfrm.lost_focus: return

		link = cell.GetLink()
		href = link.GetHref()
		self.current_target = href

		if self.tooltip.target == self.current_target:
			return 

		
		protocol_handler.on_hover(self, href, x, y)

	@staticmethod
	def on_hover(frame, href, url, x, y):
		def SetText(data):
			#set tooltip text
			if(data.endswith("<hr>")):
				data = data[:-4]
			frame.tooltip.SetText(data)


		if url.getHostName() != "passagestudy.jsp":
			return
		action = url.getParameterValue("action")
		bible = biblemgr.bible
		dictionary = biblemgr.dictionary

		if action == "showStrongs":
			type = url.getParameterValue("type") #Hebrew or greek
			value = url.getParameterValue("value") #strongs number
			if not type or not value: 
				return
			#do lookup
			type = "Strongs"+type #as module is StrongsHebrew
			tooltipdata = dictionary.GetReferenceFromMod(type, value)
			if tooltipdata is None:
				tooltipdata = ("Module %s is not installed, so you cannot view"
				"details for this strong's number" %type)

			SetText(tooltipdata)

		elif action=="showMorph":
			type = url.getParameterValue("type") #Hebrew or greek
			types = type.split(":", 1)
			if types[0] != "robinson":
				tooltipdata = ("Don't know how to open this morphology type:"
					"<br>%s" % type)
			else:
				value = url.getParameterValue("value") #strongs number
				if not type or not value: 
					return

				#do lookup
				type = "Robinson" 
				tooltipdata = dictionary.GetReferenceFromMod(type, value)
				if tooltipdata is None:
					tooltipdata = ("Module %s is not installed, so you cannot "
					"view details for this morphological code" %type)

			SetText(tooltipdata)


		elif(action=="showNote"):
			type = url.getParameterValue("type") #x or n
			value = url.getParameterValue("value") #number footnote in verse
			if((not type) or (not value)): 
				dprint(WARNING, "Not type or value in showNote", href)
				return
			module = url.getParameterValue("module")
			passage = url.getParameterValue("passage")
			if not passage: 
				return

			if type == "n":
				data = bible.GetFootnoteData(module, passage, value, "body")
				SetText(data)

			elif type == "x":
				#make this plain
				template = util.VerseTemplate(header="<a href='nbible:$range'>"
				"<b>$range</b></a><br>", 
				body = "<font color = 'blue'><sup><small>$versenumber"
				"</small></sup></font> $text", footer = "<hr>")
				try:
					#no footnotes
					if tooltip_settings["plain_xrefs"]:
						biblemgr.temporary_state(biblemgr.plainstate)
					
					#apply template
					biblemgr.bible.templatelist.push(template)

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
						#get refs
						verselist = bible.GetReferencesFromMod(module, reflist)
						data += ''.join(verselist)

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
			if not value: 
				return

			module = url.getParameterValue("module")
			#make this plain
			#template = VerseTemplate(header = "$range<br>", 
			#body = '<font color = "blue"><small><sup>$versenumber</sup></small></font> $text')
			template = util.VerseTemplate(
				header="<a href='bible:$range'><b>$range</b></a><br>", 
				body = "<font color = 'blue'><sup><small>$versenumber"
				"</small></sup></font> $text", 
				footer = "<hr>"
			)

			try:
				if tooltip_settings["plain_xrefs"]: 
					#no footnotes
					biblemgr.temporary_state(biblemgr.plainstate)
					#apply template
				biblemgr.bible.templatelist.push(template)

				value = value.split("; ")

				#get refs
				refs = bible.GetReferencesFromMod(module, value, 
					context = str(frame.reference))

				data = "".join(refs)

				#set tooltip text
				SetText(data)

			finally:
				#put it back how it was
				if tooltip_settings["plain_xrefs"]:
					biblemgr.restore_state()
				biblemgr.bible.templatelist.pop()

		else:
			dprint(WARNING, "Unknown action", action, href)
			return


		frame.show_tooltip(x, y)
	
	@staticmethod
	def on_hover_bible(frame, href, url, x, y):
		scrolled_values = frame.CalcScrolledPosition(x, y) 
		screen_x, screen_y = frame.ClientToScreen(scrolled_values)
	
		frame.tooltip.show_bible_refs(href, url, screen_x, screen_y)

	def show_tooltip(self, x, y):
		scrolled_values = self.CalcScrolledPosition(x, y) 
		screen_x, screen_y = self.ClientToScreen(scrolled_values)
		self.tooltip.set_pos(screen_x, screen_y)
		self.tooltip.is_biblical = False
		self.tooltip.Start()

	def OnCellMouseLeave(self, cell, x, y):
		if self._tooltip is not None:
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
			type = "Strongs"+type#as module is StrongsHebrew
			if biblemgr.dictionary.ModuleExists(type):
				biblemgr.dictionary.SetModule(type)
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, value)
			return
		if action=="showMorph":
			type = url.getParameterValue("type") #Hebrew or greek
			value = url.getParameterValue("value") #strongs number
			if not type or not value: 
				return
			if type.split(":")[0] != "robinson":
				return


			#do lookup
			type = "Robinson" #as module is StrongsHebrew
			if biblemgr.dictionary.ModuleExists(type):
				biblemgr.dictionary.SetModule(type)
				wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, value)

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
		
			(MenuItem("Select all", self.select_all), IN_BOTH),
			(MenuItem("Copy selection (with links)", self.copy_text_with_links,
				enabled=lambda:bool(self.m_selection)), IN_BOTH),
			(MenuItem("Copy selection (without links)", self.copy_text_no_links,
				enabled=lambda:bool(self.m_selection)), IN_BOTH),

		)
		return menu_items

	def show_popup(self, event):
		menu = guiconfig.mainfrm.make_menu(
			[x for (x, where_shown) in self.get_menu_items() 
				if where_shown & IN_POPUP],
			is_popup=True)
		
		self.popup_position = guiutil.get_mouse_pos(self)#event.Position
		event_object = event.EventObject
		
		#if osutils.is_gtk():
		#	self.popup_position = event_object.ScreenToClient(self.popup_position)

		event.EventObject.PopupMenu(menu, self.popup_position)

	def get_popup_menu_items(self):
		return ((self.make_search_text(), self.make_lookup_text(), Separator) + 
			self.get_menu_items())

	def _get_text(self, lookup_text):
		def update_ui(event):
			text = self.SelectionToText()
			if not text:
				text = self.get_clicked_cell_text()

			if text:
				text = self.strip_text(text)

			if not text:
				event.Enable(False)
				event.SetText(lookup_text % "the selected word")
				return

			event.Enable(True)
			item = "'%s'" % text
			if text.find(" ") != -1:
				item = "the selected phrase"

			event.SetText(lookup_text % item)

		return update_ui

	def get_clicked_cell_text(self):
		cell = self.FindCell(*self.popup_position)
		if not cell: 
			return None

		return util.ReplaceUnicode(cell.ConvertToText(None))

	def make_lookup_text(self):
		update_ui = self._get_text("Look up %s in the dictionary")

		def on_lookup_click():
			"""Lookup the selected text in the dictionary"""
			text = self.SelectionToText()
			if not text:
				text = self.get_clicked_cell_text()

			text = self.strip_text(text)
			guiconfig.mainfrm.UpdateDictionaryUI(text)

		return MenuItem("Dictionary lookup", on_lookup_click, 
			update_ui=update_ui)


	def make_search_text(self):
		update_ui = self._get_text("Search for %s in the Bible")

		def on_search_click():
			""""Search for the selected word in the Bible"""
			text = self.SelectionToText()
			if not text:
				text = self.get_clicked_cell_text()

			text = self.strip_text(text)

			# if this is a phrase, put quotes around it.
			# In the future, it may be wise to set the type to phrase
			if " " in text:
				text = '"%s"' % text

			guiconfig.mainfrm.search_panel.search_and_show(text)


		return MenuItem("Search on word", on_search_click, 
			update_ui=update_ui)


	def select_all(self):
		"""Select all the text in the frame"""
		self.SelectAll()

	def copy_text_no_links(self):
		"""Copy the selected text, removing all links"""
		self.OnCopy(with_links=False)

	def copy_text_with_links(self):
		"""Copy the selected text with links"""
		self.OnCopy(with_links=True)
	
	#def test_wxp(self):
	#	import wx.lib.wxpTag
	#	self.SetPage("3 <wxp class='CheckBox'><param label='2' /></wxp>4")




class DisplayFrameXRC(DisplayFrame):
	def __init__(self):
		pre = html.PreHtmlWindow()
		self.PostCreate(pre)
		self.setup()

