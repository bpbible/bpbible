import re

import wx
from wx import aui
import guiconfig
import config
from gui import guiutil
from util.configmgr import config_manager
from util.observerlist import ObserverList
from module_popup import ModulePopup

# the following three functions borrowed from wxAUI in dockart.cpp

# wxAuiBlendColour is used by wxAuiStepColour
def wxAuiBlendColour(fg, bg, alpha):
	result = bg + (alpha * (fg - bg))
	result = max(result, 0)
	result = min(result, 255)
	return result

# wxAuiStepColour() it a utility function that simply darkens
# or lightens a color, based on the specified percentage
# ialpha of 0 would be completely black, 100 completely white
# an ialpha of 100 returns the same colour
def wxAuiStepColour(c, ialpha):
	if ialpha == 100:
		return c
		
	r, g, b = c.Red(), c.Green(), c.Blue()
	
	# ialpha is 0..200 where 0 is completely black
	# and 200 is completely white and 100 is the same
	# convert that to normal alpha 0.0 - 1.0
	ialpha = min(ialpha, 200);
	ialpha = max(ialpha, 0);
	alpha = (ialpha - 100.0)/100.0
	
	if (ialpha > 100):
		# blend with white
		bg = 255.0;
		alpha = 1.0 - alpha#  // 0 = transparent fg; 1 = opaque fg
	else:
		# blend with black
		bg = 0.0
		alpha = 1.0 + alpha#  // 0 = transparent fg; 1 = opaque fg
	
	r = wxAuiBlendColour(r, bg, alpha)
	g = wxAuiBlendColour(g, bg, alpha)
	b = wxAuiBlendColour(b, bg, alpha)
	
	return r, g, b

def wxAuiLightContrastColour(c):
	amount = 120

	# if the color is especially dark, then
	# make the contrast even lighter
	if c.Red() < 128 and c.Green() < 128 and c.Blue() < 128:
		amount = 160

	return wxAuiStepColour(c, amount)

