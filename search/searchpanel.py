import re
import time

#wx imports
import wx
from wx import xrc

from util import osutils
from util.unicode import to_unicode, to_str
from util import string_util
from backend.verse_template import VerseTemplate
from backend.bibleinterface import biblemgr
from xrc.search_xrc import *

import config
import guiconfig
import index
from index import COMBINED
from index import SearchException, SpellingException, RemoveDuplicates
from search.query_parser import separate_words
from search.stemming import get_stemmer

from search.highlighted_frame import HighlightedDisplayFrame
from swlib.pysw import (
	TK, VK, UserVK, GetBestRange, Searcher, VerseKeySearcher, SWREGEX
)
from gui import guiutil
from util.debug import dprint, WARNING, is_debugging
from gui import virtuallist
from gui import reference_display_frame
from gui import fonts
from events import SEARCH
from util.configmgr import config_manager
from manage_topics_frame import ManageTopicsFrame

from keypad import KeyPad
from util.i18n import N_
from util import i18n



#TODO: better status bar: text overlay
#						  status messages

# TODO: Sword regex search doesn't work with word boundaries

#class MyThread(threading.Thread):
#	def __init__(self, dialog):
#		self.dialog = dialog
#		threading.Thread.__init__(self)
#
#	def run(self):
#		self.dialog.on_search2()

search_config = config_manager.add_section("Search")
search_config.add_item("disappear_on_doubleclick", True, item_type=bool)

# we don't currently use this setting
# search_config.add_item("search_type", COMBINED, item_type=int)
search_config.add_item("indexed_search", True, item_type=bool)
search_config.add_item("past_search_length", 20, item_type=int)
search_config.add_item("past_searches", [], item_type="pickle")

class RangePanel(xrcRangePanel):
	def __init__(self, parent):
		super(RangePanel, self).__init__(parent)
		self.oldtestament.Bind(wx.EVT_RADIOBUTTON, self.old_testament)
		self.newtestament.Bind(wx.EVT_RADIOBUTTON, self.new_testament)
		self.wholebible.Bind(wx.EVT_RADIOBUTTON, self.whole_bible)
		self.custom_range.Bind(wx.EVT_TEXT, self.on_custom_changed)
		self.range_top.Bind(wx.EVT_CHOICE, self.on_range_top)
		self.range_bottom.Bind(wx.EVT_CHOICE, self.on_range_bottom)
		
		self.biblebooks = []

		for book in UserVK.books:
			bookname = unicode(book)
			self.biblebooks.append(bookname)
			self.range_top.Append(bookname)
			self.range_bottom.Append(bookname)

		self.range_top.SetSelection(0)
		number = self.range_bottom.GetCount()
		self.range_bottom.SetSelection(number-1)
		self.update_boxes(self.wholebible)
		
		
	def old_testament(self, event = None):
		self.range_top.SetSelection(0)
		vk = VK()
		num = vk.bookCount(1)
		self.range_bottom.SetSelection(num-1)
		self.update_boxes(self.oldtestament)
		
	def new_testament(self, event=None):
		vk = VK()
		start = vk.bookCount(1)
		self.range_top.SetSelection(start)
		number = self.range_bottom.GetCount()
		self.range_bottom.SetSelection(number-1)

		self.update_boxes(self.newtestament)

	   
	def whole_bible(self, event=None):
		self.range_top.SetSelection(0)
		number = self.range_bottom.GetCount()
		self.range_bottom.SetSelection(number-1)
		self.update_boxes(self.wholebible)
	
	def on_custom_changed(self, event=None):
		self.update_boxes(set_custom=False)		
	
	def on_range_top(self, event=None):
		sel = self.range_top.GetSelection()
		if(self.range_bottom.GetSelection() < sel):
			self.range_bottom.SetSelection(sel)
		self.update_boxes()

	def on_range_bottom(self, event=None):
		sel = self.range_bottom.GetSelection()
		if(self.range_top.GetSelection() > sel):
			self.range_top.SetSelection(sel)		 
		self.update_boxes()
	
	def update_boxes(self, radio=None, set_custom=True):
		# we have a dummy radio box, which gets the selection when no radio
		# box is selected. This is needed under wxGTK, where it seems you
		# cannot set it a radio box's value to False
		# The dummy radio box is hidden, of course.
		if radio is None:
			radio = self.dummy_radio

		for item in [self.oldtestament, self.newtestament, self.wholebible,
				self.dummy_radio]:
			item.SetValue(item is radio)

		if set_custom:
			self.custom_range.ChangeValue("%s - %s" % (
				self.range_top.StringSelection,
				self.range_bottom.StringSelection))

	def get_scope(self):
		if self.wholebible.Value:
			scope = None

		else:
			# If custom range, use it
			scope = self.custom_range.GetValue()

		return scope

