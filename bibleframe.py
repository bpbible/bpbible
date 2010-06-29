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
				_("Go to Reference"), 
				self.focus_reference_textbox, 
				accelerator="Ctrl-L",
				doc=_("Go to a reference"),
			), IN_MENU),
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
			(wx.WXK_LEFT, wx.MOD_ALT): self.history_go_back,
			(wx.WXK_RIGHT, wx.MOD_ALT): self.history_go_forward,
		})
		return actions

	def get_reference_textbox(self):
		return guiconfig.mainfrm.bibleref
	
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
		d.Destroy()
	
		
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

	def history_go_back(self):
		if guiconfig.mainfrm.history.can_back():
			guiconfig.mainfrm.move_history(-1)

	def history_go_forward(self):
		if guiconfig.mainfrm.history.can_forward():
			guiconfig.mainfrm.move_history(1)
	
	def notify(self, reference, source=BIBLEFRAME):
		#event = BibleEvent(ref=reference, source=source)
		self.observers(reference, source)
 
	def manage_topics(self):
		if not self.check_if_topic_management_is_available():
			return

		from manage_topics_frame import ManageTopicsFrame
		frame = ManageTopicsFrame(guiconfig.mainfrm)
		frame.Show()

	def tag_verses(self):
		if not self.check_if_topic_management_is_available():
			return

		from tag_passage_dialog import tag_passage
		tag_passage(self, self.get_quick_selected())

	def comment_on_verses(self):
		if not self.check_if_topic_management_is_available():
			return

		from tag_passage_dialog import comment_on_passage
		comment_on_passage(self, self.get_quick_selected())

	def check_if_topic_management_is_available(self):
		from passage_list import get_primary_passage_list_manager
		is_available = not get_primary_passage_list_manager().has_error_on_loading

		if not is_available:
			wx.MessageBox(_(u"Topic management is currently not available due to an error."),
				_(u"Error in Topic Management"), wx.OK | wx.ICON_ERROR, self)

		return is_available
	
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
		self.OpenURI("bpbible://content/page/%s/%s" % (self.book.version, self.reference))

		self.update_title()
	
	def GetRangeSelected(self):
		text = self.ExecuteScriptWithResult("""
			(function()	{
				var selectionRange = window.getSelection().getRangeAt(0);
				if (selectionRange.collapsed)	{
					return "";
				}
				var links = document.getElementsByTagName("a");
				var selectionStart = "";
				var selectionEnd = "";
				var re = /nbible:([^#]*)(#current)?/;
				var linkRange = document.createRange();
				for (var index = 0; index < links.length; index++)	{
					var link = links[index];
					var match = re.exec(link.href);
					if (!match)	{
						continue;
					}
					linkRange.selectNode(link);
					if (selectionRange.compareBoundaryPoints(Range.START_TO_START, linkRange) > 0)	{
						selectionStart = match[1];
					}
					if (selectionRange.compareBoundaryPoints(Range.END_TO_END, linkRange) > 0)	{
						selectionEnd = match[1];
					}
				}
				return (selectionStart && selectionEnd) ? decodeURI(selectionStart) + " - " + decodeURI(selectionEnd) : "";
			})();
		""")
		if not text:
			return

		return GetBestRange(text)

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