class DockArt(wx.aui.PyAuiDockArt):
	"""DockArt: tracks the sections which when right clicked, bring up a
	toolbar popup"""
	text_padding = 2

	def __init__(self, parent):
		self.aui_dock_art = wx.aui.AuiDefaultDockArt()
		self.caption_drawn = ObserverList()
		super(DockArt, self).__init__()
		self.parent = parent

	def DrawBackground(self, dc, window, orientation, rect):
		# note the empty space that has been taken by spurious background
		# this space will be able to be right-clicked in to bring up a list of
		# toolbars
		self.aui_dock_art.DrawBackground(dc, window, orientation, rect)
		#dc.SetBrush(wx.BLUE_BRUSH)
		#dc.DrawEllipseRect(rect)
		self.parent.rects.append(rect)
	
	def DrawBorder(self, dc, rect, pane):
		# note the empty space that has been taken by toolbars that aren't
		# floating
		# this space will be able to be right-clicked in to bring up a list of
		# toolbars	
		self.aui_dock_art.DrawBorder(dc, pane.window, rect, pane)
	
		if pane.IsToolbar() and not pane.IsFloating():
			self.parent.rects.append(rect)
	
	def setup_font(self, dc, active):
		dc.TextForeground = self.GetColour([
			aui.AUI_DOCKART_INACTIVE_CAPTION_TEXT_COLOUR,
			aui.AUI_DOCKART_ACTIVE_CAPTION_TEXT_COLOUR
		][active])
		
		dc.Font = self.GetFont(aui.AUI_DOCKART_CAPTION_FONT)

	def DrawCaption(self, dc, window, text, rect, pane):
		from install_manager.install_module import chop_text
	
		active = bool(pane.state & pane.optionActive)

		match = None		
		if pane.name in [title for p, title in self.parent.panes]:
			self.regex = re.compile(r"\(([^)]+)\)")

			# get the last match
			for match in self.regex.finditer(text):
				pass

		if not match:
			# use the default behaviour
			return self.aui_dock_art.DrawCaption(dc, window, text, rect, pane)

		# draw the background...
		self.aui_dock_art.DrawCaption(dc, window, "", rect, pane)

		# setup our font
		self.setup_font(dc, active)
		
		combo_text = match.group(1)
		before_text = text[:match.start(1)]
		after_text = text[match.end(1):]
		
		max_width = rect[2] - 5

		button_size = self.GetMetric(aui.AUI_DOCKART_PANE_BUTTON_SIZE)
		max_width -= button_size * (
			pane.HasCloseButton() + pane.HasMaximizeButton()
		)
		
		
		chopped_text = chop_text(dc, before_text, max_size=max_width)
		w, h = dc.GetTextExtent(chopped_text)
		
		clipping_rect = wx.Rect(rect[0], rect[1], max_width, rect[3])
		dc.SetClippingRegion(*clipping_rect)
		dc.DrawText(chopped_text, rect[0] + 2,  rect.y+(rect.height/2)-(h/2))

		#if before_text != chopped_text:
		#	if pane.name in size_taken:
		#		del size_taken[pane.name]

		#	return
		
		c_w = w
		c_h = h

		w, h = dc.GetTextExtent(combo_text)
		height = h + 2
		
		backing_rect = wx.Rect(
			rect[0] + c_w + self.text_padding, rect.y+rect.height/2-height/2, 
			w+self.text_padding+height, height
		)

		self.draw_combo(dc, window, backing_rect, combo_text, 
			pane, clipping_rect)
		
		max_width -= backing_rect.width - 3

		chopped_text = chop_text(dc, after_text, max_size=max_width)
		w, h = dc.GetTextExtent(chopped_text)
		
		dc.DrawText(chopped_text, backing_rect.right + 2, 
			rect.y+(rect.height/2)-(h/2))
		
		

		w += rect[0] + 2
		h = rect[1]
		size_taken[pane.name] = backing_rect, combo_text, clipping_rect
		#self.caption_drawn(pane, max_width, *size_taken[pane.name])
		dc.DestroyClippingRegion()
		
	
	def draw_combo(self, dc, window, rect, text, pane, clipping_rect=None):
		assert pane.IsShown(), "Trying to draw hidden combo!"
		active = bool(pane.state & pane.optionActive)
		
		self.setup_font(dc, active)
		
		
		cc = self.GetColour([
			aui.AUI_DOCKART_INACTIVE_CAPTION_COLOUR,
			aui.AUI_DOCKART_ACTIVE_CAPTION_COLOUR,			
		][active])
		
		dc.SetBrush(wx.Brush(wxAuiStepColour(cc, 120)))
		dc.SetPen(wx.Pen(wxAuiStepColour(cc, 
			70 + (pane.name not in mouse_over) * 25))
		)
		
		w, h = dc.GetTextExtent(text)
	
		dc.DrawRectangleRect(rect)
		
		dc.DrawText(text, rect[0] + self.text_padding, 
			rect.y+(rect.height/2)-(h/2))
		
		
		h = rect.height
		drop_arrow_rect = (
			rect[0] + w + self.text_padding,
			rect.y+(rect.height/2)-(h/2), 15, 15
		)

		# clipping doesn't seem to be done here. So draw all or nothing
		if clipping_rect and clipping_rect.ContainsRect(drop_arrow_rect):
			wx.RendererNative.Get().DrawDropArrow(
				window, dc, drop_arrow_rect, 0
			)
	

