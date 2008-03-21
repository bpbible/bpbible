import re

import wx
from wx import aui
import guiconfig
from gui import guiutil
from util import util
from util.configmgr import config_manager

class DockArt(wx.aui.PyAuiDockArt):
	"""DockArt: tracks the sections which when right clicked, bring up a
	toolbar popup"""
	def __init__(self):
		self.aui_dock_art = wx.aui.AuiDefaultDockArt()
		super(DockArt, self).__init__()

	def DrawBackground(self, dc, window, orientation, rect):
		# note the empty space that has been taken by spurious background
		# this space will be able to be right-clicked in to bring up a list of
		# toolbars
		self.aui_dock_art.DrawBackground(dc, window, orientation, rect)
		#dc.SetBrush(wx.BLUE_BRUSH)
		#dc.DrawEllipseRect(rect)
		self.owner.rects.append(rect)
	
	def DrawBorder(self, dc, rect, pane):
		# note the empty space that has been taken by toolbars that aren't
		# floating
		# this space will be able to be right-clicked in to bring up a list of
		# toolbars	
		self.aui_dock_art.DrawBorder(dc, pane.window, rect, pane)
	
		if pane.IsToolbar() and not pane.IsFloating():
			self.owner.rects.append(rect)
	
	#def DrawCaption(self, dc, window, text, rect, pane):
	#	dc.Brush = wx.RED_BRUSH
	#	dc.Pen = wx.TRANSPARENT_PEN
	#	dc.GradientFillLinear(rect, "#0A246A", "#A6CAF0")

	#	dc.TextForeground = "WHITE"
	#	dc.DrawText(text, rect[0] + 5, rect[1])
	#
	#
	#	pass

