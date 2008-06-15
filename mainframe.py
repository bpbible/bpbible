import sys
import os


from util.debug import dprint, MESSAGE, ERROR, is_debugging

import wx
from wx import xrc 

from wx.lib.wordwrap import wordwrap

dprint(MESSAGE, "importing sword")
from swlib import pysw
dprint(MESSAGE, "/importing sword")

dprint(MESSAGE, "Other imports")

from backend.bibleinterface import biblemgr
from backend import filterutils


from bibleframe import BibleFrame
from bookframe import CommentaryFrame
from bookframe import DictionaryFrame
from displayframe import IN_MENU
from genbookframe import GenBookFrame

from auilayer import AuiLayer

from util.observerlist import ObserverList
from util import osutils
#import mySearchDialog
import versetree
from copyverses import CopyVerseDialog
import config
import guiconfig
from module_tree import ModuleTree
from pathmanager import PathManager
from gui import htmlbase
from gui import guiutil
from gui.guiutil import bmp
from gui.menu import Separator
from gui.htmlbase import HtmlBase

from search.searchpanel import SearchPanel

from fontchoice import FontChoiceDialog 
from versecompare import VerseCompareFrame
from htmlide import HtmlIde
from events import BibleEvent, SETTINGS_CHANGED, BIBLE_REF_ENTER, HISTORY
from events import LOADING_SETTINGS, VERSE_TREE
from history import History, HistoryTree
from util.configmgr import config_manager
from install_manager.install_drop_target import ModuleDropTarget

settings = config_manager.add_section("BPBible")

settings.add_item("layout", None, item_type="pickle")
settings.add_item("bibleref", "Genesis 1:1")
settings.add_item("bible", "ESV")
settings.add_item("dictionary", "ISBE")
settings.add_item("dictref", "")
settings.add_item("commentary", "TSK")
settings.add_item("genbook", "Josephus")

settings.add_item("zoom_level", 0)
settings.add_item("copy_verse", "Default",
	item_type="pickle")
settings.add_item("options", None, item_type="pickle")
settings.add_item("size", None, item_type="pickle")
settings.add_item("maximized", False, item_type=bool)
settings.add_item("last_book_directory", "", item_type=str)




dprint(MESSAGE, "/Other imports")

XRC_DIRECTORY = 'xrc'