mouse_over = {}
size_taken = {}
class AuiLayer(object):
	"""The AUI part of the main form"""
	def setup(self):
		self.aui_mgr = aui.AuiManager(
			self,
			aui.AUI_MGR_ALLOW_FLOATING| 
			aui.AUI_MGR_ALLOW_ACTIVE_PANE|
			aui.AUI_MGR_NO_VENETIAN_BLINDS_FADE|
			aui.AUI_MGR_TRANSPARENT_HINT)


		self.aui_uses_provider = False
		self.maximized_pane_direction = None
		
		self.on_render = ObserverList()
		
		try:
			self.dockart = DockArt(self)
			
			self.aui_mgr.Bind(aui.EVT_AUI_RENDER, self.on_aui_render)

			self.aui_mgr.SetArtProvider(self.dockart)
			self.aui_uses_provider = True
		except AttributeError:
			# no constructor defined previous to wx 2.8.4.0, so can't override
			pass


		# now set the inactive caption colour
		# wxAUI arguably should do this itself
		# on high contrast black, you couldn't see the inactive captions at
		# all
		prov = self.aui_mgr.GetArtProvider()

		# wxAUI darkens the gripper colour if it is too light. However, this
		# looks ugly next to a toolbar.
		prov.SetColour(wx.aui.AUI_DOCKART_GRIPPER_COLOUR,
			wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE))

		if not config.use_system_inactive_caption_colour:
			return
		
		prov.SetMetric(aui.AUI_DOCKART_GRADIENT_TYPE, 
					   aui.AUI_GRADIENT_HORIZONTAL)

		inactive_caption_colour = wx.SystemSettings.GetColour(
			wx.SYS_COLOUR_INACTIVECAPTION
		)
		
		inactive_caption_gradient_colour = wxAuiLightContrastColour(
			inactive_caption_colour
		)
		
		inactive_caption_text_colour = wx.SystemSettings.GetColour(
			wx.SYS_COLOUR_INACTIVECAPTIONTEXT
		)
		
		for setting, colour in (
			(aui.AUI_DOCKART_INACTIVE_CAPTION_COLOUR, inactive_caption_colour),
			(aui.AUI_DOCKART_INACTIVE_CAPTION_GRADIENT_COLOUR,
				inactive_caption_gradient_colour),
			(aui.AUI_DOCKART_INACTIVE_CAPTION_TEXT_COLOUR,
				inactive_caption_text_colour)
			):

			prov.SetColour(setting, colour)
	
	def set_aui_items_up(self):
		self.ToolBar = None#self.main_toolbar
	
		items = [
			[self.version_tree, "Books",],
			[self.bibletext.get_window(), "Bible", ["CloseButton", False]],
			[self.commentarytext.get_window(), "Commentary",],
			[self.dictionarytext.get_window(), "Dictionary"],
			[self.genbooktext.get_window(), "Other Books"],
			[self.verse_compare.get_window(), "Version Comparison"],			
			
			[self.history_pane, "History"],
		]
		items.extend([item, item.title] for item in self.searchers)


		panes = (
			self.bibletext, self.commentarytext, 
			self.dictionarytext, self.genbooktext, self.verse_compare
		)

		self.panes = [(frame, frame.title) for frame in panes]

		if config_manager["BPBible"]["layout"] is not None:
			layout = config_manager["BPBible"]["layout"]
			self.create_items(items)
			self.create_toolbars(self.toolbars)
			
			self.load_aui_perspective(layout["perspective"])
			maximized = layout["maximized"]
			if maximized:
				pane = self.aui_mgr.GetPane(maximized)
				assert pane.IsOk(), maximized
				self.fix_pane_direction(pane)
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

		self.aui_mgr.Bind(wx.EVT_MOTION, self.on_motion)
		self.aui_mgr.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
		self.aui_mgr.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave_window)
	
	def on_leave_window(self, event):
		self.clear_over_list()
		event.Skip()
	
	def on_left_down(self, event):
		if mouse_over:
			self.popup(event)
		else:
			event.Skip()
	
	def popup(self, event):
		assert(len(mouse_over)) == 1, "Only one thing can have mouse over"	
		name, (rect, title, clipping_rect) = mouse_over.items()[0]
		frames = [frame for frame, f_title in self.panes if f_title  == name]
		assert len(frames) == 1, "Wrong frame count: %s (%r)" % (name, frames)
		frame = frames[0]
		
		
		p = ModulePopup(self, event, rect, frame.book)
		def on_dismiss(chosen):
			if not rect.Contains(self.ScreenToClient(wx.GetMousePosition())):
				self.clear_over_list()
			
			if chosen is not None:
				frame.book.SetModule(p.box.GetString(chosen))

		p.on_dismiss += on_dismiss
		p.Popup()
	
	def clear_over_list(self):
		old_mouse_over = mouse_over.items()
		mouse_over.clear()		

		for key, (rect, title, clipping_rect) in old_mouse_over:
			self.repaint_combo(key, rect, title, clipping_rect)

	def repaint_combo(self, key, rect, title, clipping_rect):
		dc = wx.ClientDC(self)
		dc.SetClippingRegion(*clipping_rect)
		pane = self.aui_mgr.GetPane(key)
		if not pane.IsShown():
			return False

		self.dockart.draw_combo(dc, self, rect, title, pane, clipping_rect)
		dc.DestroyClippingRegion()
		return True

	def on_motion(self, event):
		self.clear_over_list()

		for key, (rect, title, clipping_rect) in size_taken.items():
			if rect.Contains((event.X, event.Y)):
				mouse_over[key] = rect, title, clipping_rect
				if self.repaint_combo(key, rect, title, clipping_rect):
					return


		event.Skip()

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
			self.restore_maximized_pane(maximized)
		assert pane.IsOk(), panel
		#if not toggle and pane.IsMaximized():
		#	# restore the pane first
		#	self.aui_mgr.RestorePane(pane)
		pane.Show(toggle)
		self.aui_mgr.Update()
		if panel in self.aui_callbacks:
			self.aui_callbacks[panel](toggle)

		self.on_pane_changed(panel, toggle)

	def restore_maximized_pane(self, pane):
		self.restore_pane_direction(pane)
		self.aui_mgr.RestoreMaximizedPane()

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
		pane = event.GetPane()
		self.restore_pane_direction(pane)
		wx.CallAfter(self.update_all_aui_menu_items)
	
	def fix_pane_direction(self, pane):
		self.maximized_pane_direction = pane.dock_direction
		pane.Right()
	
	def restore_pane_direction(self, pane):
		if self.maximized_pane_direction:
			 pane.dock_direction = self.maximized_pane_direction
			 self.maximized_pane_direction = None
	
	def on_pane_maximize(self, event):
		# workaround maximization bug - move the pane to the right before
		# maximizing, then back afterwards
		pane = event.GetPane()
		self.fix_pane_direction(pane)
		wx.CallAfter(self.update_all_aui_menu_items)
		 

	def on_pane_close(self, event):
		self.event = event
		self.on_pane_changed(event.pane.name, False)		
	
	def save_layout(self):
		maximized = self.get_maximized_pane()
		maximized_name = None
		if maximized:
			maximized_name = maximized.name

			self.restore_maximized_pane(maximized)

		data = dict(perspective=self.aui_mgr.SavePerspective(),
					maximized=maximized_name)
		return data

	def on_aui_render(self, event):
		self.rects = []
		self.on_render()
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
		scrollsize2 = (630, 470)
		#scrollsize[0] += 63
		default_items = [[self.version_tree, "Books", ["Left"], 
				["MinSize", [138, 50]],# self.version_tree.GetSize()],
				["BestSize", [138, 50]],#self.version_tree.GetBestSize()]
				
				],
	
			[self.bibletext.get_window(), "Bible", 
				["Centre"], 
				["CloseButton", False],
				["Floatable", False],
			],
			[self.commentarytext.get_window(), "Commentary", ["Right"],["Layer",2]],
			[self.dictionarytext.get_window(), "Dictionary", ["Bottom"]],
			[self.genbooktext.get_window(), "Other Books", ["Top"], 
				["Hide"]
			],
			
			[self.verse_compare.get_window(), "Version Comparison", ["Left"],			
				["Hide"]
			],
			[self.history_pane, "History", ["Left"],
				["Hide"]
			],
			
		]
		for item in self.searchers:
			default_items.append([item, item.title, 
				["Left"], ["Layer", 1],
				["MinSize", scrollsize],
				["BestSize", scrollsize2],
				["FloatingSize", scrollsize2],
				
				
				["Hide"],
				["Float"],
				["Dockable", False],
			])
		
		default_toolbars = self.toolbars
							#([self.main_toolbar, "Navigation"],
							#[self.zoom_toolbar, "Zoom"])
			
	
		self.create_items(default_items)
		self.create_toolbars(default_toolbars)		
	
