import random

import wx

from swlib.pysw import VK, GetVerseStr, GetBookChapter, GetBestRange
from bookframe import VerseKeyedFrame
from displayframe import IN_BOTH, IN_MENU, IN_POPUP
from gui.htmlbase import linkiter, eq
from gui import guiutil
from util.observerlist import ObserverList

import config, guiconfig
from gui.menu import MenuItem, Separator

from harmony.harmonyframe import HarmonyFrame
from gui.quickselector import QuickSelector
from events import BIBLEFRAME, RANDOM_VERSE, VERSE_LINK_SELECTED, HEADER_BAR
from copyverses import CopyVerseDialog

from util.i18n import _
from util.configmgr import config_manager
from versecompare import VerseCompareFrame
import header_bar


bible_settings = config_manager.add_section("Bible")
bible_settings.add_item("verse_per_line", False, item_type=bool)


class BibleFrame(VerseKeyedFrame):
	title = "Bible"
	html_header = False

	def __init__(self, parent):
		self.panel = wx.Panel(parent)
		super(BibleFrame, self).__init__(self.panel)
		self.header_bar = header_bar.HeaderBar(self.panel, "Genesis 1")
		self.header_bar.on_click += lambda chapter: \
			guiconfig.mainfrm.set_bible_ref(chapter, HEADER_BAR)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.header_bar, 0, wx.GROW)
		sizer.Add(self, 1, wx.GROW)
		self.panel.SetSizer(sizer)


	def set_verse_per_line(self, to):
		"""Set to either verse-per-line or not. 
		
		Doesn't update UI."""
		config.bible_template.body.verse_per_line = to
		config.current_verse_template.body.verse_per_line = to

	def setup(self):
		self.observers = ObserverList()
		self.set_verse_per_line(bible_settings["verse_per_line"])
		super(BibleFrame, self).setup()
	
	def get_window(self):
		return self.panel

	def get_menu_items(self):
		items = super(BibleFrame, self).get_menu_items()
		
		for item, scope in items:
			if item != Separator and item.text == "Search":
				item.accelerator = "Ctrl-F"

		items = (
			(MenuItem("Harmony", self.show_harmony, accelerator="Ctrl-H"),
				IN_MENU),
			(MenuItem("Random verse", self.random_verse, accelerator="Ctrl-R"),
				IN_BOTH),
			(MenuItem("Copy verses", guiconfig.mainfrm.on_copy_button, 
				enabled=self.has_module, accelerator="Ctrl-Alt-C"), IN_BOTH),
			
			(MenuItem("Open sticky tooltip", self.open_sticky_tooltip, 
					enabled=self.has_module), IN_POPUP),
					
			(MenuItem("Compare verses", self.compare_verses, 
					enabled=self.has_module), IN_POPUP),
					
			
			(Separator, IN_BOTH),
			# Pick suitably arbitrary accelerators.
			(MenuItem("Manage Topics", self.manage_topics,
					accelerator="Ctrl+Shift+T"), IN_BOTH),
			(MenuItem("Tag verses", self.tag_verses,
					enabled=self.has_module), IN_BOTH),

			(Separator, IN_BOTH),
				 
		) + items

		return items
	
	def get_actions(self):
		actions = super(BibleFrame, self).get_actions()
		actions.update({
			ord("S"): self.search_quickly,
			(ord("C"), wx.MOD_CMD|wx.MOD_SHIFT): self.copy_quickly,
			(ord("T"), wx.MOD_SHIFT): self.tooltip_quickly,
			ord("T"): self.tag_verses,
			
		})
		return actions
	
	def tooltip_quickly(self):
		qs = QuickSelector(self.get_window(), 
			title="Open sticky tooltip")

		qs.pseudo_modal(self.tooltip_quickly_finished)
		
	def tooltip_quickly_finished(self, qs, ansa):
		if ansa == wx.OK:
			text = self.get_verified_multi_verses(qs.text)
			if text:
				self.open_tooltip(text)
				
		qs.Destroy()
	
	
	def get_quick_selected(self):
		text = self.GetRangeSelected()

		if not text:
			text = self.reference

		return text

	def open_sticky_tooltip(self):
		"""Open a sticky tooltip with the selected verses"""
		text = self.get_quick_selected()
		self.open_tooltip(text)
	
	
	def compare_verses(self):
		"""Open the verse comparison pane to the selected verses"""
		
		text = self.get_quick_selected()
		title = VerseCompareFrame.title
		#if not guiconfig.mainfrm.is_pane_shown(title):
		guiconfig.mainfrm.show_panel(title)
		guiconfig.mainfrm.verse_compare.notify(text)
			
	
	def copy_quickly(self):
		d = wx.BusyInfo("Copying selected verses...")
		wx.Yield()
	
		text = self.get_quick_selected()
		wx.Yield()

		cvd = CopyVerseDialog(self)
		cvd.copy_verses(text)
		cvd.Destroy()	
	
		
	def show_harmony(self):
		"""Opens the harmony"""
		harmony_frame = HarmonyFrame(guiconfig.mainfrm)
		harmony_frame.SetIcons(guiconfig.icons)
		harmony_frame.Show()
		
	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		version = self.book.version
		ref = self.reference
		text = "%s (%s)" % (ref, version)
		
		m.set_pane_title(p.name, text)
		
	
	def random_verse(self):
		"""Go to a random verse"""
		randomnum = random.randint(1, 31102)
		text = VK("Gen 1:%d" % randomnum).text
		self.notify(text, source=RANDOM_VERSE)
	
	def notify(self, reference, source=BIBLEFRAME):
		#event = BibleEvent(ref=reference, source=source)
		self.observers(reference, source)

	def search_quickly(self):
		qs = QuickSelector(self.get_window(), 
			title="Search in Bible for:")

		qs.pseudo_modal(self.search_quickly_finished)
 
	def manage_topics(self):
		"""Manages all of the topics and the passages in them."""
		from manage_topics_frame import ManageTopicsFrame
		frame = ManageTopicsFrame(self)
		frame.Show()

	def tag_verses(self):
		"""Tags the currently selected verses."""
		from tag_passage_dialog import tag_passage
		tag_passage(self, self.get_quick_selected())
	
	def search_quickly_finished(self, qs, ansa):
		if ansa == wx.OK:
			guiconfig.mainfrm.search_panel.search_and_show(qs.text)

		qs.Destroy()
	
	@guiutil.frozen
	def SetReference(self, ref, context=None, raw=None):
		"""Sets reference. This is set up to be an observer of the main frame,
		so don't call internally. To set verse reference, use notify"""
		if raw is None:
			raw = config.raw

		self.reference = GetVerseStr(ref)

		chapter = GetBookChapter(self.reference)
		self.header_bar.set_current_chapter(chapter)
		data = ''

		if self.html_header:		
			data += '<table width="100%" VALIGN=CENTER ><tr>'
			vk = VK(self.reference)
			vk.chapter -= 1
			d = lambda:{"ref":GetBookChapter(vk.text),
				"graphics":config.graphics_path}

			if not vk.Error():
				data += ('<td align="LEFT" valign=CENTER>'
						 '<a href="headings:%(ref)s">'
						 '<img src="%(graphics)sgo-previous.png">&nbsp;'
						 '%(ref)s</a></td>'
				) % d()
			else:
				data += '<td align=LEFT>'+ '&nbsp;'*15 + '</td>'
						

			data += "<td align=CENTER><center>%s</center></td>" % \
					"<h3>%s</h3>" % chapter
			
			vk = VK(self.reference)
			vk.chapter += 1
			if not vk.Error():
				data += ('<td align="RIGHT" valign=CENTER>'
						 '<a href="headings:%(ref)s">%(ref)s&nbsp;'
						 '<img src="%(graphics)sgo-next.png">'
						 '</a></td>'
				) % d()
			else:
				data += '<td align=RIGHT>'+ '&nbsp;'*15 + '</td>'

			data += "</tr></table>\n"

		chapter = self.book.GetChapter(ref, self.reference,
			config.current_verse_template, context, raw=raw)

		if chapter is None:
			data = config.MODULE_MISSING_STRING
			self.SetPage(data, raw=raw)
			
			

		else:
			data += chapter

			data = data.replace("<!P>","</p><p>")
			#replace common values
			#data = ReplaceUnicode(data)

			self.SetPage(data, raw=raw)

			#set to current verse
			self.scroll_to_current()

		#file = open("a.html","w")
		#file.writelines(data)
		#file.close()
		self.update_title()

		


	def LinkClicked(self, link, cell):
		if(self.select): return
		#cell = link.GetHtmlCell()
		href = link.GetHref()
		if(href.startswith("#")):
			string = cell.ConvertToText(None)
			self.notify(GetVerseStr(string, self.reference),
				source=VERSE_LINK_SELECTED)
			#self.ScrollTo(string,cell)
			return
		super(BibleFrame, self).LinkClicked(link, cell)
	
	def FindVerse(self, cell, start_cell):
		assert cell.IsTerminalCell()
		i = linkiter(start_cell, cell)

		prev = i.m_pos
		verse = None
		while (i):
			#print cell, i.m_pos
		
			# new block
			#if (not eq(prev.GetParent(), i.m_pos.GetParent())):
			#	text += '\n';
			#	faketext += '\n'
			#print i.m_pos.ConvertToText(None)

			if(i.m_pos.GetLink()):
				target = i.m_pos.GetLink().GetTarget()
				if target:
					try:
						int(target)
					except:
						print "Excepting"
						pass
					else:
						verse = target
						#print "TARGET", target

			
			prev = i.m_pos
			i.next()
			

		if not eq(prev, cell):
			return None

		if not verse:
			return None

		return GetVerseStr(verse, self.reference)
	
	def GetRangeSelected(self):
		if not self.m_selection:
			return

		from_cell = self.m_selection.GetFromCell()
		to_cell = self.m_selection.GetToCell()

		start_cell = self.GetInternalRepresentation().GetFirstChild()
		first = self.FindVerse(from_cell, start_cell=start_cell)
		
		last = self.FindVerse(to_cell, start_cell=start_cell)

		if not first:
			first = GetVerseStr("1", self.reference)

		if not last:
			return ""

		text = first + " - " + last
		print text
		return GetBestRange(text)

	
	#def CellClicked(self, cell, x, y, event):
	#	#if(self.select): return
	#	if(event.ControlDown()):
	#		print cell.this, self.FindVerse(cell)

	#	return super(BibleFrame, self).CellClicked(cell, x, y, event)

	

