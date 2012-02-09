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
from gui import guiutil
from util.observerlist import ObserverList
from backend.bibleinterface import biblemgr

import guiconfig
from gui.menu import MenuItem, Separator

from gui.quickselector import QuickSelector
import events
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

	def __init__(self, parent):
		self.panel = wx.Panel(parent)
		super(BibleFrame, self).__init__(self.panel)
		self.header_bar = header_bar.HeaderBar(self.panel, "Genesis 1")
		self.header_bar.on_click += lambda chapter: \
			guiconfig.mainfrm.set_bible_ref(chapter, events.HEADER_BAR)
		self.last_bible_event = None
		
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

	def DomContentLoaded(self, event):
		super(BibleFrame, self).DomContentLoaded(event)
		self.NewReferenceLoaded()
	
	def get_window(self):
		return self.panel

	def get_menu_items(self, event=None):
		items = super(BibleFrame, self).get_menu_items(event)
		
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
					enabled=self.has_module,
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
				enabled=self.has_module,
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
			else:
				return
				
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
		guiconfig.mainfrm.show_panel(title)
		guiconfig.mainfrm.verse_compare.notify(text)
			
	
	def copy_quickly(self):
		d = wx.BusyInfo(_("Copying selected verses..."))
		wx.Yield()
	
		text = self.get_quick_selected()
		wx.Yield()

		cvd = CopyVerseDialog(self)
		cvd.copy_verses(text, dialog_hidden_mode=True)
		cvd.Destroy()
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
		self.notify(ref, source=events.RANDOM_VERSE)

	def history_go_back(self):
		if guiconfig.mainfrm.history.can_back():
			guiconfig.mainfrm.move_history(-1)

	def history_go_forward(self):
		if guiconfig.mainfrm.history.can_forward():
			guiconfig.mainfrm.move_history(1)
	
	def notify(self, reference, source=events.BIBLEFRAME):
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
		tag_type = biblemgr.bible.get_tag_type_to_show(passage_entry)
		if not tag_type:
			return

		verses_on_screen = self.get_verses_on_screen(added_verses)
		if verses_on_screen:
			get_div_contents = {
				"passage_tag": biblemgr.bible.get_passage_topic_div,
				"usercomment": biblemgr.bible.get_user_comment_div,
			}[tag_type]
			tag_contents = json.dumps(get_div_contents(passage_entry))
			script_to_execute = "".join(self.get_add_command(tag_contents, osisRef, tag_type) for osisRef in verses_on_screen)
			self.Execute(script_to_execute)

	def get_add_command(self, tag_content, osisRef, tag_type):
		return """$('.%(tag_type)s_container[osisRef="%(osisRef)s"]').append(%(tag_content)s);\n""" % locals()
	
	def on_remove_topic_verses(self, passage_entry, removed_verses):
		tag_type = biblemgr.bible.get_tag_type_to_show(passage_entry)
		verses_on_screen = self.get_verses_on_screen(removed_verses)
		if verses_on_screen:
			script_to_execute = "".join(self.get_delete_command(passage_entry, osisRef, tag_type) for osisRef in verses_on_screen)
			self.Execute(script_to_execute)

	def get_delete_command(self, passage_entry, osisRef, tag_type):
		passage_entry_id = passage_entry.get_id()
		return """$('.%(tag_type)s_container[osisRef="%(osisRef)s"] .%(tag_type)s[passageEntryId="%(passage_entry_id)d"]').remove();\n""" % locals()

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

	def HandleBibleEvent(self, event):
		self.last_bible_event = event
		self.SetReference(event.ref, event.ref_to_scroll_to, event.settings_changed)

	def NewReferenceLoaded(self):
		"""Only reload all the dependent frames when the Bible window has actually loaded."""
		if self.last_bible_event:
			guiconfig.mainfrm.bible_observers(self.last_bible_event)
			self.last_bible_event = None
	
	@guiutil.frozen
	def SetReference(self, ref, ref_to_scroll_to=None, settings_changed=False):
		"""Sets reference. This is set up to be an observer of the main frame,
		so don't call internally. To set verse reference, use notify"""
		self.reference = GetVerseStr(ref)

		has_selected_new_verse = False
		# If the settings have changed we want to do a complete reload anyway
		# (since it could be something that requires a complete reload, such as changing version).
		if self.dom_loaded:
			if settings_changed:
				self.reference, ref_to_scroll_to = self.GetCurrentReferenceAndPosition()
			else:
				osisRef = VK(self.reference).getOSISRef()
				has_selected_new_verse = self.ExecuteScriptWithResult('select_new_verse("%s")' % osisRef)
				has_selected_new_verse = (has_selected_new_verse == "true")

		if has_selected_new_verse:
			self.NewReferenceLoaded()
		elif self.CheckChapterInBook(ref):
			self.OpenURIForCurrentBook("bpbible://content/page/%s/%s" % (self.book.version, self.reference))

		if ref_to_scroll_to:
			self.scroll_to_osis_ref(ref_to_scroll_to)

		chapter = GetBookChapter(self.reference)
		self.header_bar.set_current_chapter(
			pysw.internal_to_user(chapter), chapter
		)

		self.update_title()

	def scroll_to_osis_ref(self, osisRef):
		self.scroll_to_anchor(osisRef + '_start');

	def GetCurrentReferenceAndPosition(self):
		if not self.dom_loaded:
			return ('', None)

		current_reference = GetVerseStr(self.ExecuteScriptWithResult('get_current_reference_on_screen()')) or self.reference
		ref_to_scroll_to = self.ExecuteScriptWithResult('current_reference_at_top_of_screen')
		return (current_reference, ref_to_scroll_to)

	def current_segment_changed(self, new_segment_ref):
		chapter = GetBookChapter(new_segment_ref)
		self.header_bar.set_current_chapter(
			pysw.internal_to_user(chapter), chapter
		)
	
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
						selectionStart = this.getAttribute("osisRef");
					}
					if (selectionRange.compareBoundaryPoints(Range.END_TO_END, linkRange) > 0)	{
						selectionEnd = this.getAttribute("osisRef");
					}
				});

				// If the selection is before the first verse marker (e.g. a chapter number) or after the last verse marker
				// then we should just use the first/last verse on the page.
				if (links.length > 0 && !selectionStart)	{
					selectionStart = links.get(0).getAttribute("osisRef");
				}
				if (links.length > 0 && !selectionEnd)	{
					selectionEnd = links.get(links.length - 1).getAttribute("osisRef");
				}
				return (selectionStart && selectionEnd) ? selectionStart + " - " + selectionEnd : "";
			})();
		""")
		if not text:
			return

		return GetBestRange(text)
