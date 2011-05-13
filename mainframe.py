import sys
import os


from util.debug import dprint, MESSAGE, ERROR, WARNING, is_debugging

import wx
from wx import xrc 

dprint(MESSAGE, "importing sword")
from swlib import pysw
from swlib.pysw import SW
dprint(MESSAGE, "/importing sword")

dprint(MESSAGE, "Other imports")

from backend.bibleinterface import biblemgr
from backend import filterutils


dprint(MESSAGE, "Importing frames")
from bibleframe import BibleFrame, bible_settings
from bookframe import BookFrame
from bookframe import CommentaryFrame
from bookframe import DictionaryFrame
from displayframe import IN_MENU, DisplayFrameManager
from genbookframe import GenBookFrame, HarmonyFrame

from auilayer import AuiLayer

from util.observerlist import ObserverList
from util import osutils
#import mySearchDialog
import versetree
import copyverses
import config
import guiconfig
from module_tree import ModuleTree
from pathmanager import PathManager
from module_manager import ModuleManagerDialog


dprint(MESSAGE, "Importing gui")
from gui import guiutil
from gui import fonts
from gui.guiutil import bmp
from gui.menu import Separator

from search.searchpanel import (BibleSearchPanel, GenbookSearchPanel,
								 HarmonySearchPanel, DailyDevotionalSearchPanel,
								 DictionarySearchPanel, CommentarySearchPanel)

from fontchoice import FontChoiceDialog 
from versecompare import VerseCompareFrame
from htmlide import HtmlIde
import events
from events import BibleEvent
from history import History, HistoryTree
from util.configmgr import config_manager
from install_manager.install_drop_target import ModuleDropTarget
import passage_list
from error_handling import ErrorDialog
from util.i18n import N_
import util.i18n
from preview_window import PreviewWindow
import display_options


settings = config_manager.add_section("BPBible")

