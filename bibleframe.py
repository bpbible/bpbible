try:
	import json
except ImportError:
	import simplejson as json

import random

import wx

from swlib.pysw import VK, GetVerseStr, GetBookChapter, GetBestRange
from swlib import pysw
from bookframe import VerseKeyedFrame
from displayframe import IN_BOTH, IN_MENU, IN_POPUP
from gui.htmlbase import linkiter, eq
from gui import guiutil
from util.observerlist import ObserverList
from backend.bibleinterface import biblemgr

import config, guiconfig
from gui.menu import MenuItem, Separator

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
		from passage_list.verse_to_passage_entry_map import singleton_verse_to_passage_entry_map
		singleton_verse_to_passage_entry_map.add_verses_observers += self.on_add_topic_verses
		singleton_verse_to_passage_entry_map.remove_verses_observers += self.on_remove_topic_verses

	def setup(self):
		self.observers = ObserverList()
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

		# we can't destroy it until it has put the text there and copied it...
		cvd.preview.defer_call_till_document_loaded(lambda cvdpreview:cvd.Destroy())
		d.Destroy()
		
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

	def on_add_topic_verses(self, passage_entry, added_verses):
		if not biblemgr.bible.can_show_topic_tag(passage_entry.parent):
			return

		verses_on_screen = self.get_verses_on_screen(added_verses)
		if verses_on_screen:
			topic_tag = json.dumps(biblemgr.bible.get_passage_topic_div(passage_entry))
			script_to_execute = "".join(self.get_add_command(topic_tag, osisRef) for osisRef in verses_on_screen)
			self.Execute(script_to_execute)

	def get_add_command(self, topic_tag, osisRef):
		return """$('.passage_tag_container[osisRef="%s"]').append(%s);\n""" % (osisRef, topic_tag)
	
	def on_remove_topic_verses(self, passage_entry, removed_verses):
		verses_on_screen = self.get_verses_on_screen(removed_verses)
		if verses_on_screen:
			script_to_execute = "".join(self.get_delete_command(passage_entry, osisRef) for osisRef in verses_on_screen)
			self.Execute(script_to_execute)

	def get_delete_command(self, passage_entry, osisRef):
		return """$('.passage_tag_container[osisRef="%s"] .passage_tag[passageEntryId="%d"]').remove();\n""" % (osisRef, passage_entry.get_id())

	def get_verses_on_screen(self, verses):
		if not self.dom_loaded:
			return []

		osis_refs = [VK(verse).getOSISRef() for verse in verses]
		osis_refs_on_screen = self.ExecuteScriptWithResult("""
			(function(osis_refs) {
				var result = [];
				for (var index = 0; index < osis_refs.length; index++)	{
					var osisRef = osis_refs[index];
					var reference_found = $('[osisRef="' + osisRef + '"]').length > 0;
					if (reference_found)	{
						result.push(osisRef);
					}
				}
				return JSON.stringify(result);
			})(%s);
		""" % json.dumps(osis_refs))

		return json.loads(osis_refs_on_screen)
	
	@guiutil.frozen
	def SetReference(self, ref, context=None, raw=None, y_pos=None, settings_changed=False):
		"""Sets reference. This is set up to be an observer of the main frame,
		so don't call internally. To set verse reference, use notify"""
		if raw is None:
			raw = config.raw

		self.reference = GetVerseStr(ref)

		chapter = GetBookChapter(self.reference)
		self.header_bar.set_current_chapter(
			pysw.internal_to_user(chapter), chapter
		)
		has_selected_new_verse = False
		# If the settings have changed we want to do a complete reload anyway
		# (since it could be something that requires a complete reload, such as changing version).
		if self.dom_loaded:
			# in the document we keep user verse keys, in here we keep
			# internal ones. Do conversions as appropriate.
			if settings_changed:
				self.reference = GetVerseStr(self.ExecuteScriptWithResult('get_current_reference_range()'))
			else:
				ref = pysw.internal_to_user(self.reference)
				has_selected_new_verse = self.ExecuteScriptWithResult('select_new_verse("%s")' % ref)
				has_selected_new_verse = (has_selected_new_verse == "true")

		if not has_selected_new_verse:
			self.OpenURI("bpbible://content/page/%s/%s" % (self.book.version, self.reference))

		self.update_title()
	
	def GetRangeSelected(self):
		text = self.ExecuteScriptWithResult("""
			(function()	{
				var selectionRange = window.getSelection().getRangeAt(0);
				if (selectionRange.collapsed)	{
					return "";
				}
				var links = $("a.vnumber");
				var selectionStart = "";
				var selectionEnd = "";
				var linkRange = document.createRange();
				links.each(function()	{
					linkRange.selectNode(this);
					if (selectionRange.compareBoundaryPoints(Range.START_TO_START, linkRange) > 0)	{
						selectionStart = this.getAttribute("reference");
					}
					if (selectionRange.compareBoundaryPoints(Range.END_TO_END, linkRange) > 0)	{
						selectionEnd = this.getAttribute("reference");
					}
				});
				return (selectionStart && selectionEnd) ? selectionStart + " - " + selectionEnd : "";
			})();
		""")
		if not text:
			return

		return GetBestRange(text)