class SearchPanel(xrcSearchPanel):
	id = N_("Search")
	def __init__(self, parent):
		super(SearchPanel, self).__init__(parent)
		
		#if osutils.is_gtk():
		#	self.Bind(wx.EVT_WINDOW_CREATE, self.on_create)
		#else:
		wx.CallAfter(self.on_create)

		self.search_results = []
		self.save_results_button.Hide()

		self.searching = False
		self.index = None
		self.version = None
		self.stop = False
		self.regexes = []
		self.fields = []

		# if search panel is on screen at startup, on_show and set_version will
		# both be called. Then if there is no index, it will prompt twice.
		# This flag is false only before the end of the first call to
		# set_version
		self.has_started = False
		self.search_on_show = False
		
		self.verselist.parent = self
		self.versepreview.parent = self

		fonts.fonts_changed += self.set_font
	
	def on_create(self, event=None):
		self.Unbind(wx.EVT_WINDOW_CREATE)
		self._post_init()
		if event:
			event.Skip()

		return True
	
	def on_list(self, event):
		item_text = self.verselist.results[event.m_itemIndex]
		self.versepreview.SetReference(item_text)
	
	def search_and_show(self, key=""):
		self.searchkey.SetValue(key)

		# If we call on_search from here, then it may search before asking
		# the user about building the search index, so instead we call it
		# from on_show after checking the index.
		self.show(search_on_show=True)
	
	def show(self, search_on_show=False):
		self.search_on_show = search_on_show
		guiconfig.mainfrm.show_panel(self.id)
	
	def on_show(self, toggle):
		self.search_splitter.SetSashPosition(
				self.search_splitter.ClientSize[1]/2
		)
		
		
		if self.version is None:
			self.genindex.Disable()
	
		if not toggle: 
			return

		panel = guiconfig.mainfrm.aui_mgr.GetPane(self.id)
		if panel.IsFloating():
			# do resizing to force layout 
			#panel.window.SetSize(panel.window.GetSize() + (0, 1))		
			tlw = guiutil.toplevel_parent(panel.window)
			assert tlw
			tlw.DefaultItem = self.search_button
			tlw.Show()

			self.searchkey.SetFocus()
			
			#tlw.Sizer.Layout()
			#tlw.SetSize(panel.floating_size)		
			
			
			
		else:
			dprint(WARNING, "NOT FLOATING", panel)
		
		self.check_for_index()
		self.set_title()
		
		if self.search_on_show:
			self.search_on_show = False
			wx.CallAfter(self.on_search)
	
	def set_version(self, version):
		self.version = version

		self.set_font()
		self.genindex.Enable(version is not None)
		

		if(guiconfig.mainfrm.is_pane_shown(self.id) and self.has_started):
			self.check_for_index()

		self.search_label.Label = _("%d references found") % 0
		self.versepreview.SetReference(None)
		

		wx.CallAfter(self.clear_list)

		self.set_title()
		self.has_started = True
	
	def set_font(self):
		if self.version is None:
			return

		module = self.book.parent.get_module(self.version)
		assert module
		
		font = fonts.get_module_gui_font(module)

		self.verselist.Font = font
		self.searchkey.Font = font
		self.layout_panel_1()
		

	
	def set_index_available(self, available=True):
		if not available:
			self.genindex.SetLabel(_("&Index"))
			
		else:
			self.genindex.SetLabel(_("Unindex"))
			self.search_button.Enable()

		
		
		if not is_debugging():
			self.genindex.ContainingSizer.Show(self.genindex, not available)
		
			self.layout_panel_1()
			

	def layout_panel_1(self):
		# If we have Jesus "lamb" in our search combo dropdown items, and do a
		# layout when Jesus is type in, it changes to Jesus "lamb"
		# so change it back
		old_value = self.searchkey.Value
		self.panel_1.Layout()
		self.searchkey.Value = old_value
		

	def check_for_index(self):
		self.set_gui_search_type(search_config["indexed_search"])
		NO_CURRENT_VERSION = _("You don't have a current %s, "
				"so you cannot search at the moment") % self.book.noun
		if not search_config["indexed_search"]:
			self.search_button.Enable(self.book.version is not None)
			self.set_index_available(index.IndexExists(self.version))
			if not self.book.version:
				wx.MessageBox(NO_CURRENT_VERSION,
				_("No current version"), parent=self)
			
			return
		

		if self.index and self.index.version == self.version:
			self.set_index_available(True)
			
			return

		if(self.version and index.IndexExists(self.version)):
			busy_info = wx.BusyInfo(_("Reading search index..."))
			try:
				self.index = index.ReadIndex(self.version)
			except Exception, e:
				dprint(WARNING, "Error reading index. Deleting it...", e)
				try:
					index.DeleteIndex(self.version)
				except Exception, e2:
					dprint(WARNING, "Couldn't delete it", e2)

				self.index = None
				self.show_keyboard_button(shown=False)
				self.set_index_available(False)
			#	del busy_info

				
			else:
				self.set_index_available(True)
				return
			
		self.search_button.Enable(self.version is not None)
		
		self.index = None
		
		if not self.version:
			wx.MessageBox(NO_CURRENT_VERSION,
			_("No current version"), parent=self)
			self.show_keyboard_button(shown=False)
			
			return
		self.set_index_available(False)

		msg = _("Search index does not exist for book %s. "
			"Indexing will make search much faster. "
			"Create Index?") % self.version 
		create = wx.MessageBox(msg, _("Create Index?"), 
			wx.YES_NO, parent=self)
		if create == wx.YES:
			self.build_index(self.version)
		else:
			self.set_gui_search_type(self.indexed_search)

	def on_select(self, event):
		self.go_to_reference(event.m_itemIndex)
		if search_config["disappear_on_doubleclick"]:
			self.on_close()
		
	
	def go_to_reference(self, idx):
		item_text = self.verselist.results[idx]
		
		guiconfig.mainfrm.set_bible_ref(item_text, source=SEARCH)
			
	def _post_init(self):
		self.search_button.SetLabel(_("&Search"))
	
		self.search_splitter.SetSashGravity(0.5)
		self.search_splitter.SetSashPosition(
				self.search_splitter.ClientSize[1]/2
		)

		for search_key in search_config["past_searches"]:
			self.searchkey.Append(search_key)

		if osutils.is_msw():
			# MSW insertion point is lost when the control is unfocused
			# so track it		
			self.insertion_point = 0
			self.searchkey.Bind(wx.EVT_SET_FOCUS, self.on_searchkey_focus)
			self.searchkey.Bind(wx.EVT_KILL_FOCUS, self.on_searchkey_unfocus)
		

		font = self.search_label.Font
		font.SetWeight(wx.FONTWEIGHT_BOLD)
		self.search_label.Font = font
		self.collapsible_panel.WindowStyle |= wx.CP_NO_TLW_RESIZE
		self.collapsible_panel.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, 
			self.on_collapse)	

		# XRC doesn't localize the Label
		self.collapsible_panel.Label = _("Search Options")
		

		# Do all init here
		#self.Fit()
		#self.GetContainingSizer().ContainingWindow.Fit()
		
		# Do binding
		self.Bind(wx.EVT_BUTTON, self.on_search_button, self.search_button)
		self.Bind(wx.EVT_BUTTON, self.on_close, id=wx.ID_CLOSE)
		
		self.construct_option_panels(self.options_holder)

		
		
		self.verselist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		self.verselist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_select)
		self.genindex.Bind(wx.EVT_BUTTON, self.generate_index)
		self.keyboard_button.Bind(wx.EVT_BUTTON, self.show_keyboard)

		# Set properties:

		# under gtk, enter in the searchkey should push button...
		if not osutils.is_msw():

			self.searchkey.Bind(wx.EVT_KEY_UP, 
			lambda event:event.KeyCode == wx.WXK_RETURN and (self.on_search(),) 
				or event.Skip())

		#SetWindowStyle(self.searchkey.GetWindowStyle() | \
		#							  wx.TE_PROCESS_ENTER)
		#self.verselist.InsertColumn(0, "Reference")
		#self.verselist.InsertColumn(1, "Preview")
		self.set_gui_search_type(search_config["indexed_search"])

	def construct_option_panels(self, parent):
		self.range_panel = RangePanel(parent)
		self.options_panel = xrcOptionsPanel(parent)
		parent.Sizer.Add(self.options_panel, 1, wx.GROW)
		parent.Sizer.Add(self.range_panel, 1, wx.GROW)
		
		self.options_panel.gui_search_type.Bind(
			wx.EVT_CHOICE, self.on_search_type)
		
	def get_scope(self):
		return self.range_panel.get_scope()

	def on_collapse(self, event):
		self.layout_panel_1()
		self.verselist.Refresh()

	def on_searchkey_focus(self, event):
		event.Skip()
		
		self.searchkey.Bind(wx.EVT_IDLE, self.set_insertion_point)
	
	def on_searchkey_unfocus(self, event):
		event.Skip()
	
		unbound = self.searchkey.Unbind(wx.EVT_IDLE)
		assert unbound, "Unequal focus shifting"
	
	def set_insertion_point(self, event):
		event.Skip()
		self.insertion_point = self.searchkey.InsertionPoint

	def show_keyboard(self, event):
		assert self.index is not None, "No index in show keyboard"

		btn = event.GetEventObject()
		pos = btn.ClientToScreen((btn.Size[0], 0))
		position = pos, (-btn.Size[0], btn.Size[0])
		module = self.book.parent.get_module(self.version)
		assert module
		
		font = fonts.get_module_gui_font(module, default_to_None=True)
		
		kp = KeyPad(self, self.index.statistics["letters"], position, font)
		
		
		def press_key(key):
			if osutils.is_msw():
				insertion_point = self.insertion_point
				self.insertion_point += 1
				
			else:
				insertion_point = self.searchkey.GetInsertionPoint()
				
			text = self.searchkey.Value 
			text = text[:insertion_point] + key + text[insertion_point:]
			self.searchkey.Value = text
			self.searchkey.SetInsertionPoint(insertion_point + 1)

		kp.key_pressed += press_key
		kp.Popup()

	def set_gui_search_type(self, indexed_search):
		"""Sets the search type to be displayed in the GUI."""
		self.options_panel.gui_search_type.SetSelection(not indexed_search)
		self.show_keyboard_button(shown=indexed_search)
		
	def show_keyboard_button(self, shown=True):
		self.keyboard_button.ContainingSizer.Show(self.keyboard_button, shown)
		self.layout_panel_1()
	
	def on_close(self, event=None):
		guiconfig.mainfrm.show_panel(self.id, False)

	def stop_search(self):
		self.stop = True
	
	def show_progress_bar(self, toggle=True):
		self.progressbar.Show(toggle)
		sizer = self.progressbar.ContainingSizer
		sizer.Children[1].Show(not toggle)
		self.progressbar.ContainingSizer.Layout()

		self.genindex.Enable(self.version is not None and not toggle)

	def on_search_button(self, event=None):
		#if already searching, this is magically a terminate button
		#so if clicked, quit
		if(self.searching):
			self.stop_search()

		else:
			self.on_search()
	
	def on_search(self):
		if self.searching:
			dprint(WARNING, 
				"Already searching when on_search called.  Ignoring...")
			return

		try:
			self.stop = False
			self.searching = True
			self.search_button.SetLabel(_("&Stop"))
			
			key = self.searchkey.GetValue()
			if not key: 
				self.search_label.Label = _("%d references found") % 0

				wx.CallAfter(self.clear_list)
				return


			### insert the item into the combo box
			try:
				# if it is there already, delete it ready for 
				# insertion at the top
				idx = self.searchkey.Strings.index(key)
				self.searchkey.Delete(idx)
			except ValueError:
				# index throws ValueError if it isn't there
				pass
				
			self.searchkey.Insert(key, 0)
			self.searchkey.SetSelection(0)
			search_config["past_searches"] = self.searchkey.Strings[:search_config["past_search_length"]]
		
			self.show_progress_bar()
		    
			scope = self.get_scope()
			
			case_sensitive = self.options_panel.case_sensitive.GetValue()

			
			self.perform_search(key, scope, case_sensitive)

		finally:
			self.show_progress_bar(False)
			self.searching = False
			self.search_button.SetLabel(_("&Search"))
			

	def perform_search(self, key, scope, case_sensitive):
		proximity, is_word_proximity = self.get_proximity_options()
		
		
		if self.indexed_search:
			index_word_list = self.index.statistics["wordlist"]
			stemming_data = self.index.statistics["stem_map"]

			# don't stem on case sensitive as we cannot retain the case
			if not case_sensitive:
				stemmer = get_stemmer(self.book.mod)
			else:
				stemmer = None
		else:
			index_word_list = None
			stemming_data = None
			stemmer = None

		
		succeeded = True
		try:
			(regexes, excl_regexes), (fields, excl_fields) = separate_words(
				key, index_word_list, stemming_data, stemmer,
				cross_verse_search=is_word_proximity or proximity > 1
			)

		except SearchException, myexcept:
			wx.MessageBox(myexcept.message, _("Error in search"), parent=self)
			succeeded = False

		except SpellingException, spell:
			wx.MessageBox(u"%s\n%s" % (
				_("The following words were not found in this %s:") 
					% self.book.noun, 
				unicode(spell)
			), _("Unknown word"),
				parent=self
			)
		
			succeeded = False
		
		if not succeeded:
			self.regexes = []	
			self.fields = []
			return
		
			
		

		flags = re.UNICODE | re.IGNORECASE * (not case_sensitive) | re.MULTILINE
		
		try:
			self.regexes = [re.compile(regex, flags) for regex in regexes]
			self.fields = fields
		except re.error, e:
			dprint(WARNING, "Couldn't compile expression for search.",
				key, e)

			self.regexes = []	
			self.fields = []
		
		if self.indexed_search:
			self.on_indexed_search(regexes, excl_regexes, fields, excl_fields, 
				scope, case_sensitive, proximity, is_word_proximity)

		else:
			self.on_sword_search(regexes, excl_regexes, fields, excl_fields, 
				scope, case_sensitive)

	def on_indexed_search(self, regexes, excl_regexes, fields, excl_fields, 
		scope, case_sensitive, proximity, is_word_proximity):
		"""This is what does the main bit of searching."""
		assert self._has_index()
		last_time = [time.time()]
		def index_callback(value):#, userdata):
			# calling GUI functions here is quite expensive (under linux,
			# takes twice as long if you do it always), so only do it every
			# 0.1 seconds
			if time.time() - last_time[0] > 0.1:
				self.progressbar.SetValue(value[1])
				
				guiconfig.app.Yield()
				last_time[0] = time.time()

			return not self.stop
		
		search_type = COMBINED
		self.numwords = len(regexes)
		succeeded = True
		if case_sensitive:
			search_type |= index.CASESENSITIVE
		
		try:
			self.search_results = self.index.Search(
				regexes, excl_regexes, fields, excl_fields, 
				search_type, searchrange=scope,
				progress=index_callback,
				proximity=proximity, is_word_proximity=is_word_proximity
			)

		except SearchException, myexcept:
			wx.MessageBox(myexcept.message, _("Error in search"), parent=self)
			succeeded = False
		
		except SpellingException, spell:
			wx.MessageBox(u"%s\n%s" % (
				_("The following words were not found in this %s:") 
					% self.book.noun, 
				unicode(spell)
			), _("Unknown word"),
				parent=self
			)
		
			succeeded = False

		else:
			self.hits = len(self.search_results)
			if self.hits == 0:
				succeeded = False

		if not succeeded:
			self.search_label.Label = (
				"%s, %s, %s" % (
					_("%d references found") % 0, 
					i18n.ngettext(
						_("1 word"),
						_("%d words") % self.numwords,
						self.numwords
					),
					_("%d hits") % 0
				)
			)
				
			wx.CallAfter(self.clear_list)
			return

		self.search_results = index.RemoveDuplicates(self.search_results)
		
		self.search_label.Label = (
			"%s, %s, %s" % (
				i18n.ngettext(
					_("1 reference found"), 
					_("%d references found") % len(self.search_results),
					len(self.search_results)),
				i18n.ngettext(
					_("1 word"),
					_("%d words") % self.numwords,
					self.numwords
				),
				i18n.ngettext(
					_("1 hit"),
					_("%d hits") % self.hits,
					self.hits
				)				
			)
		)
		
		self.insert_results()

	def on_sword_search(self, regexes, excl_regexes, fields, excl_fields, 
		scope, case_sensitive):
		"""This is what does the main bit of searching."""
		def callback(value, userdata):
			self.progressbar.SetValue(value)
			guiconfig.app.Yield()
			return not self.stop

		if not self.book.mod:
			wx.CallAfter(self.clear_list)
			return
		
		#Create searcher, and set percent callback to callback
		self.searcher = self.get_sword_searcher()(self.book)
		self.searcher.callback = callback

		if fields or excl_fields:
			wx.MessageBox(
				_("You cannot search on fields in unindexed search"),
				_("Error"),
				parent=self
			)
			return
		
		self.numwords = len(regexes)
		if not regexes:
			self.search_results = []
		

		# set the previous results to the scope, so that we only search in it
		search_scope = scope
		for item in regexes:
			self.search_results = self.searcher.Search(
				to_str(item, self.book.mod),
				SWREGEX, search_scope, case_sensitive
			)
			# TODO: ;'s don't cut it - in the ISBE, they are often used
			search_scope = "; ".join(self.search_results)
	
		# If we need to exclude, do another search through the scope 
		# Then remove duplicates
		for item in excl_regexes:
			if not self.search_results: # or self.stop:
				break

			exclude_list = self.searcher.Search(
				to_str(item, self.book.mod),
				SWREGEX,
				"; ".join(self.search_results), 
				case_sensitive
			)
			
			for excl in exclude_list:
				if excl in self.search_results:
					self.search_results.remove(excl)

		self.hits = len(self.search_results)
		if self.hits == 0:
			self.search_label.Label = "%s, %s" % (
				_("%d references found") % 0,
				i18n.ngettext(
					_("1 word"),
					_("%d words") % self.numwords,
					self.numwords
				),
			)
			
				
			wx.CallAfter(self.clear_list)
			return
		
		
		self.search_label.Label = "%s, %s" % (
			i18n.ngettext(
				_("1 reference found"), 
				_("%d references found") % self.hits,
				self.hits
			),
			i18n.ngettext(
				_("1 word"),
				_("%d words") % self.numwords,
				self.numwords
			),
		)
		
		# Update UI
		self.insert_results()

	def clear_list(self):
		self.search_button.SetLabel(_("&Search"))
		self.show_progress_bar(False)

		#Clear list
		self.verselist.set_data([_("Reference"), _("Preview")], length=0)

		self.versepreview.regexes = []
		self.versepreview.fields = []
		self.versepreview.SetReference(None)
		self.save_results_button.Disable()

		#insert columns
		#self.verselist.InsertColumn(0, "Reference")
		#self.verselist.InsertColumn(1, "Preview")
		self.set_title()
	
	def set_title(self):
		text = _("%(version)s search - %(numresults)s") % dict(
			version=self.version,
			numresults=i18n.ngettext(
				_("1 reference found"), 
				_("%d references found") % self.verselist.ItemCount,
				self.verselist.ItemCount
			),
		)
		
		guiconfig.mainfrm.set_pane_title(self.id, text)

	@guiutil.frozen
	def insert_results(self):
		text = self.search_results
		self.search_button.SetLabel(_("&Search"))

		self.verselist.results = self.search_results

		#Clear list
		self.clear_list()
		self.verselist.set_data(
			[_("Reference"), _("Preview")], 
			length=len(text)
		)
		self.set_title()

		self.versepreview.regexes = self.regexes	
		self.versepreview.fields = self.fields
		
		self.versepreview.SetReference(text[0])
		self.save_results_button.Enable()
		
		
		
		
	def on_search_type(self, evt):
		search_config["indexed_search"] = not evt.GetSelection()
		self.show_keyboard_button(shown=search_config["indexed_search"])
		self.check_for_index()
		

	def generate_index(self, event=None):
		if(self.index):
			self.index = None
			error = index.DeleteIndex(self.version)
			if error:
				wx.MessageBox(error, parent=self)
			else:
				self.set_index_available(False)
				self.show_keyboard_button(shown=False)				
				self.search_button.Disable()
				
		else:
			self.build_index(self.version)
			
			

	def build_index(self, version):
		def callback(value):
			self.progressbar.SetValue(value[1])
			continuing, skip = p.Update(value[1], _("Processing %s") % value[0])
			wx.GetApp().Yield()
			return continuing

		p = wx.ProgressDialog(_("Indexing %s") % version, _("Preparing"), 
			parent=self, style=wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_AUTO_HIDE )

		p.Size = (400, -1)
		p.Show()
		#self.show_progress_bar()

		error = None
		try:
			#create index
			try:
				self.index = self.index_type(version, callback)
			except index.Cancelled:
				self.show_keyboard_button(False)
				return None

			except index.BadBook, e:
				self.index = e.index
				error = unicode(e)
			
			self.set_index_available(True)
			self.show_keyboard_button()
			

			#write it to file

			def index_callback(value):
				# calling GUI functions here is quite expensive (under linux,
				# takes twice as long if you do it always), so only do it every
				# 0.1 seconds
				if time.time() - last_time[0] > 0.1:
					continuing, skip = p.Update(value[1], 
						_("Writing %s") % value[0])
				
					self.progressbar.SetValue(value[1])
					
					guiconfig.app.Yield()
					last_time[0] = time.time()
		                                                                           
					return continuing
				return True

			p.Show()
			
			last_time = [time.time()]
			self.index.WriteIndex(progress=index_callback)
			

		finally:
			if error:
				wx.MessageBox(unicode(error), "Error on indexing", parent=self)
		
			#self.show_progress_bar(False)
			p.Hide()
			p.Destroy()

	def _has_index(self):
		"""Does the current module have an index?

		Note that this assumes that the index has been loaded correctly.
		"""
		return self.index and self.index.version == self.version

	@property
	def indexed_search(self):
		"""Gets the type of search to be used.

		This will be a Sword replacement if an indexed search is requested
		and the module doesn't have an index.
		Otherwise, it will be the global search type.
		"""
		indexed_search = search_config["indexed_search"]
		if indexed_search and not self._has_index():
			indexed_search = False
		return indexed_search
	
	@property
	def book(self):
		return biblemgr.bible
	
	@property
	def index_type(self):
		return index.Index
	
	@property
	def title(self):
		return _(self.id)
	
	@property
	def template(self):
		return None

	def get_proximity_options(self):
		proximity = int(self.options_panel.proximity.GetValue())
		is_word_proximity = self.options_panel.proximity_type.Selection == 0
		return proximity, is_word_proximity
		
	def get_sword_searcher(self):
		return Searcher

	def search_list_format_text(self, text):
		return GetBestRange(text, abbrev=True, userInput=False, userOutput=True)