settings.add_item("layout", {}, item_type="pickle")
settings.add_item("bibleref", "Genesis 1:1")
settings.add_item("bible", "ESV")
settings.add_item("dictionary", "ISBE")
settings.add_item("dictref", "")
settings.add_item("commentary", "TSK")
settings.add_item("genbook", "Josephus")
settings.add_item("harmony", "CompositeGospel")
settings.add_item("daily_devotional", "Daily")

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
		super(MainFrame, self).__init__(self, parent, -1, config.name(), 
		wx.DefaultPosition, size=(1024, 768))
		
		self.setup()

	def setup(self):
		self.on_close = ObserverList()
		

		dprint(MESSAGE, "Setting up")

		# Use the standard BPBible title to prevent the title from changing
		# from "Bible" to "<Reference> - BPBible".
		self.SetTitle(config.name())
	
		# use this dialog to catch all our errors
		self.error_dialog = ErrorDialog(self)
		self.error_dialog.install()
		self.on_close += self.error_dialog.uninstall
		
	
		guiconfig.mainfrm = self
		self.toplevels = []
		self.currentverse = ""
		self.zoomlevel = 0

		self.bible_observers = ObserverList()
		self.bible_observers += self.set_title

		biblemgr.bible.observers += self.bible_version_changed
		biblemgr.commentary.observers += self.commentary_version_changed

		biblemgr.on_after_reload += self.on_modules_reloaded
		self.on_close += lambda: \
			biblemgr.bible.observers.remove(self.bible_version_changed)
		
		self.on_close += lambda: \
			biblemgr.commentary.observers.remove(
				self.commentary_version_changed
			)
		
		self.on_close += lambda: \
			biblemgr.on_after_reload.remove(self.on_modules_reloaded)
		
		self.lost_focus = False
		self.history = History()
		self.bible_observers += self.add_history_item

		self.load_data()

		# issue 142 - devenagari text shows up too small in windows 7,
		# increase the base window font size.
		if osutils.is_win7() and pysw.locale_lang in ('ne', 'hi'):
			self.SetFont(wx.Font(11, wx.SWISS, wx.NORMAL, wx.NORMAL, False, fonts.default_fonts()[1][0]))

		self.make_toolbars()
		
		self.create_searchers()
		dprint(MESSAGE, "Setting AUI up")
		
		self.create_aui_items()
		self.buffer = wx.TextCtrl(self)
		self.buffer.Hide()
		
		super(MainFrame, self).setup()
		self.set_aui_items_up()
		
		dprint(MESSAGE, "Binding events")
		
		self.bind_events()
		dprint(MESSAGE, "Setting up frames")
		self.setup_frames()

		self.bibleref.SetFocus()
		
		for display_frame in (self.bibletext, self.commentarytext, self.dictionarytext, self.genbooktext, self.harmony_frame, self.daily_devotional_frame):
			display_options.display_option_changed_observers += display_frame.change_display_option
			fonts.fonts_changed += display_frame.fonts_changed

		fonts.fonts_changed += self.verse_compare.fonts_changed

		dprint(MESSAGE, "Setting menus up")
		self.set_menus_up()
		
		wx.CallAfter(dprint, MESSAGE, "Constructed")

		dprint(MESSAGE, "Done first round of setting up")
		self.drop_target = ModuleDropTarget(self)
		self.SetDropTarget(self.drop_target)
		wx.CallAfter(self.Show)
		if guiconfig.app.splash:
			wx.CallAfter(guiconfig.app.splash.Destroy)
		
		#guiutil.call_after_x(100, self.bibletext.scroll_to_current)
		
		# after three goes round the event loop, set timer for 200ms to scroll
		# to correct place
		# Under GTK, neglecting to do this will mean that it will scroll to
		# the top.
		guiutil.call_after_x(3, wx.CallLater, 200, 
			self.bibletext.scroll_to_current)
		



		
		
	def make_toolbars(self):
	
		dprint(MESSAGE, "Making toolbars")
		
		toolbar_style = wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT

	
	
		if not guiconfig.use_one_toolbar:# or True:
			toolbars = [
				wx.ToolBar(self, wx.ID_ANY, style=toolbar_style) 
				for i in range(3)
			]
		else:
			tb = self.CreateToolBar(wx.TB_TEXT|wx.TB_FLAT)
			toolbars = tb, tb, tb

		(self.main_toolbar, self.zoom_toolbar, 
			self.history_toolbar) = toolbars

		for toolbar in toolbars:
			toolbar.SetToolBitmapSize((16, 16))

		if not guiconfig.use_versetree:
			self.bibleref = wx.ComboBox(self.main_toolbar, 
					# TODO: add to this list
					choices=["Genesis 1:1"],
						style=wx.TE_PROCESS_ENTER)
		else:
			self.bibleref = versetree.VerseTree(self.main_toolbar)
			self.bible_observers += self.bibleref.set_current_verse
		
		self.bibleref.SetSize((140, -1))
		self.main_toolbar.AddControl(self.bibleref)
		
		self.tool_go = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Go to verse"), bmp("accept.png"),
			shortHelp=_("Go to this verse"))
			
		self.tool_search = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Search"), bmp("find.png"),
			shortHelp=_("Search in the current book"))
			
		self.tool_copy_verses = self.main_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Copy Verses"), bmp("page_copy.png"),
			shortHelp=_("Open the Copy Verses dialog"))

		if guiconfig.use_one_toolbar: self.ToolBar.AddSeparator()

		self.tool_back = self.history_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Back"), bmp("go-previous.png"),
			shortHelp=_("Go back a verse"))
		
		self.tool_forward = self.history_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Forward"), bmp("go-next.png"),
			shortHelp=_("Go forward a verse"))
			
		if guiconfig.use_one_toolbar: self.ToolBar.AddSeparator()
		self.tool_zoom_in = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Zoom In"), bmp("magnifier_zoom_in.png"),
			shortHelp=_("Make text bigger"))
			
		self.tool_zoom_default = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Default Zoom"), bmp("magnifier.png"),
			shortHelp=_("Return text to default size"))
			
		self.tool_zoom_out = self.zoom_toolbar.AddLabelTool(wx.ID_ANY,  
			_("Zoom Out"), bmp("magifier_zoom_out.png"),
			shortHelp=_("Make text smaller"))
			
		
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

		self.toolbars = ([self.main_toolbar, N_("Navigation"), 
							("BestSize", best_size)],
						 [self.zoom_toolbar, N_("Zoom"),
						 	["Hide"]],
						 [self.history_toolbar, N_("History toolbar"),
						 	["Row", 0]])
	
	def load_data(self):
		dprint(MESSAGE, "Loading data")
		
		if settings["options"]:
			for item, value in settings["options"].iteritems():
				biblemgr.set_option(item, value)
				
		if settings["size"]:
			self.SetSize(settings["size"])
		
		if settings["maximized"]:
			self.Maximize(True)
				
		filterutils.set_headwords_module_from_conf(biblemgr)

		def set_mod(book, mod_name):
			if book.ModuleExists(mod_name):
				book.SetModule(mod_name, notify=False)

		set_mod(biblemgr.bible, settings["bible"])
		set_mod(biblemgr.dictionary, settings["dictionary"])
		set_mod(biblemgr.commentary, settings["commentary"])
		set_mod(biblemgr.genbook, settings["genbook"])
		set_mod(biblemgr.harmony, settings["harmony"])
		set_mod(biblemgr.daily_devotional, settings["daily_devotional"])
		
		
	
	def capture_size(self, set_back=True):
		"""Capture the real size, not including maximization or minimization
		of the window.

		This will cause the screen to flash if minimized/maximized"""
		i = self.IsIconized()
		if i:
			self.Iconize(False)

		w = self.IsMaximized()
		if w:
			self.Maximize(False)

		size = self.Size
		if set_back:
			if w: 
				self.Maximize(w)

			if i: 
				self.Iconize(i)

		return w, size
	
	def save_data(self):
		settings["layout"][util.i18n.langid] = self.save_layout()
		settings["bibleref"] = self.currentverse
		settings["bible"] = biblemgr.bible.version
		settings["commentary"] = biblemgr.commentary.version
		settings["genbook"] = biblemgr.genbook.version
		settings["dictionary"] = biblemgr.dictionary.version
		settings["harmony"] = biblemgr.harmony.version
		settings["daily_devotional"] = biblemgr.daily_devotional.version

		settings["options"] = biblemgr.save_state()

		settings["maximized"], settings["size"] = \
			self.capture_size(set_back=False)

		#settings["position"] = self.Position
		
		

		try:
		#	if not os.path.exists(config.data_path):
		#		os.makedirs(config.data_path)

			config_manager.save()
		
		except (OSError, EnvironmentError), e:
			wx.MessageBox("OSError on saving settings\n%s" % str(e))

		except Exception, e:
			wx.MessageBox("Error on saving settings\n%s" % str(e))
		
		
			

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
		self.search_panel = BibleSearchPanel(self)
		self.genbook_search_panel = GenbookSearchPanel(self)
		#self.harmony_search_panel = HarmonySearchPanel(self)
		self.dictionary_search_panel = DictionarySearchPanel(self)
		self.daily_devotional_search_panel = DailyDevotionalSearchPanel(self)
		self.commentary_search_panel = CommentarySearchPanel(self)
		
		
		
		def make_closure(item):
			def version_changed(version=None):
				wx.CallAfter(item.set_version, item.book.version)

			def callback(toggle):
				wx.CallAfter(item.on_show, toggle)			
			
			def remove_observer():
				item.book.observers.remove(version_changed)
				
			return version_changed, callback, remove_observer

		self.searchers = (
			self.search_panel, 
			self.genbook_search_panel,
			self.dictionary_search_panel, 
			self.commentary_search_panel,
			#self.harmony_search_panel,
			self.daily_devotional_search_panel,
		)

		self.aui_callbacks = {}
		for item in self.searchers:
			version_changed, callback, remove_observer = make_closure(item)
			self.aui_callbacks[item.id] = callback

			item.book.observers += version_changed
			self.on_close += remove_observer
			version_changed()
			
		self.bible_observers += self.search_panel.versepreview.RefreshUI

	def create_aui_items(self):
		self.version_tree = ModuleTree(self)
		self.version_tree.on_module_choice += self.set_module_from_module_choice
		
		self.preview_window = PreviewWindow(self)
		

		self.genbooktext = GenBookFrame(self, biblemgr.genbook)
		self.harmony_frame = HarmonyFrame(self)

		self.bibletext = BibleFrame(self)
		self.bibletext.SetBook(biblemgr.bible)

		# set a watch on the bibletext to update the reference in text box
		# every time new page is loaded
		self.bibletext.observers += self.set_bible_ref

		self.commentarytext = CommentaryFrame(self, biblemgr.commentary)
		self.dictionarytext = DictionaryFrame(self, biblemgr.dictionary)
		self.daily_devotional_frame = DictionaryFrame(self,
				biblemgr.daily_devotional)
		self.daily_devotional_frame.id = "Daily Devotional"
		self.daily_devotional_frame.has_menu = False

		self.verse_compare = VerseCompareFrame(self, biblemgr.bible)
		#if settings["verse_comparison_modules"] is not None:
		#	self.verse_compare.modules = settings["verse_comparison_modules"]

		self.history_pane = wx.Panel(self)
		self.history_tree = HistoryTree(self.history_pane, self.history)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.history_tree, 1, wx.GROW)
		self.history_pane.SetSizer(sizer)

	def set_module_from_module_choice(self, mod):
		book = biblemgr.get_module_book_wrapper(mod.Name())
		self.set_module(book.mod, book)

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
		text = self.bibletext.get_quick_selected()
		
		cvd = copyverses.CopyVerseDialog(self)
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
		self.Bind(wx.EVT_MENU, self.on_manage_books,
			id=xrc.XRCID('manage_books'))
			
		
		self.Bind(wx.EVT_MENU, self.load_default_perspective, 
			id=xrc.XRCID('menu_default_layout'))
		
		self.Bind(wx.EVT_MENU, self.on_font_choice,
			id=xrc.XRCID('fontchoice'))
		
		self.Bind(wx.EVT_MENU, self.on_html_ide, 
			id=xrc.XRCID('gui_html_ide'))
		
		self.Bind(wx.EVT_MENU, self.on_widget_inspector, 
			id=xrc.XRCID('gui_widget_inspector'))
		
		self.Bind(wx.EVT_MENU, self.on_error_console, 
			id=xrc.XRCID('gui_error_console'))
		
		self.locales_menu_lookup = {}
		for item in "gather diff compile confirm".split():
			id = xrc.XRCID('gui_locale_%s' % item)
			self.Bind(wx.EVT_MENU, self.on_locale_menu, 
				id=id)

			self.locales_menu_lookup[id] = item

		self.Bind(wx.EVT_MENU, self.on_locale_restart, 
			id=xrc.XRCID('gui_locale_restart'))
		
		self.Bind(wx.EVT_MENU, self.on_reload, 
			id=xrc.XRCID('gui_reload'))

		self.Bind(wx.EVT_MENU, self.on_reload_chrome, 
			id=xrc.XRCID('gui_reload_chrome'))
		
		self.Bind(wx.EVT_MENU, id = wx.ID_EXIT, handler = self.ExitClick)
		self.Bind(wx.EVT_MENU, id = wx.ID_ABOUT, handler = self.AboutClick)
		
		web_links = dict(
			gui_website="http://bpbible.com",
			gui_documentation="http://code.google.com/p/bpbible/w/list?q=label:user-documentation&sort=pagename",
			gui_issues="http://code.google.com/p/bpbible/issues/list",
			gui_books="http://code.google.com/p/bpbible/wiki/InstallingBooks",
		)
		
		def weblink_handler(weblink):
			def handle_event(event):
				guiutil.open_web_browser(weblink)

			return handle_event
		
		for xrcid, website in web_links.items():
			self.Bind(wx.EVT_MENU, weblink_handler(website), 
				id=xrc.XRCID(xrcid))
			
			
		self.bibleref.Bind(wx.EVT_TEXT_ENTER, self.BibleRefEnter)

		# if it is selected in the drop down tree, go straight there
		# use callafter so that our text in the control isn't changed straight
		# back
		if guiconfig.use_versetree:
			self.bibleref.on_selected_in_tree += lambda text: \
			wx.CallAfter(self.set_bible_ref, text, 
				userInput=True, source=events.VERSE_TREE)
		else:
			self.bibleref.Bind(wx.EVT_COMBOBOX, self.BibleRefEnter)

		self.Bind(wx.EVT_TOOL, self.on_copy_button, 
			self.tool_copy_verses)
			
		
		self.Bind(wx.EVT_TOOL, self.BibleRefEnter, self.tool_go)
		
		self.Bind(wx.EVT_TOOL, self.do_search, self.tool_search)
		
		self.Bind(wx.EVT_TOOL, lambda x:DisplayFrameManager.zoom(1),
			self.tool_zoom_in)
			
		self.Bind(wx.EVT_TOOL, lambda x:DisplayFrameManager.zoom(-1),
			self.tool_zoom_out)
		
		self.Bind(wx.EVT_TOOL, lambda x:DisplayFrameManager.reset_zoom_level(),
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
		
	def on_locale_menu(self, event):
		from locales.doi18n import main
		text = self.locales_menu_lookup[event.Id]
		
		main([text])

	def on_locale_restart(self, event):
		import gettext

		# kill gettext's cache
		gettext._translations.clear()

		self.restart()

	def on_reload_chrome(self, event):
		print "Reloading all"
		guiconfig.app.reload_restarting = True
		guiconfig.app.restarting = True
		self.MainFrameClose(None)
		
	def on_reload(self, event):
		import reload_util
		reload(reload_util)
		reload_util.reboot_section("filtering")
		reload_util.reboot_section("copying")
		
	def add_history_item(self, event):
		if event.source != events.HISTORY:
			self.history.new_location(event.ref)

	def move_history(self, direction):
		history_item = self.history.go(direction)
		self.set_bible_ref(history_item.ref, ref_to_scroll_to=history_item.ref_to_scroll_to, source=events.HISTORY)
	
	def on_html_ide(self, event):
		ide = HtmlIde(self)
		ide.Show()
		
	def on_widget_inspector(self, event):
		wx.GetApp().ShowInspectionTool()

	def on_error_console(self, event):
		self.bibletext.Execute("window.open('chrome://global/content/console.xul', '', 'chrome,dialog=no,toolbar,resizable')")
	
	def on_path_manager(self, event):
		PathManager(self).ShowModal()
	
	def on_manage_books(self, event):
		ModuleManagerDialog(self).ShowModal()

	def on_install_module(self, event):
		fd = wx.FileDialog(self, 
			wildcard=_("Installable books") +  " (*.zip)|*.zip",
			style=wx.FD_DEFAULT_STYLE|wx.FD_MULTIPLE|wx.FD_MULTIPLE|wx.FD_OPEN,
			defaultDir=settings["last_book_directory"], 
			message=_("Choose books")
		)

		if fd.ShowModal() == wx.ID_OK:
			self.drop_target.handle_dropped_files(fd.Paths, self)
			settings["last_book_directory"] = fd.GetDirectory()

		fd.Destroy()
			
	
	def on_modules_reloaded(self, biblemgr):
		# as this will have refreshed the manager, refresh everything
		self.version_tree.recreate()
		self.fill_options_menu()

		self.refresh_all_pages()

	def on_font_choice(self, event):
		dialog = FontChoiceDialog(self)
		ansa = dialog.ShowModal()
		dialog.Destroy()
		if ansa == wx.ID_OK:
			fonts.fonts_changed()

	def get_menu(self, label):
		for idx, (menu, menu_name) in enumerate(self.MenuBar.Menus):
			if self.MenuBar.GetMenuLabel(idx) == label:
				break
		else:
			menu = None
		return menu
	
	
	def on_bookname_language_choice(self, event):
		print self.language_bookname_mapping[event.Id]
		util.i18n.locale_settings["language_book_names"][util.i18n.langid] = self.language_bookname_mapping[event.Id]
		self.restart()
	
	def on_language_choice(self, event):
		util.i18n.locale_settings["language"] = self.language_mapping[event.Id]
		self.restart()
	
	def fill_language_menu(self, menu, data, current, func, mapping):
		for text, display_name in sorted(data, key=lambda (t, d): d):			
			result = util.i18n.get_locale(text)
			if result:
				worked, own_locale, own_encoding = result
				own_key = display_name.encode(own_encoding)
				own_trans = own_locale.translate(own_key)
				own_trans = own_trans.decode(own_encoding)
			
			else:
				own_trans = None

			key = display_name.encode(pysw.locale_encoding)
			trans = pysw.locale.translate(key)
			trans = trans.decode(pysw.locale_encoding)

			if trans != own_trans and own_trans:
				trans += " - %s" % own_trans

			menu_item = menu.AppendRadioItem(wx.ID_ANY, trans)
			menu_item.Check(text == current)

			mapping[menu_item.Id] = text
			self.Bind(wx.EVT_MENU, func, menu_item)
	
	def set_menus_up(self):
		self.file_menu = self.MenuBar.GetMenu(0)
		for item in self.file_menu.MenuItems:
			if item.ItemLabel == _("&Language"):
				language_menu = item.SubMenu
				for iitem in language_menu.MenuItems:
					if iitem.ItemLabel == _("&Bible book names"):
						bible_book_name_menu = iitem.SubMenu
						break
				else:
					assert False, "Bible book name menu could not be found"

				break
		else:
			assert False, "Language menu could not be found"
		
		self.language_mapping = {}		

		self.fill_language_menu(language_menu, 
			[(text, display_name) for text, (display_name, x, y, z) 
				in util.i18n.languages.items()],
			util.i18n.locale_settings["language"],
			self.on_language_choice, self.language_mapping)
		self.language_bookname_mapping = {}
		self.fill_language_menu(bible_book_name_menu, 
			[(text, display_name) for text, (display_name, x, y) 
				in util.i18n.get_bookname_languages()],
			util.i18n.locale_settings["language_book_names"].get(
				util.i18n.locale_settings["language"],
				util.i18n.locale_settings["language"]
			),
			self.on_bookname_language_choice, self.language_bookname_mapping)
		



		
		#self.edit_menu
		self.options_menu = self.get_menu(_("&Display"))	
		assert self.options_menu, "Display menu could not be found"
		self.fill_options_menu()
		
		
		self.windows_menu = self.get_menu(_("&Windows"))
		assert self.windows_menu, "Window menu could not be found"
		
		mi = list(self.windows_menu.MenuItems)
		for idx, item in enumerate(mi):
			if item.Label == _("Toolbars"):
				self.toolbar_menu = item.SubMenu
				if guiconfig.use_one_toolbar:
					self.windows_menu.DeleteItem(item)
					#self.windows_menu.RemoveItem(mi[idx])				

				break
		else:
			assert False, "Toolbars menu could not be found"
		
		if not guiconfig.use_one_toolbar:
			self.windows_menu.AppendSeparator()
			
		for pane in self.aui_mgr.GetAllPanes():
			if pane.name in ("Bible",):
				continue

			for title, id in self.pane_titles.items():
				if id == pane.name:
					break
			
			else:
				dprint(WARNING, "Couldn't find pane title", pane.name)
				continue

			if pane.IsToolbar(): 
				item = self.toolbar_menu.AppendCheckItem(wx.ID_ANY,
					title,
					help=_("Show the %s toolbar")%title)
			else:
				item = self.windows_menu.AppendCheckItem(wx.ID_ANY,
					title,
					help=_("Show the %s pane")%title)

			if pane.IsShown():
				item.Check()

			self.Bind(wx.EVT_MENU, self.on_window, item)
		
		for idx, frame in enumerate(self.frames):
			if not frame.has_menu: continue
			items = [x for (x, where_shown) in frame.get_menu_items() 
				if where_shown & IN_MENU]
			
			menu = self.make_menu(items)

			self.MenuBar.Insert(2+idx, menu, "&" + frame.title)

		for idx, (menu, menu_name) in enumerate(self.MenuBar.Menus):
			if self.MenuBar.GetMenuLabel(idx) == _("Debug"):
				if is_debugging():
					for option in display_options.debug_options_menu:
						option.add_to_menu(self, menu)
				else:
					self.MenuBar.Remove(idx)
				break
	
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

		for option in display_options.options_menu:
			option.add_to_menu(self, self.options_menu)

		#if options:
		#	self.options_menu.AppendSeparator()

		cross_references = self.options_menu.AppendCheckItem(
			wx.ID_ANY,
			_("Expand cross-references"),
			_("Display cross references partially expanded")
		)
		
		display_tags = self.options_menu.AppendCheckItem(
			wx.ID_ANY,
			_("Topic Tags"),
			_("Display the topics that each verse is tagged with.")
		)

		"""
		expand_topic_passages = self.options_menu.AppendCheckItem(
			wx.ID_ANY,
			_("Expand Topic Passages"),
			_("Display the complete passage text for passages in the topic tooltip")
		)
		"""
		

		self.Bind(wx.EVT_MENU, self.toggle_expand_cross_references, 
			cross_references)
		self.Bind(wx.EVT_MENU, self.toggle_display_tags, display_tags)
		#self.Bind(wx.EVT_MENU, self.toggle_expand_topic_passages, expand_topic_passages)
		
		filter_settings = config_manager["Filter"]
		cross_references.Check(filter_settings["footnote_ellipsis_level"])
		display_tags.Check(passage_list.settings.display_tags)
		#expand_topic_passages.Check(passage_list.settings.expand_topic_passages)

	def toggle_expand_cross_references(self, event):
		filter_settings = config_manager["Filter"]
	
		filter_settings["footnote_ellipsis_level"] = \
			event.IsChecked() * filterutils.default_ellipsis_level

		self.UpdateBibleUI(settings_changed=True, source=events.EXPAND_CROSS_REFERENCES_TOGGLED)

	def toggle_display_tags(self, event):
		passage_list.settings.display_tags = event.IsChecked()
		self.UpdateBibleUI(settings_changed=True, source=events.DISPLAY_TAGS_TOGGLED)

	"""
	def toggle_expand_topic_passages(self, event):
		passage_list.settings.expand_topic_passages = event.IsChecked()
	"""

	def do_search(self, event):
		"""Search in the currently selected book, defaulting to the Bible if
		no book window is selected.
		"""
		selected_frame = self.get_selected_frame()
		if (selected_frame is None or
				(not isinstance(selected_frame, BookFrame)) or
				(not selected_frame.allow_search)):
			selected_frame = self.bibletext
		selected_frame.search()

	def on_window(self, event):
		obj = event.GetEventObject()
		menuitem = obj.MenuBar.FindItemById(event.Id)
		self.show_panel(self.pane_titles[menuitem.Label], event.Checked())
	
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
			self.daily_devotional_frame, self.harmony_frame, self.genbooktext,
			self.verse_compare]

		for frame in self.frames:
			name = self.get_pane_for_frame(frame).name 
			self.aui_callbacks[name] = frame.on_shown

		dprint(MESSAGE, "Setting initial bibleref")
		
		self.set_bible_ref(settings["bibleref"] or "Genesis 1:1", 
			events.LOADING_SETTINGS, userInput=False)
		self.dictionarytext.UpdateUI()
		self.daily_devotional_frame.UpdateUI()
		self.version_tree.recreate()

	def restart(self, event=None):
		guiconfig.app.restarting = True
		wx.MessageBox(
			_("BPBible will now quickly restart to change your language."), 
			_("Restarting")
		)
		self.MainFrameClose(None)
	
	def MainFrameClose(self, event=None):
		try:
			# unbind activation events so that we don't get these called when the
			# frame disappears for the last time
			self.Unbind(wx.EVT_ACTIVATE)
			for a in self.toplevels:
				if a:
					a.Unbind(wx.EVT_ACTIVATE)

			self.save_data()
			self.on_close()
		except Exception, e:
			# give notification - we probably have uninstalled our error
			# handler
			wx.MessageBox("%s\n%s" % 
				(_("An error occurred on closing:"), e)
			)

			# but let it propagate and print a stack trace
			raise
		finally:
			# but whatever happens, close
			self.Destroy()

	#def BibleRefEnterChar(self, event):
	
	def BibleRefEnter(self, event=None):
		if self.bibleref.Value.startswith(_("search ")):
			self.searchkey = self.bibleref.GetValue()[len(_("search ")):]
			if self.searchkey:
				self.search_panel.search_and_show(self.searchkey)
			else:
				self.search_panel.show()
		else:
			try:
				self.set_bible_ref(self.bibleref.GetValue(),
					source=events.BIBLE_REF_ENTER, userInput=True)
			except pysw.VerseParsingError, e:
				wx.MessageBox(str(e), config.name())

	def ExitClick(self, event):
		self.Close()

	def AboutClick(self, event):
		wxversion = wx.VERSION_STRING
		wxversiondata = ", ".join(wx.PlatformInfo[1:])
		sysversion = sys.version.split()[0]
		v = SW.cvar.SWVersion_currentVersion
		swversion = v.getText()
		xulrunner_version = config.xulrunner_version
		
		name = config.name()
		text = _("""Flexible Bible study software.
			Built Using the SWORD Project from crosswire.org
			Python Version: %(sysversion)s
			wxPython Version: %(wxversion)s
			SWORD Version: %(swversion)s
			XULRunner Version: %(xulrunner_version)s""").expandtabs(0) %locals()

		info = wx.AboutDialogInfo()
		info.Name = config.name()
		info.Version = config.version
		info.Description = text#, 350, wx.ClientDC(self))
		info.WebSite = ("bpbible.com", 
						_("BPBible website"))
		info.Developers = [
			_("BPBible development team"), 
			_("SWORD library developers"),
		]

		# mark these strings for translation
		N_("Developers")
		N_("Artists")
		N_("Translators")

		translator = _("translator-credits")
		if translator != "translator-credits":
			info.AddTranslator(translator)

		info.Artists = [_("Icons used are from famfamfam\n"
			"http://www.famfamfam.com/lab/icons/silk\n"
			"and the Tango Desktop Project\n"
			"http://tango.freedesktop.org/Tango_Desktop_Project")]

		from wx.lib.wordwrap import wordwrap
		info.License = wordwrap(_("BPBible is licensed under the GPL v2. "
			"For more details, refer to the LICENSE.txt file in the "
			"application directory"), 330, wx.ClientDC(self))


		# Then we call wx.AboutBox giving it that info object
		wx.AboutBox(info)

	def bible_version_changed(self, newversion):
		self.UpdateBibleUI(settings_changed=True, source=events.BIBLE_MODULE_CHANGED)
	
	def commentary_version_changed(self, newversion):
		self.commentarytext.refresh()

	def UpdateBibleUI(self, source, settings_changed=False, ref_to_scroll_to=None):
		if source != events.HISTORY:
			self.history.before_navigate()

		self.bibletext.HandleBibleEvent(
			BibleEvent(
				ref=self.currentverse,
				settings_changed=settings_changed,
				source=source,
				ref_to_scroll_to=ref_to_scroll_to,
			)
		)
	
	def refresh_all_pages(self):
		self.UpdateBibleUI(events.SETTINGS_CHANGED, settings_changed=True)
		self.dictionarytext.reload()
		self.genbooktext.reload()
		self.daily_devotional_frame.reload()
	
	def set_title(self, event):
		self.SetTitle(config.title_str % dict(name=config.name(), 
											 verse=pysw.internal_to_user(event.ref)))
	
	def set_bible_ref(self, ref, source, settings_changed=False, 
			userInput=False, ref_to_scroll_to=None):
		"""Sets the current Bible reference to the given reference.

		This will trigger a Bible reference update event.

		ref: The new reference (as a string).
		source: The source of the change in Bible reference.
			The possible sources are defined in events.py.
		settings_changed: This is true if the settings have been changed.
		userInput: was this user input (i.e. using user locale)?
		ref_to_scroll_to: An OSISRef to scroll the top of the screen to.
			Used by the history to make sure we return to the same position,
			rather than the selected verse which is often verse 1 and generally
			not what the user was at before they clicked on a hyperlink.
		"""
		self.currentverse = pysw.GetVerseStr(
			ref, self.currentverse, raiseError=True, 
			userInput=userInput
		)
		
		self.UpdateBibleUI(source, settings_changed, ref_to_scroll_to)

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