class AuiLayer(object):
	"""The AUI part of the main form"""
	def setup(self):
		self.aui_mgr = aui.AuiManager(
			self,
			aui.AUI_MGR_ALLOW_FLOATING| 
			aui.AUI_MGR_ALLOW_ACTIVE_PANE|
			aui.AUI_MGR_NO_VENETIAN_BLINDS_FADE|
			guiconfig.aui_hint)


		self.aui_uses_provider = False
		
		try:
			dockart = DockArt()
			dockart.owner = self
			
			self.aui_mgr.Bind(aui.EVT_AUI_RENDER, self.on_aui_render)

			self.aui_mgr.SetArtProvider(dockart)
			self.aui_uses_provider = True
		except AttributeError:
			# no constructor defined previous to wx 2.8.4.0, so can't override
			pass
	
	def set_aui_items_up(self):
		self.ToolBar = None#self.main_toolbar
	
		items = [[self.version_tree, "Books",],
			[self.bibletext.get_window(), "Bible", ["CloseButton", False]],
			[self.commentarytext.get_window(), "Commentary",],
			[self.dictionarytext.get_window(), "Dictionary"],
			[self.genbooktext.get_window(), "Other Books"],
			[self.verse_compare.get_window(), "Version Comparison"],			
			[self.search_panel, "Search"],
			[self.history_pane, "History"],
		]

		self.panes = (self.bibletext, self.commentarytext, 
			self.dictionarytext, self.genbooktext, self.verse_compare
		)

		self.panes = [(frame, frame.title) for frame in self.panes]
			

		if config_manager["BPBible"]["layout"] is not None:
			layout = config_manager["BPBible"]["layout"]
			self.create_items(items)
			self.create_toolbars(self.toolbars)
			
			self.load_aui_perspective(layout["perspective"])
			maximized = layout["maximized"]
			if maximized:
				pane = self.aui_mgr.GetPane(maximized)
				assert pane.IsOk(), maximized
				self.aui_mgr.MaximizePane(pane)
			
		else:
			self.default_set_aui_items_up()


		self.aui_mgr.Update()
	
	def get_pane_for_frame(self, frame):
		for f, pane_name in self.panes:
			if f == frame:
				pane = self.aui_mgr.GetPane(pane_name)
				assert pane.IsOk()
				return pane
		
	
	def create_items(self, items):
		for item in items:
			defaults = "CaptionVisible MaximizeButton Movable Floatable " \
				"MinimizeButton"
			item[2:] = [[j] for j in defaults.split()] + item[2:]
			info = aui.AuiPaneInfo().BestSize((300, 300)) \
			.Name(item[1]).Caption(item[1]).MinimizeButton(True).Layer(0)
			for attr in item[2:]:
				getattr(info, attr[0])(*attr[1:])
			self.aui_mgr.AddPane(item[0], info)
	
	def create_toolbars(self, toolbars):
		for item in toolbars:
			defaults = "Top"
			item = item[:]
			item[2:] = [[j] for j in defaults.split()] + item[2:]
			info = aui.AuiPaneInfo()\
			.Name(item[1]).Caption(item[1]).Row(0).ToolbarPane().\
			LeftDockable(False).RightDockable(False)

			for attr in item[2:]:
				getattr(info, attr[0])(*attr[1:])
			
			self.aui_mgr.AddPane(item[0], info)	
	
	def bind_events(self):
		self.aui_mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.on_pane_close)
		self.aui_mgr.Bind(aui.EVT_AUI_PANE_RESTORE, self.on_pane_restore)
		self.aui_mgr.Bind(aui.EVT_AUI_PANE_MAXIMIZE, self.on_pane_maximize)
	
	def show_toolbar_popup(self, event):
		if self.aui_uses_provider:
			for item in self.rects:
				if item.Contains(event.Position):
					break
			else:
				return

		event.EventObject.PopupMenu(self.toolbar_menu,
		guiutil.get_mouse_pos(event.EventObject))
	
	def get_maximized_pane(self):
		for pane in self.aui_mgr.GetAllPanes():
			if pane.IsMaximized():
				return pane
	
	@guiutil.frozen
	def load_default_perspective(self, event):
		for item in self.aui_mgr.AllPanes:
			self.aui_mgr.DetachPane(item.window)
		
		self.default_set_aui_items_up()
		self.aui_mgr.Update()
		self.on_changed()

	def load_aui_perspective(self, perspective):
		#perspective = re.sub("caption=[^;]*;","", perspective)
		#print perspective
		self.aui_mgr.LoadPerspective(perspective)
		#d = dict()
		self.on_changed()
	
	def on_changed(self):
		for pane in self.aui_mgr.GetAllPanes():
			if pane.IsShown():
				if pane.name in self.aui_callbacks:
					self.aui_callbacks[pane.name](True)
		wx.CallAfter(self.update_all_aui_menu_items)
	

	def show_panel(self, panel, toggle=True):
		pane = self.aui_mgr.GetPane(panel)
		
		maximized = self.get_maximized_pane()
		
		if maximized and not pane.IsToolbar(): 
			self.aui_mgr.RestoreMaximizedPane()

		assert pane.IsOk(), panel
		#if not toggle and pane.IsMaximized():
		#	# restore the pane first
		#	self.aui_mgr.RestorePane(pane)
		pane.Show(toggle)
		self.aui_mgr.Update()
		if panel in self.aui_callbacks:
			self.aui_callbacks[panel](toggle)

		self.on_pane_changed(panel, toggle)

	def on_pane_changed(self, pane_name, toggle):
		wx.CallAfter(self.update_all_aui_menu_items)

		for item in self.windows_menu.MenuItems:
			if item.Label == pane_name:
				item.Check(toggle)
	
	def update_all_aui_menu_items(self):

		menus = self.windows_menu, self.toolbar_menu
		for menu in menus:
			for item in reversed(menu.MenuItems):
				if item.IsSeparator():
					break
	
				pane = self.aui_mgr.GetPane(item.Label)
				assert pane.IsOk(), item.Label
				item.Check(pane.IsShown())
	
	def on_pane_restore(self, event):
		wx.CallAfter(self.update_all_aui_menu_items)
	
	on_pane_maximize = on_pane_restore

	def on_pane_close(self, event):
		self.event = event
		self.on_pane_changed(event.pane.name, False)		
	
	def save_layout(self):
		maximized = self.get_maximized_pane()
		if maximized:
			maximized = maximized.name

		self.aui_mgr.RestoreMaximizedPane()
		data = dict(perspective=self.aui_mgr.SavePerspective(),
					maximized=maximized)
		return data

	def on_aui_render(self, event):
		self.rects = []
		event.Skip()
		
	
	def set_pane_title(self, panename, text):
		pane = self.aui_mgr.GetPane(panename)
		assert pane.IsOk()
		
		pane.Caption(text)
		if pane.IsFloating():
			parent = guiutil.toplevel_parent(pane.window)			
			assert parent, "Top level parent of window not found!!!"

			parent.Title = text
			

		self.aui_mgr.Update()
	
	def is_pane_shown(self, panename):
		pane = self.aui_mgr.GetPane(panename)
		assert pane.IsOk()
		return pane.IsShown()
	
	def default_set_aui_items_up(self):
		"""Code used to generate perspective"""
		scrollsize = self.search_panel.BestSize
		#scrollsize[0] += 63
		default_items = [[self.version_tree, "Books", ["Left"], 
				["MinSize", [138, 50]],# self.version_tree.GetSize()],
				["BestSize", [138, 50]],#self.version_tree.GetBestSize()]
				
				],
	
			[self.bibletext.get_window(), "Bible", ["Centre"], ["CloseButton", False]],
			[self.commentarytext.get_window(), "Commentary", ["Right"],["Layer",2]],
			[self.dictionarytext.get_window(), "Dictionary", ["Bottom"]],
			[self.genbooktext.get_window(), "Other Books", ["Top"], 
				["Hide"]
			],
			[self.search_panel, "Search", 
				["Left"], ["Layer", 1],
				["MinSize", scrollsize],
				["BestSize", self.search_panel.GetBestSize()],
				["Hide"],
				["Float"],
				["Dockable", False],
			],
			[self.verse_compare.get_window(), "Version Comparison", ["Left"],			
				["Hide"]
			],
			[self.history_pane, "History", ["Left"],
				["Hide"]
			],
			
		]
		
		default_toolbars = self.toolbars
							#([self.main_toolbar, "Navigation"],
							#[self.zoom_toolbar, "Zoom"])
			
	
		self.create_items(default_items)
		self.create_toolbars(default_toolbars)		
