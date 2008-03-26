#wx imports
import wx
from wx import xrc

from util import osutils
#from util.util import *
from util import util
from backend.bibleinterface import biblemgr
from xrc.search_xrc import *

import config
import guiconfig
import search
from search import REGEX, PHRASE, CASESENSITIVE, MULTIWORD, COMBINED
from search import SearchException, SpellingException, RemoveDuplicates
from swlib.pysw import VK, GetBestRange, Searcher, SWMULTI, SWPHRASE, SWREGEX
from gui import guiutil
from util.debug import dprint, WARNING
from gui import virtuallist
from gui import reference_display_frame
from events import SEARCH
from util.configmgr import config_manager



#TODO: better status bar: text overlay
#						  status messages

#class MyThread(threading.Thread):
#	def __init__(self, dialog):
#		self.dialog = dialog
#		threading.Thread.__init__(self)
#
#	def run(self):
#		self.dialog.on_search2()

search_config = config_manager.add_section("Search")
search_config.add_item("disappear_on_doubleclick", True, item_type=bool)
search_config.add_item("search_type", COMBINED, item_type=int)


search_items = (COMBINED, MULTIWORD, PHRASE, REGEX, SWMULTI, SWPHRASE, SWREGEX)
needs_index  = (1, 		  1,	     1,      1,     0,       0,        0) 

needs_index = dict(zip(search_items, needs_index))