class SearchList(virtuallist.VirtualListCtrlXRC):
	def __init__(self):
		self.results = []
		self.parent = None
		super(SearchList, self).__init__()

	def get_data(self, idx, col):
		assert self.parent, "Parentless search list :("
		template = VerseTemplate(body=u"$text ")#, headings=u"")
		
	
		if col == 0:
			return self.parent.search_list_format_text(self.results[idx])

		
		biblemgr.temporary_state(biblemgr.plainstate)
		self.parent.book.templatelist.append(template)
		try:
			item = self.results[idx]
			ref_parts = item.split(" - ")
			reference = ref_parts.pop(0)
			end_reference = None
			if ref_parts:
				end_reference = ref_parts[0]
			

			content = self.parent.book.GetReference(
					reference, end_ref=end_reference, stripped=True
				)
			
			# remove non-canonical headings
			content = re.sub('<h6 class="heading" canonical="false">.*?</h6>',
						 '', content)
			content = re.sub(
				'<h6 class="heading" canonical="true">(.*?)</h6>', r'\1', 
				content)


						 
			bibletext = string_util.RemoveWhitespace(content)
			
			# trim to 500, otherwise it can be very slow on long entries		
			if len(bibletext) > 500:
				bibletext = bibletext[:500] + "..."

			return bibletext

		finally:
			biblemgr.restore_state()
			self.parent.book.templatelist.pop()