class MainFrame(wx.Frame, AuiLayer):
	"""MainFrame: The main frame containing everything."""
	def __init__(self, parent):
		super(MainFrame, self).__init__(self, parent, -1, config.name, 
		wx.DefaultPosition, size=(1024, 768))
		
		self.setup()

	def setup(self):
		HtmlBase.override_loading_a_page = True

		dprint(MESSAGE, "Setting up")
	
		guiconfig.mainfrm = self
		self.toplevels = []
		self.currentverse = ""
		self.zoomlevel = 0

		self.bible_observers = ObserverList([
					lambda event: self.bibletext.SetReference(event.ref),
					self.set_title
		
		])

		self.all_observers = ObserverList([
			lambda:self.bible_observers(
				BibleEvent(ref=self.currentverse, settings_changed=True,
				source=SETTINGS_CHANGED)
			),

			lambda:self.dictionarytext.reload(),
			lambda:self.genbooktext.reload()
		])

		biblemgr.bible.observers += self.bible_version_changed
		biblemgr.commentary.observers += self.commentary_version_changed
		biblemgr.dictionary.observers += self.dictionary_version_changed
		biblemgr.on_after_reload += self.on_modules_reloaded
		
		
		#self.Freeze()

		self.lost_focus = False
		self.history = History()
		self.bible_observers += self.add_history_item

		self.load_data()
		self.make_toolbars()
		
		self.create_searchers()
		self.create_aui_items()
		super(MainFrame, self).setup()
		self.set_aui_items_up()
		
		
		self.bind_events()
		self.setup_frames()

		self.bibleref.SetFocus()
		self.buffer = wx.TextCtrl(self)
		self.buffer.Hide()
		
		self.set_menus_up()

		def override_end():
			HtmlBase.override_loading_a_page = False
		
		wx.CallAfter(dprint, MESSAGE, "Constructed")
		wx.CallAfter(override_end)	
		dprint(MESSAGE, "Done first round of setting up")
		self.drop_target = ModuleDropTarget(self)
		self.SetDropTarget(self.drop_target)
		#guiutil.call_after_x(100, self.bibletext.scroll_to_current)
		
		# after three goes round the event loop, set timer for 100ms to scroll
		# to correct place
		# Under GTK, neglecting to do this will mean that it will scroll to
		# the top.
		guiutil.call_after_x(3, wx.CallLater, 100, 
			self.bibletext.scroll_to_current)
		



		
		
	def make_toolbars(self):
	
		dprint(MESSAGE, "Making toolbars")
		
		toolbar_style = wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT

	
	
		toolbars = [
			wx.ToolBar(self, wx.ID_ANY, style=toolbar_style) 
			for _ in range(3)
		]

		(self.main_toolbar, self.zoom_toolbar, 
			self.history_toolbar) = toolbars

		for toolbar in toolbars:
			toolbar.SetToolBitmapSize((16, 16))

		self.tool_back = self.history_toolbar.AddLabelTool(wx.ID_ANY,  
			"Back", bmp("go-previous.png"),
			shortHelp="Go back a verse")
		
		self.tool_forward = self.history_toolbar.AddLabelTool(wx.ID_ANY,  
			"Forward", bmp("go-next.png"),
			shortHelp="Go forward a verse")
			
		self.tool_zoom_in = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			"Zoom In", bmp("magnifier_zoom_in.png"),
			shortHelp="Make text bigger")
			
		self.tool_zoom_default = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			"Default Zoom", bmp("magnifier.png"),
			shortHelp="Return text to default size")
			
		self.tool_zoom_out = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			"Zoom Out", bmp("magifier_zoom_out.png"),
			shortHelp="Make text smaller")
			
		self.bibleref = versetree.VerseTree(self.main_toolbar)
		self.bible_observers += self.bibleref.set_current_verse
		
		self.bibleref.SetSize((140, -1))
		self.main_toolbar.AddControl(self.bibleref)
		
		self.tool_go = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			"Go to verse", bmp("accept.png"),
			shortHelp="Open this verse")
			
		self.tool_search = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			"Bible Search", bmp("find.png"),
			shortHelp="Search in this Bible")
			
		self.tool_copy_verses = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			"Copy Verses", bmp("page_copy.png"),
			shortHelp="Open the Copy Verses dialog")
		
		#self.zoom_toolbar = xrc.XRCCTRL(self, "zoom_toolbar")
		#self.main_toolbar = xrc.XRCCTRL(self, "main_toolbar")
		#self.history_toolbar = xrc.XRCCTRL(self, "history_toolbar")
		
		for toolbar in toolbars:
			toolbar.Realize()

		if osutils.is_win2000():
			# this is what the minimum size should be
			# however, adding controls to toolbars breaks their length :(
			best_size = (
				self.main_toolbar.BestSize[0] + self.bibleref.Size[0] +
				self.main_toolbar.Margins[0], 
				
				-1#self.main_toolbar.BestSize[1]
			)
		else:
			best_size = self.main_toolbar.BestSize

		for toolbar in toolbars:
			toolbar.Bind(wx.EVT_CONTEXT_MENU, self.show_toolbar_popup)
			toolbar.Bind(wx.EVT_RIGHT_UP, self.show_toolbar_popup)

		self.Bind(wx.EVT_CONTEXT_MENU, self.show_toolbar_popup)
		self.Bind(wx.EVT_RIGHT_UP, self.show_toolbar_popup)

		self.toolbars = ([self.main_toolbar, "Navigation", 
							("BestSize", best_size)],
						 [self.zoom_toolbar, "Zoom",
						 	["Hide"]],
						 [self.history_toolbar, "History toolbar",
						 	["Row", 0]])
	
	def load_data(self):
		dprint(MESSAGE, "Loading data")
		
		config_manager.load()
		if settings["options"]:
			for item, value in settings["options"].iteritems():
				biblemgr.set_option(item, value)
				
		if settings["size"]:
			self.SetSize(settings["size"])
		
		if settings["maximized"]:
			self.Maximize(True)
				
		def set_mod(book, mod_name):
			if book.ModuleExists(mod_name):
				book.SetModule(mod_name, notify=False)

		set_mod(biblemgr.bible, settings["bible"])
		set_mod(biblemgr.dictionary, settings["dictionary"])
		set_mod(biblemgr.commentary, settings["commentary"])
		set_mod(biblemgr.genbook, settings["genbook"])
		
		
				
	def save_data(self):
		settings["layout"] = self.save_layout()
		settings["bibleref"] = self.currentverse
		settings["bible"] = biblemgr.bible.version
		settings["commentary"] = biblemgr.commentary.version
		settings["genbook"] = biblemgr.genbook.version
		settings["dictionary"] = biblemgr.dictionary.version

		settings["options"] = biblemgr.save_state()

		settings["size"] = self.Size

		#settings["position"] = self.Position
		
		settings["maximized"] = self.IsMaximized()
		

		try:
		#	if not os.path.exists(config.data_path):
		#		os.makedirs(config.data_path)

			config_manager.save()
		
		except (OSError, EnvironmentError), e:
			wx.MessageBox("OSError on saving settings\n%s" % 
				e.message)

		except Exception, e:
			wx.MessageBox("Error on saving settings\n%s" % 
				e.message)
		
		
			

	def copy(self, text):
		# Under MSW, doesn't like pasting into Word 97 just using clipboard, so
		# use a text control to do it
		# TODO: check if this is still true
		if ( wx.TheClipboard.Open() ):
			if osutils.is_gtk():
				wx.TheClipboard.UsePrimarySelection(False)
		
			tdo = wx.TextDataObject()
			tdo.SetText(text)
			wx.TheClipboard.SetData(tdo)
			wx.TheClipboard.Close()

		else:
			dprint(ERROR, "Could not open the clipboard")
		
		if osutils.is_msw():
			self.buffer.ChangeValue(text)
			self.buffer.SetSelection(-1, -1)
			self.buffer.Copy()


	def create_searchers(self):
		self.search_panel = SearchPanel(self)
		
		self.aui_callbacks = {}
		self.aui_callbacks["Search"] = lambda toggle:wx.CallAfter(
							self.search_panel.on_show, toggle)
		
		self.bible_observers += self.search_panel.versepreview.RefreshUI

		wx.CallAfter(lambda:self.set_search_version(biblemgr.bible.version))

	def create_aui_items(self):
		self.version_tree = ModuleTree(self)
		self.version_tree.on_module_choice += self.set_module

		self.genbooktext = GenBookFrame(self, biblemgr.genbook)

		self.bibletext = BibleFrame(self)
		self.bibletext.SetBook(biblemgr.bible)

		# set a watch on the bibletext to update the reference in text box
		# every time new page is loaded
		self.bibletext.observers += self.set_bible_ref

		self.commentarytext = CommentaryFrame(self, biblemgr.commentary)
		self.dictionarytext = DictionaryFrame(self, biblemgr.dictionary)

		self.dictionary_list = self.dictionarytext.dictionary_list

		self.verse_compare = VerseCompareFrame(self, biblemgr.bible)
		#if settings["verse_comparison_modules"] is not None:
		#	self.verse_compare.modules = settings["verse_comparison_modules"]

		self.history_pane = wx.Panel(self)
		self.history_tree = HistoryTree(self.history_pane, self.history)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.history_tree, 1, wx.GROW)
		self.history_pane.SetSizer(sizer)

	def set_module(self, module, book):
		# if the pane is not shown, show it
		for frame in self.frames:
			if hasattr(frame, "book") and frame.book == book:
				pane = self.get_pane_for_frame(frame)
				if not pane.IsShown():
					self.show_panel(pane.name)	

				break
		
		# set the module afterwards so that the pane size will be correctly
		# set
		book.SetModule(module)	

				
		
	def on_copy_button(self, event=None):
		"""Copy verses to other applications"""

		text = self.bibletext.get_quick_selected()
		
		cvd = CopyVerseDialog(self)
		cvd.ShowModal(text)
		cvd.Destroy()


	def bind_events(self):
		#self.Bind(wx.EVT_KILL_FOCUS, self.OffFocus)
		#self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

		self.Bind(wx.EVT_CLOSE, self.MainFrameClose)
		self.Bind(wx.EVT_MENU, self.on_path_manager, 
			id = xrc.XRCID('pathmanager'))
		
		self.Bind(wx.EVT_MENU, self.on_install_module,
			id=xrc.XRCID('installmodule'))
		
		self.Bind(wx.EVT_MENU, self.load_default_perspective, 
			id=xrc.XRCID('menu_default_layout'))
		
		self.Bind(wx.EVT_MENU, self.on_font_choice,
			id=xrc.XRCID('fontchoice'))
		
		self.Bind(wx.EVT_MENU, self.on_html_ide, 
			id=xrc.XRCID('gui_html_ide'))
		
		self.Bind(wx.EVT_MENU, self.on_widget_inspector, 
			id=xrc.XRCID('gui_widget_inspector'))
			
						
			
		
		self.Bind(wx.EVT_MENU, id = wx.ID_EXIT, handler = self.ExitClick)
		self.Bind(wx.EVT_MENU, id = wx.ID_ABOUT, handler = self.AboutClick)
		
		web_links = dict(
			gui_website="http://bpbible.com",
			gui_documentation="http://code.google.com/p/bpbible/w/list",
			gui_issues="http://code.google.com/p/bpbible/issues/list",
			gui_books="http://www.crosswire.org/sword/modules/index.jsp"
		)
		
		def weblink_handler(weblink):
			def handle_event(event):
				guiutil.open_web_browser(weblink)

			return handle_event
		
		for xrcid, website in web_links.items():
			self.Bind(wx.EVT_MENU, weblink_handler(website), 
				id=xrc.XRCID(xrcid))
			
			
		self.dictionary_list.item_changed += self.DictionaryListSelected

		self.bibleref.Bind(wx.EVT_TEXT_ENTER, self.BibleRefEnter)

		# if it is selected in the drop down tree, go straight there
		# use callafter so that our text in the control isn't changed straight
		# back
		self.bibleref.on_selected_in_tree += lambda text: \
			wx.CallAfter(self.set_bible_ref, text, source=VERSE_TREE)
		
		
		#self.BibleRef.Bind(wx.EVT_COMBOBOX, self.BibleRefEnter)

		self.Bind(wx.EVT_TOOL, self.on_copy_button, 
			self.tool_copy_verses)
			
		
		self.Bind(wx.EVT_TOOL, self.BibleRefEnter, self.tool_go)
		
		self.Bind(wx.EVT_TOOL, lambda x: self.search_panel.show(), 
			self.tool_search)
		
		self.Bind(wx.EVT_TOOL, lambda x:self.zoom(1),
			self.tool_zoom_in)
			
		self.Bind(wx.EVT_TOOL, lambda x:self.zoom(-1),
			self.tool_zoom_out)
		
		self.Bind(wx.EVT_TOOL, lambda x:self.zoom(0),
			self.tool_zoom_default)
			
		self.Bind(wx.EVT_TOOL, lambda x:self.move_history(-1),
			self.tool_back)
		
		#self.Bind(wx.EVT_TOOL, lambda x:self.show_history(),
		#	self.tool_history)
			
			
		self.Bind(wx.EVT_TOOL, lambda x:self.move_history(1),
			self.tool_forward)
		
		self.Bind(wx.EVT_UPDATE_UI, 
			lambda event:event.Enable(self.history.can_back()),
			self.tool_back)
		
		self.Bind(wx.EVT_UPDATE_UI, 
			lambda event:event.Enable(self.history.can_forward()),
			self.tool_forward)
			
			
			
			

		if osutils.is_msw():
			# if we try binding to this under gtk, other key up events 
			# propagate up, so we get them where we shouldn't
			self.Bind(wx.EVT_KEY_UP, self.on_char)

		self.Bind(wx.EVT_ACTIVATE, self.on_activate)

		super(MainFrame, self).bind_events()
	
	def show_history(self):
		self.show_panel("History")
		
		
	#def history_moved(self, history_item):
	#	self.set_bible_ref(history_item.ref, source=HISTORY)
	def add_history_item(self, event):
		if event.source != HISTORY:
			self.history.new_location(event.ref)

	def move_history(self, direction):
		history_item = self.history.go(direction)
		self.set_bible_ref(history_item.ref, source=HISTORY)
	
	def on_html_ide(self, event):
		ide = HtmlIde(self)
		ide.Show()
		
	def on_widget_inspector(self, event):
		wx.GetApp().ShowInspectionTool()
	
	def on_path_manager(self, event):
		PathManager(self).ShowModal()
	
	def on_install_module(self, event):
		fd = wx.FileDialog(self, 
			wildcard="Installable books (*.zip)|*.zip",
			style=wx.FD_DEFAULT_STYLE|wx.FD_MULTIPLE|wx.FD_MULTIPLE|wx.FD_OPEN,
			defaultDir=settings["last_book_directory"], message="Choose books"
		)

		if fd.ShowModal() == wx.ID_OK:
			self.drop_target.handle_dropped_files(fd.Paths)
			settings["last_book_directory"]	= fd.GetDirectory()

		fd.Destroy()
			
	
	def on_modules_reloaded(self, biblemgr):
		# as this will have refreshed the manager, refresh everything
		self.version_tree.recreate()
		self.fill_options_menu()

		self.refresh_all_pages()

	def on_font_choice(self, event):
		dialog = FontChoiceDialog(self, config_manager["Html"]["font_name"], 
								   config_manager["Html"]["base_text_size"])
		dialog.ShowModal()

		self.refresh_all_pages()

	def zoom(self, direction):	
		htmlbase.zoom(direction)

		self.refresh_all_pages()

	def get_menu(self, label):
		for menu, menu_name in self.MenuBar.Menus:
			if menu_name == label:
				break
		else:
			menu = None
		return menu
	

	def set_menus_up(self):
		#self.edit_menu
		self.options_menu = self.get_menu("Display")
		assert self.options_menu, "Display menu could not be found"
		self.fill_options_menu()
		
		
		self.windows_menu = self.get_menu("Window")
		assert self.windows_menu, "Window menu could not be found"
		
		for item in self.windows_menu.MenuItems:
			if item.Label == "Toolbars":
				self.toolbar_menu = item.SubMenu
				break
		else:
			assert False, "Toolbars menu could not be found"
		
				
		for pane in self.aui_mgr.GetAllPanes():
			if pane.name in ("Bible",):
				continue

			if pane.IsToolbar(): 
				item = self.toolbar_menu.AppendCheckItem(wx.ID_ANY, pane.name,
					help="Show the %s toolbar"%pane.name)
			else:
				item = self.windows_menu.AppendCheckItem(wx.ID_ANY, pane.name,
					help="Show the %s pane"%pane.name)

			if pane.IsShown():
				item.Check()

			self.Bind(wx.EVT_MENU, self.on_window, item)
		
		for idx, frame in enumerate(self.frames):
			if not frame.has_menu: continue
			#items = frame.get_menu_items()
			items = [x for (x, where_shown) in frame.get_menu_items() 
				if where_shown & IN_MENU]
			
			menu = self.make_menu(items)

			self.MenuBar.Insert(2+idx, menu, frame.title)

		if not is_debugging():
			for idx, (menu, menu_name) in enumerate(self.MenuBar.Menus):
				if menu_name == "Debug":
					self.MenuBar.Remove(idx)
					break
			#else:
			#	menu = None
		
	
	def make_menu(self, items, is_popup=False):
		menu = wx.Menu()
		for item in items:
			if item == Separator:
				menu.AppendSeparator()
				continue

			item.create_item(self, menu, is_popup=is_popup)
		return menu
	
	def fill_options_menu(self):
		while self.options_menu.MenuItems:
			self.options_menu.DestroyItem(
				self.options_menu.FindItemByPosition(0)
			)

		options = biblemgr.get_options()
		for option, values in options:
			help_text = biblemgr.get_tip(option)
		
			if set(values) == set(("Off", "On")):
				item = self.options_menu.AppendCheckItem(
					wx.ID_ANY, 
					option, 
					help=help_text
				)

				if biblemgr.options[option] == "On":
					item.Check()
				
				self.Bind(wx.EVT_MENU, self.on_option, item)
			else:
				sub_menu = wx.Menu("")
				
			
				for value in values:
					item = sub_menu.AppendRadioItem(wx.ID_ANY, value, 
						help=help_text)
					if biblemgr.options[option] == value:
						item.Check()
					self.Bind(wx.EVT_MENU, self.on_option, item)
				
				item = self.options_menu.AppendSubMenu(sub_menu, option, 
					help=help_text)
				self.Bind(wx.EVT_MENU, self.on_option, item)

		if options:
			self.options_menu.AppendSeparator()

		strongs_headwords = self.options_menu.AppendCheckItem(
			wx.ID_ANY,
			"Use Strong's headwords",
			"Display Strong's numbers using the transliterated text"
		)

		cross_references = self.options_menu.AppendCheckItem(
			wx.ID_ANY,
			"Expand cross-references",
			"Display cross references partially expanded"
		)
		

		self.Bind(wx.EVT_MENU, self.toggle_headwords, strongs_headwords)
		self.Bind(wx.EVT_MENU, self.toggle_expand_cross_references, 
			cross_references)
		
		filter_settings = config_manager["Filter"]
		strongs_headwords.Check(filter_settings["strongs_headwords"])
		cross_references.Check(filter_settings["footnote_ellipsis_level"])
	
	def toggle_headwords(self, event):
		config_manager["Filter"]["strongs_headwords"] = event.IsChecked()
		self.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
		
	def toggle_expand_cross_references(self, event):
		filter_settings = config_manager["Filter"]
	
		filter_settings["footnote_ellipsis_level"] = \
			event.IsChecked() *	filterutils.default_ellipsis_level

		self.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
		

	def on_option(self, event):
		obj = event.GetEventObject()
		menuitem = obj.MenuBar.FindItemById(event.Id)
		#if not menuitem: return
		option_menu = menuitem.GetMenu()
		if option_menu == self.options_menu:
			biblemgr.set_option(menuitem.Text, event.Checked()) 
			self.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
			
			return
			
		for item in self.options_menu.MenuItems: 
			if item.GetSubMenu() == option_menu:
				biblemgr.set_option(item.Text, menuitem.Text) 
				self.UpdateBibleUI(
					settings_changed=True,
					source=SETTINGS_CHANGED
				)
				
				break
		else:
			assert False, "BLAH"
			
	def on_window(self, event):
		obj = event.GetEventObject()
		menuitem = obj.MenuBar.FindItemById(event.Id)
		self.show_panel(menuitem.Label, event.Checked())
	
	def on_activate(self, event):
		# call our hiding event afterwards when focus has been updated
		# wx.CallAfter(self.on_after_activate)

		# I don't think we need to hide everything as they are no longer
		# absolutely top. If they become that again, they will float above
		# other windows, which is undesirable
		pass
	
	def on_after_activate(self):
		# if we don't have focus at all, hide all tooltips and don't let any
		# more appear yet.
		if not wx.Window.FindFocus():
			self.hide_tooltips()
			self.lost_focus = True
			
		else:
			self.lost_focus = False
	
	def hide_tooltips(self, exceptions=[]):
		# remove dead objects
		self.toplevels = [item for item in self.toplevels if item]
		for item in self.toplevels:
			if item not in exceptions:
				item.Stop()
	
	def add_toplevel(self, toplevel):
		toplevel.Bind(wx.EVT_ACTIVATE, self.on_activate)
		self.toplevels.append(toplevel)
	
	#def remove_toplevel(self, toplevel):
	#	if toplevel:
	#		toplevel.Unbind(wx.EVT_ACTIVATE)

	#	self.toplevels.remove(toplevel)
	
	def on_char(self, event):
		# just pass the event on for now
		self.bibletext.on_char(event)
		#actions = {
		#	ord("G"): self.bibletext.go_quickly,
		#	ord("S"): self.bibletext.search_quickly
		#}
		#
		#print self.FindFocus()
		#guiutil.dispatch_keypress(actions, event)
		
	def setup_frames(self):
		self.frames = [self.bibletext, self.commentarytext, self.dictionarytext,
			self.genbooktext, self.verse_compare]

		for frame in self.frames:
			name = self.get_pane_for_frame(frame).name 
			self.aui_callbacks[name] = frame.update_title

		self.set_bible_ref(settings["bibleref"], LOADING_SETTINGS)
		self.DictionaryListSelected()
		self.version_tree.recreate()

	def MainFrameClose(self, event):
		# unbind activation events so that we don't get these called when the
		# frame disappears for the last time
		self.Unbind(wx.EVT_ACTIVATE)
		for a in self.toplevels:
			if a:
				a.Unbind(wx.EVT_ACTIVATE)

		self.save_data()
		self.Destroy()

	def set_search_version(self, version):
		self.search_panel.set_version(version)

	#def BibleRefEnterChar(self, event):
	
	def BibleRefEnter(self, event=None):
		if self.bibleref.GetValue()[:6] == "search":
			self.searchkey = self.bibleref.GetValue()[7:]
			if self.searchkey:
				self.search_panel.search_and_show(self.searchkey)
			else:
				self.search_panel.show()
		else:
			try:
				self.set_bible_ref(self.bibleref.GetValue(),
					source=BIBLE_REF_ENTER)
			except pysw.VerseParsingError, e:
				wx.MessageBox(e.message, config.name)

	def ExitClick(self, event):
		self.Close()

	def AboutClick(self, event):
		wxversion = wx.VERSION_STRING
		wxversiondata = ", ".join(wx.PlatformInfo[1:])
		sysversion = sys.version.split()[0]
		name = config.name
		text = """Flexible Bible study software.
			Built Using the Sword Project from crosswire.org
			Python Version: %(sysversion)s
			wxPython Version: %(wxversion)s""".expandtabs(0) %locals()

		info = wx.AboutDialogInfo()
		info.Name = "BPBible"
		info.Version = "0.3"
		info.Description = text#, 350, wx.ClientDC(self))
		info.WebSite = ("bpbible.com", 
						"BPBible website")
		info.Developers = ["Ben Morgan", "SWORD library developers"]
		info.Artists = ["Icons used are from famfamfam\n"
			"http://www.famfamfam.com/lab/icons/silk\n"
			"and the Tango Desktop Project\n"
			"http://tango.freedesktop.org/Tango_Desktop_Project"]

		info.License = wordwrap("BPBible is licensed under the GPL v2. "
			"For more details, refer to the LICENSE.txt file in the "
			"application directory", 330, wx.ClientDC(self))


		# Then we call wx.AboutBox giving it that info object
		wx.AboutBox(info)

	def bible_version_changed(self, newversion):
		self.set_search_version(biblemgr.bible.version)
		self.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
	
	def commentary_version_changed(self, newversion):
		#TODO get rid of this?
		self.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
	
	def dictionary_version_changed(self, newversion):
		freeze_ui = guiutil.FreezeUI(self.dictionary_list)
		self.dictionary_list.set_book(biblemgr.dictionary)
		
	def DictionaryListSelected(self, event=None):
		self.UpdateDictionaryUI()

	def UpdateDictionaryUI(self, ref=""):
		if not ref:
			ref = self.dictionary_list.GetValue().upper()
		else:
			self.dictionary_list.SetValue(ref)

		self.dictionarytext.SetReference(ref)

	def UpdateBibleUI(self, source, settings_changed=False):
		self.bible_observers(
			BibleEvent(
				ref=self.currentverse,
				settings_changed=settings_changed,
				source=source
			)
		)
	
	def refresh_all_pages(self):
		self.all_observers()
	
	def set_title(self, event):
		self.SetTitle(config.title_str % dict(name=config.name, 
											 verse=event.ref))
	
	def set_bible_ref(self, ref, source, settings_changed=False):
		"""Sets the current Bible reference to the given reference.

		This will trigger a Bible reference update event.

		ref: The new reference (as a string).
		source: The source of the change in Bible reference.
			The possible sources are defined in events.py.
		settings_changed: This is true if the settings have been changed.
		"""
		self.currentverse = pysw.GetVerseStr(ref, self.currentverse,
			raiseError=True)
		
		
		self.UpdateBibleUI(source, settings_changed)

class MainFrameXRC(MainFrame):
	def __init__(self):
		pre = wx.PreFrame()
		self.PostCreate(pre)
		self.Bind(wx.EVT_WINDOW_CREATE, self.OnCreate)

	def OnCreate(self, event):
		self.Unbind(wx.EVT_WINDOW_CREATE)
		wx.CallAfter(self.setup)
		event.Skip()
		return True