sword_replacement_search = {
	COMBINED: SWMULTI,
	MULTIWORD: SWMULTI,
	PHRASE: SWPHRASE,
	REGEX: SWREGEX
}

		
class SearchPanel(xrcSearchPanel):
	def __init__(self, parent):#, search_type=SWMULTI):
		super(SearchPanel, self).__init__(parent)
		#self.search_type = search_type
		

		if osutils.is_gtk():
			self.Bind(wx.EVT_WINDOW_CREATE, self.on_create)
		else:
			wx.CallAfter(self.on_create)

		self.search_results = ""

		self.searching = False
		self.index = None
		self.version = None
		self.stop = False

		# if search panel is on screen at startup, on_show and set_version will
		# both be called. Then if there is no index, it will prompt twice.
		# This flag is false only before the end of the first call to
		# set_version
		self.has_started = False
		self.search_on_show = False
	
	def on_create(self, event=None):
		self.Unbind(wx.EVT_WINDOW_CREATE)
		wx.CallAfter(self._post_init)
		if event:
			event.Skip()

		return True
	
	def on_list(self, event):
		item_text = self.verselist.GetItemText(event.m_itemIndex)
		self.versepreview.SetReference(str(item_text))
	
	
	def search_and_show(self, key=""):
		self.searchkey.SetValue(key)

		# If we call on_search from here, then it may search before asking
		# the user about building the search index, so instead we call it
		# from on_show after checking the index.
		self.show(search_on_show=True)
	
	def show(self, search_on_show=False):
		self.search_on_show = search_on_show
		guiconfig.mainfrm.show_panel("Search")
	
	def on_show(self, toggle):
		if self.version is None:
			self.genindex.Disable()
	
		if not toggle: 
			return

		panel = guiconfig.mainfrm.aui_mgr.GetPane("Search")
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

		self.genindex.Enable(version is not None)
		

		if(guiconfig.mainfrm.is_pane_shown("Search") and self.has_started):
			self.check_for_index()

		self.search_label.Label = "0 verses found"

		wx.CallAfter(self.clear_list)

		self.set_title()
		self.has_started = True
	
	def check_for_index(self):
		self.set_gui_search_type(search_config["search_type"])
		if not needs_index[search_config["search_type"]]:
			#self.genindex.SetLabel("Unindex")
			self.search_button.Enable(biblemgr.bible.version is not None)
			if not biblemgr.bible.version:
				wx.MessageBox("You don't have a current bible version, "
				"so you cannot search at the moment", "No current version")
			
			return
		

		if self.index and self.index.version == self.version:
			self.genindex.SetLabel("Unindex")
			self.search_button.Enable()
		
			return

		if(self.version and search.IndexExists(self.version)):
			busy_info = wx.BusyInfo("Reading search index...")
			self.index = search.ReadIndex(self.version)
			self.genindex.SetLabel("Unindex")
			self.search_button.Enable()
			
		else:
			self.search_button.Enable()
			
			self.index = None
		
			if not self.version:
				wx.MessageBox("You don't have a current bible version, "
				"so you cannot search at the moment", "No current version")
				return
			self.genindex.SetLabel("Index")

			msg = "Search index does not exist for module %s. " \
				"Indexing will make search much faster. " \
				"Create Index?" % self.version 
			create = wx.MessageBox(msg, "Create Index?", wx.YES_NO)
			if create == wx.YES:
				self.index = self.build_index(self.version)
			else:
				self.set_gui_search_type(self.search_type)

	def on_select(self, event):
		item_text = self.verselist.GetItemText(event.m_itemIndex)
		
		guiconfig.mainfrm.set_bible_ref(item_text, source=SEARCH)
		if search_config["disappear_on_doubleclick"]:
			self.on_close()
			
	def _post_init(self):
		self.set_gui_search_type(search_config["search_type"])

		self.search_button.SetLabel("&Search")
	
		self.search_splitter.SetSashGravity(0.5)
		self.search_splitter.SetSashPosition(
				self.search_splitter.ClientSize[1]/2
		)

		font = self.search_label.Font
		font.SetWeight(wx.FONTWEIGHT_BOLD)
		self.search_label.Font = font

		# Do all init here
		#self.Fit()
		#self.GetContainingSizer().ContainingWindow.Fit()
		
		# Do binding
		self.Bind(wx.EVT_BUTTON, self.on_search_button, self.search_button)
		self.Bind(wx.EVT_BUTTON, self.on_close, id=wx.ID_CLOSE)
		
		self.gui_search_type.Bind(wx.EVT_CHOICE, self.on_search_type)

		self.oldtestament.Bind(wx.EVT_RADIOBUTTON, self.old_testament)
		self.newtestament.Bind(wx.EVT_RADIOBUTTON, self.new_testament)
		self.wholebible.Bind(wx.EVT_RADIOBUTTON, self.whole_bible)
		self.custom_range.Bind(wx.EVT_TEXT, self.on_custom_changed)
		
		
		self.verselist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		self.verselist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_select)
		self.range_top.Bind(wx.EVT_CHOICE, self.on_range_top)
		self.range_bottom.Bind(wx.EVT_CHOICE, self.on_range_bottom)
		self.genindex.Bind(wx.EVT_BUTTON, self.generate_index)

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
		self.biblebooks = []

		for book in VK.books:
			bookname = book.bookname
			self.biblebooks.append(bookname)
			self.range_top.Append(bookname)
			self.range_bottom.Append(bookname)

		self.range_top.SetSelection(0)
		number = self.range_bottom.GetCount()
		self.range_bottom.SetSelection(number-1)
		self.update_boxes(self.wholebible)

	def set_gui_search_type(self, search_type):
		"""Sets the search type to be displayed in the GUI."""
		for index, item in enumerate(search_items):
			if item == search_type:
				self.gui_search_type.SetSelection(index)
		

			
	def on_close(self, event=None):
		guiconfig.mainfrm.show_panel("Search", False)

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
			print "Starting search"
			self.searching = True
			self.search_button.SetLabel("&Stop")
			
			key = str(self.searchkey.GetValue())
			if not key: 
				self.search_label.Label = "0 verses found"

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
		
			self.show_progress_bar()
		    
			if self.wholebible.Value:
				scope = None

			else:
				# If custom range, use it
				scope = str(self.custom_range.GetValue())
			
			excludestr = str(self.exclude.GetValue())
			exclude = excludestr
			if not excludestr:
				exclude = None
			
			
			case_sensitive = self.case_sensitive.GetValue()

			self.perform_search(key, scope, exclude, case_sensitive)

		finally:
			self.show_progress_bar(False)
			print "Stopping search"
			self.searching = False
			self.search_button.SetLabel("&Search")
			

	def perform_search(self, key, scope, exclude, case_sensitive):
		if needs_index[self.search_type]:
			self.on_indexed_search(key, scope, exclude, case_sensitive)
		else:
			self.on_sword_search(key, scope, exclude, case_sensitive)
	
	def on_indexed_search(self, key, scope, exclude, case_sensitive):
		"""This is what does the main bit of searching."""
		assert self._has_index()
		def index_callback(value):#, userdata):
			#dprint(MESSAGE, "callback status", *value)
			self.progressbar.SetValue(value[1])
			#wx.SafeYield(self.search_button)
			guiconfig.app.Yield()
			return not self.stop


		proximity = int(self.proximity.GetValue())
		search_type = search_config["search_type"]
		self.numwords = len(key.split())
		succeeded = True
		if case_sensitive:
			search_type |= search.CASESENSITIVE
		
		try:
			self.search_results = self.index.Search(key, search_type, 
			searchrange=scope, progress=index_callback, excludes=exclude,
			proximity=proximity)

		except SearchException, myexcept:
			wx.MessageBox(str(myexcept), "Error in search")
			succeeded = False

		except SpellingException, spell:
			wx.MessageBox("The following words were not found in the module:"
				"\n%s" % str(spell), "Unknown word")
			
			succeeded = False

		else:
			self.hits = len(self.search_results)
			if self.hits == 0:
				succeeded = False

		if not succeeded:
			self.search_label.Label = (
				"0 verses found, %s, 0 hits" % 
					util.pluralize("word", self.numwords)
			)
				
			wx.CallAfter(self.clear_list)
			return
		
		
		if self.hits > 20000:
			wx.MessageBox("Your search gave %d hits, which is too many\n"
				"Try a more specific search." % self.hits, 
				"Too many hits")

			self.search_label.Label = (
				"0 verses found, %s, %s" % (
					util.pluralize("word", self.numwords),
					util.pluralize("hit", self.hits),
					)
			)
			
			wx.CallAfter(self.clear_list)
			return

		self.search_results = search.RemoveDuplicates(self.search_results)
		self.insert_results()

	def on_sword_search(self, key, scope, exclude, case_sensitive):
		"""This is what does the main bit of searching."""
		def callback(value, userdata):
			self.progressbar.SetValue(value)
			guiconfig.app.Yield()
			return not self.stop

		#Create searcher, and set percent callback to callback
		self.searcher = Searcher(biblemgr.bible)
		self.searcher.callback = callback

	    # If custom range, use it
		self.numwords = len(key.split())
		self.search_results = self.searcher.Search(key, 
			search_config["search_type"], scope, case_sensitive)

		# If we need to exclude, do another search through the scope 
		# Then remove duplicates
		if exclude:
			for string in exclude.split(" "):
				if not self.search_results: # or self.stop:
					break

				exclude_list = self.searcher.Search(string, 
					search_config["search_type"],
					"; ".join(self.search_results), 
					case_sensitive)
				
				for excl in exclude_list:
					if excl in self.search_results:
						self.search_results.remove(excl)

		self.hits = len(self.search_results)
		if self.hits == 0:
			self.search_label.Label = (
				"0 verses found, %s, 0 hits" % 
					util.pluralize("word", self.numwords)
			)
			
				
			wx.CallAfter(self.clear_list)
			return
		
		
		if self.hits > 20000:
			wx.MessageBox("Your search gave %d hits, which is too many\n"
				"Try a more specific search." % self.hits, 
				"Too many hits")

			self.search_label.Label = (
				"0 verses found, %s, %s" % (
					util.pluralize("word", self.numwords),
					util.pluralize("hit", self.hits),
					)
			)
				
			
			wx.CallAfter(self.clear_list)
			return

		# Update UI
		self.insert_results()

	def clear_list(self):
		self.search_button.SetLabel("Search")
		self.show_progress_bar(False)

		#Clear list
		self.verselist.set_data("Reference Preview".split(), length=0)

		self.versepreview.SetReference(None)

		#insert columns
		#self.verselist.InsertColumn(0, "Reference")
		#self.verselist.InsertColumn(1, "Preview")
		self.set_title()
	
	def set_title(self):
		text = "%s Bible search - %s" % (self.version,
			util.pluralize("result", self.verselist.ItemCount))		
		guiconfig.mainfrm.set_pane_title("Search", text)

	@guiutil.frozen
	def insert_results(self):
		text = self.search_results
		self.search_button.SetLabel("Search")

		#make this plain
		#template = VerseTemplate(body = "$text ")

		#Set Reference to shortened version
		#for val, item in enumerate(text):
		#	#vk = SW.VerseKey(item)
		#	text[val] = GetBestRange(item, abbrev=True)

		self.verselist.results = self.search_results#text

		#biblemgr.temporary_state(biblemgr.plainstate)
		#biblemgr.bible.templatelist.push(template)
		#for val, item in enumerate(text):
		#	bibletext = br2nl(biblemgr.bible.GetReference(item))
		#	bibletext = KillTags(util.ReplaceUnicode(bibletext))
		#	bibletext = RemoveWhitespace(bibletext)
		#	data[val] = (item, bibletext)
		#biblemgr.restore_state()
		#biblemgr.bible.templatelist.pop()

		#Clear list
		self.clear_list()
		self.verselist.set_data("Reference Preview".split(), length=len(text))
		#insert data	   
		#for key, mydata in data.iteritems():
		#	index = self.verselist.InsertStringItem(sys.maxint, mydata[0])
		#	self.verselist.SetStringItem(index, 1, mydata[1])
		#	self.verselist.SetItemData(index, key)
		#self.verselist.SetColumnWidth(0, wx.LIST_AUTOSIZE)
		#self.verselist.SetColumnWidth(0, self.verselist.GetColumnWidth(0) + 5)

		#self.verselist.SetColumnWidth(1, wx.LIST_AUTOSIZE)
		
		self.set_title()
		self.search_label.Label = (
			"%s found, %s, %s" % (
				util.pluralize("reference", len(text)),
				util.pluralize("word", self.numwords),
				util.pluralize("hit", self.hits),
			)
		)
		self.versepreview.SetReference(text[0])
		
		
		
		
	def on_search_type(self, evt):
		search_config["search_type"] = search_items[evt.GetSelection()]
		self.check_for_index()
		
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
		

	def generate_index(self, event=None):
		if(self.index):
			self.index = None
			error = search.DeleteIndex(self.version)
			if error:
				wx.MessageBox(error)
			else:
				self.genindex.SetLabel("Index")
				self.search_button.Disable()
				
		else:
			self.index = self.build_index(self.version)
			
			

	def build_index(self, version):
		def callback(value):
			self.progressbar.SetValue(value[1])
			continuing, skip = p.Update(value[1], "Indexing %s" % value[0])
			wx.GetApp().Yield()
			return continuing

		p = wx.ProgressDialog("Indexing %s" % version, "Preparing", 
			style=wx.PD_APP_MODAL|wx.PD_CAN_ABORT|wx.PD_AUTO_HIDE )

		p.Show()
		self.show_progress_bar()

		try:
			#create index
			try:
				index = search.Index(version, callback)
			except search.Cancelled:
				return None
			
			#write it to file
			index.WriteIndex()
			self.search_button.Enable()
			self.genindex.SetLabel("Unindex")
			
			return index
		finally:
			self.show_progress_bar(False)
			p.Hide()
			p.Destroy()

	def _has_index(self):
		"""Does the current module have an index?

		Note that this assumes that the index has been loaded correctly.
		"""
		return self.index and self.index.version == self.version

	@property
	def search_type(self):
		"""Gets the type of search to be used.

		This will be a Sword replacement if an indexed search is requested
		and the module doesn't have an index.
		Otherwise, it will be the global search type.
		"""
		search_type = search_config["search_type"]
		if needs_index[search_type] and not self._has_index():
			search_type = sword_replacement_search[search_type]
		return search_type

class SearchList(virtuallist.VirtualListCtrlXRC):
	def __init__(self):
		self.results = []
		super(SearchList, self).__init__()

	def get_data(self, idx, col):
		template = util.VerseTemplate(body = "$text ")
	
		if col == 0:
			return GetBestRange(self.results[idx], abbrev=True)

		
		biblemgr.temporary_state(biblemgr.plainstate)
		biblemgr.bible.templatelist.push(template)
		try:
			item = self.results[idx]
			bibletext = util.br2nl(biblemgr.bible.GetReference(item))
			bibletext = util.KillTags(util.ReplaceUnicode(bibletext))
			bibletext = util.RemoveWhitespace(util.remove_amps(bibletext))
			return bibletext

		finally:
			biblemgr.restore_state()
			biblemgr.bible.templatelist.pop()
		
	
	