class BibleSearchPanel(SearchPanel):
	def __init__(self, parent):
		super(BibleSearchPanel, self).__init__(parent)
		self.save_results_button.Show()

	def _post_init(self):
		super(BibleSearchPanel, self)._post_init()
		self.save_results_button.Bind(wx.EVT_BUTTON, self._save_results)

	def _save_results(self, event):
		manage_topics_frame = ManageTopicsFrame(guiconfig.mainfrm)
		manage_topics_frame.save_search_results(
				self.searchkey.Value, self.search_results
			)
		manage_topics_frame.Show()
	
	def get_sword_searcher(self):
		return VerseKeySearcher

class GenbookSearchPanel(SearchPanel):
	id = N_("Other Book Search")
	@property
	def book(self):
		return biblemgr.genbook
	
	@property
	def index_type(self):
		return index.GenBookIndex

	@property
	def template(self):
		return VerseTemplate(
			u'<p><a href="genbook:$reference_encoded"><small><em>'
			'$breadcrumbed_reference</em></small></a> $text'
		)

	def search_list_format_text(self, text):
		mod = self.book.mod
		key = TK(mod.getKey(), mod)
		items = []
		for item in text.split(" - "):
			key.text = item
			items.append(key.breadcrumb(delimiter=">"))
		return " - ".join(items)
	
	def go_to_reference(self, idx):
		item = self.verselist.results[idx]
		mod = self.book.mod
		
		ref_parts = item.split(" - ")
		reference = ref_parts.pop(0)
		
		key = TK(mod.getKey(), mod)
		key.text = reference
		
		guiconfig.mainfrm.genbooktext.SetReference(key)
			
	
	def get_scope(self):
		return None
	
	def construct_option_panels(self, parent):
		self.options_panel = xrcOptionsPanel(parent)

		# we have entries, not verses
		self.options_panel.proximity_type.SetString(1, _("Entries"))
		parent.Sizer.Add(self.options_panel, 1, wx.GROW)
		
		self.options_panel.gui_search_type.Bind(
			wx.EVT_CHOICE, self.on_search_type)

