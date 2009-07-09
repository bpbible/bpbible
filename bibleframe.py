import random

import wx

from swlib.pysw import VK, GetVerseStr, GetBookChapter, GetBestRange
from swlib import pysw
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

from util.configmgr import config_manager
from versecompare import VerseCompareFrame
import header_bar
import re
from util.i18n import N_

from guess_verse import GuessVerseFrame
import user_comments


bible_settings = config_manager.add_section("Bible")
bible_settings.add_item("verse_per_line", False, item_type=bool)
bible_settings.add_item("select_verse_on_click", False, item_type=bool)

class BibleFrame(VerseKeyedFrame):
	id = N_("Bible")
	do_convert_lgs = True
	lg_width = 60

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
			if item != Separator and item.text == _("Search"):
				item.accelerator = "Ctrl-F"

		items = (
			(MenuItem(
				_("Harmony"), 
				self.show_harmony, 
				accelerator="Ctrl-H",
				doc=_("Open the harmony"),
			), IN_MENU),
			(MenuItem(
				_("Guess the Verse"), 
				self.show_guess_verse, 
				accelerator="Ctrl-Shift-G",
				doc=_("Play Guess the Verse"),
				enabled=self.has_module, 
				
			), IN_MENU),
			
			(MenuItem(
					_("Random verse"), 
					self.random_verse, 
					accelerator="Ctrl-R",
					doc=_("Go to a random verse")
			), IN_BOTH),
			(MenuItem(
				_("Copy verses"), 
				guiconfig.mainfrm.on_copy_button, 
				enabled=self.has_module, 
				accelerator="Ctrl-Alt-C",
				doc=_("Copy verses to other applications")
			), IN_BOTH),
			
			(MenuItem(
				_("Open sticky tooltip"), 
				self.open_sticky_tooltip, 
				enabled=self.has_module, 
				doc=_("Open a sticky tooltip with the selected verses")
			), IN_POPUP),
					
			(MenuItem(
				_("Compare verses"), 
				self.compare_verses, 
				enabled=self.has_module,
				doc=_("Open the verse comparison pane to the selected verses")
			), IN_POPUP),
					
			
			(Separator, IN_MENU),
			(MenuItem(
				_("Manage Topics"), 
				self.manage_topics,
				accelerator="Ctrl+Shift+T",
				doc=_("Manages all of the topics and the passages in them.")	
			), IN_MENU),
			(MenuItem(
				_("Tag verses"), 
				self.tag_verses,
				accelerator="Ctrl+T",
				enabled=self.has_module,
				doc=_("Tags the currently selected verses.")

			), IN_BOTH),
			(MenuItem(
				_("Add comment to verses"), 
				self.comment_on_verses,
				enabled=self.has_module,
				doc=_("Makes a comment on the currently selected verses."),
			), IN_BOTH),

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
			ord("C"): self.comment_on_verses,
			
		})
		return actions
	
	def tooltip_quickly(self):
		qs = QuickSelector(self.get_window(), 
			title=_("Open sticky tooltip"))

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
		text = self.get_quick_selected()
		self.open_tooltip(text)
	
	
	def compare_verses(self):
		text = self.get_quick_selected()
		title = VerseCompareFrame.id
		#if not guiconfig.mainfrm.is_pane_shown(title):
		guiconfig.mainfrm.show_panel(title)
		guiconfig.mainfrm.verse_compare.notify(text)
			
	
	def copy_quickly(self):
		d = wx.BusyInfo(_("Copying selected verses..."))
		wx.Yield()
	
		text = self.get_quick_selected()
		wx.Yield()

		cvd = CopyVerseDialog(self)
		cvd.copy_verses(text)
		cvd.Destroy()	
	
		
	def show_harmony(self):
		harmony_frame = HarmonyFrame(guiconfig.mainfrm)
		harmony_frame.SetIcons(guiconfig.icons)
		harmony_frame.Show()
		
	def show_guess_verse(self):
		guess_frame = GuessVerseFrame(guiconfig.mainfrm)
		guess_frame.SetIcons(guiconfig.icons)
		guess_frame.Show()
		
	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		version = self.book.version
		ref = pysw.internal_to_user(self.reference)
		text = "%s (%s)" % (ref, version)
		
		m.set_pane_title(p.name, text)
		
	
	def random_verse(self):
		randomnum = random.randint(1, 31102)
		ref = VK("Gen 1:%d" % randomnum).text
		self.notify(ref, source=RANDOM_VERSE)
	
	def notify(self, reference, source=BIBLEFRAME):
		#event = BibleEvent(ref=reference, source=source)
		self.observers(reference, source)
 
	def manage_topics(self):
		from manage_topics_frame import ManageTopicsFrame
		frame = ManageTopicsFrame(guiconfig.mainfrm)
		frame.Show()

	def tag_verses(self):
		from tag_passage_dialog import tag_passage
		tag_passage(self, self.get_quick_selected())

	def comment_on_verses(self):
		from tag_passage_dialog import comment_on_passage
		comment_on_passage(self, self.get_quick_selected())
	
	@guiutil.frozen
	def SetReference(self, ref, context=None, raw=None, y_pos=None):
		"""Sets reference. This is set up to be an observer of the main frame,
		so don't call internally. To set verse reference, use notify"""
		if raw is None:
			raw = config.raw

		self.reference = GetVerseStr(ref)

		chapter = GetBookChapter(self.reference)
		self.header_bar.set_current_chapter(
			pysw.internal_to_user(chapter), chapter
		)
		data = ''

		chapter = self.book.GetChapter(ref, self.reference,
			config.current_verse_template, context, raw=raw)

		if chapter is None:
			data = config.MODULE_MISSING_STRING()
			self.SetPage(data, raw=raw)

		elif chapter == '':
			data = '<font color="#888888"><i>%s</i></font>' % _(
				"This chapter is empty.")
			self.SetPage(data, raw=raw)
			
		else:
			data += chapter

			data = data.replace("<!P>","</p><p>")
			#replace common values
			#data = ReplaceUnicode(data)

			self.SetPage(data, raw=raw)

			#set to current verse
			if y_pos is not None:
				self.Scroll(-1, y_pos)
			else:
				self.scroll_to_current()

		#file = open("a.html","w")
		#file.writelines(data)
		#file.close()
		self.update_title()

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
				match = re.match("nbible:([^#]*)(#current)?", 
					i.m_pos.GetLink().Href)
				#GetTarget()
				if match:
					verse = match.group(1)
			
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

		# use the first terminal as:
		#  - it isn't the one we want (it is probably a font cell)
		#  - we call next on it right away, so it shouldn't be a container
		#    otherwise we may miss bits
		start_cell = self.GetInternalRepresentation().FirstTerminal
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

	def CellMouseUp(self, cell, x, y, event):
		if not self.m_tmpHadSelection and not self.m_selection and not event.Dragging():
			self.maybe_select_clicked_verse(cell)

	def maybe_select_clicked_verse(self, cell):
		if not bible_settings["select_verse_on_click"]:
			return

		start_cell = self.GetInternalRepresentation().FirstTerminal
		reference = self.FindVerse(cell, start_cell=start_cell)
		if reference:
			wx.CallAfter(self.suppress_scrolling,
				lambda: self.notify(reference)
			)