class DictionarySearchPanel(SearchPanel):
	id = N_("Dictionary Search")
	@property
	def book(self):
		return biblemgr.dictionary
	
	@property
	def index_type(self):
		return index.DictionaryIndex

	def search_list_format_text(self, text):
		assert len(text.split(" - ")), "Can't have ranges in dictionary"
		return text
	
	def go_to_reference(self, idx):
		item = self.verselist.results[idx]
		mod = self.book.mod
		
		ref_parts = item.split(" - ")
		reference = ref_parts.pop(0)
		
		guiconfig.mainfrm.UpdateDictionaryUI(reference)
	
	def get_scope(self):
		return None
	
	def construct_option_panels(self, parent):
		self.options_panel = xrcOptionsPanel(parent)
		containing_sizer = self.options_panel.proximity_type.ContainingSizer
		self.options_panel.options_panel.Sizer.Detach(containing_sizer)
		parent.Sizer.Add(self.options_panel, 1, wx.GROW)
		for item in containing_sizer.Children:
			item.Window.Destroy()
		
		self.options_panel.gui_search_type.Bind(
			wx.EVT_CHOICE, self.on_search_type)
	
	def get_proximity_options(self):
		# we must be all in the same entry
		return 1, False

class CommentarySearchPanel(BibleSearchPanel):
	id = N_("Commentary Search")
	@property
	def book(self):
		return biblemgr.commentary

	@property
	def index_type(self):
		return index.CommentaryIndex

	def construct_option_panels(self, parent):
		super(CommentarySearchPanel, self).construct_option_panels(parent)

		# default is within 1 verse
		self.options_panel.proximity_type.Selection = 1
		self.options_panel.proximity.Value = 1
	
	@property
	def template(self):
		return VerseTemplate(
			body=u"$text"
		)
