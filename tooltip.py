import wx
import config, guiconfig
from backend.bibleinterface import biblemgr
from backend.verse_template import SmartVerseTemplate
import protocol_handlers
from swlib.pysw import VerseParsingError, GetBestRange

from gui import guiutil
from gui.guiutil import bmp
import re
from util.configmgr import config_manager

from util import osutils
from util.debug import dprint, TOOLTIP, WARNING

tooltip_settings = config_manager.add_section("Tooltip")

tooltip_settings.add_item("plain_xrefs", False, item_type=bool)

class TooltipBaseMixin(object):
	set_toolbar_background = False
	do_not_show_tooltip = False
	
	def __init__(self, *args, **kwargs):
		self.text = None
		self.target = None
		self.new_target = None
		self._tooltip_config = None
		self.toolbar_creator = None
		self.toolbar = None
		self.html = None

		tooltip_config = kwargs.pop("tooltip_config", TooltipConfig())
		
		super(TooltipBaseMixin, self).__init__(*args, **kwargs)

		self.set_tooltip_config(tooltip_config, update=False)
	
	def recreate_toolbar(self):
		if self.toolbar: 
			self.toolbar.Destroy()

		self.create_toolbar()
		self.toolbarpanel.Sizer.Add(self.toolbar, 1, wx.GROW)
		self.toolbarpanel.Layout()
		self.toolbar_creator = type(self.tooltip_config)

	def stay_on_top(self, evt):
		new = PermanentTooltip(guiconfig.mainfrm,
			tooltip_config=self.tooltip_config.another(),)

		if not hasattr(self.html, "reference"):
			dprint(WARNING, "Tooltip html didn't have reference", self.html)
			self.html.reference = ""
		
		# the context of the note
		new.html.reference = self.html.reference

		new.ShowTooltip(self.get_permanent_tooltip_position())
		
		dprint(TOOLTIP, "Stop on permanent popup")
		self.Stop()
		
	def get_permanent_tooltip_position(self):
		return self.Position

	def Stop(self):
		pass

	
	def show_strongs_ref(self, frame, href, url, element, x, y):
		type = url.getParameterValue("type") #Hebrew or greek
		value = url.getParameterValue("value") #strongs number
		if not type or not value: 
			print "Not type or value", href
			return

		module_for_search = frame.get_module_for_strongs_search(element)
		tooltip_config = StrongsTooltipConfig(type, value, module_for_search)
		frame.show_tooltip(tooltip_config)
	
	def show_bible_refs(self, frame, href, url, x, y):
		# don't show a tooltip if there is no bible
		if biblemgr.bible.mod is None:
			return

		ref = url.getHostName()
		if ref:
			# split up the references in case one OSIS reference encodes
			# multiple ones - issue 141
			references = re.split("[;,]", ref)
		else:
			values = url.getParameterValue("values")
			if not values:
				return

			references = [
				url.getParameterValue("val%s" % value)
				for value in range(int(values))
			]

		frame.show_tooltip(BibleTooltipConfig(references))

	def update_text(self, force=True):
		self._SetText(self.tooltip_config.get_text())

		if force:
			self.html.SetPage(self.text)
			self.maybe_scroll_to_current()

	def _SetText(self, text):
		# remove trailing new lines
		text = re.sub("(<br[^>]*>\s*)*$", "", text)

		self.text = text
		
	def ShowTooltip(self, position=None):
		"""Show the tooltip near the cursor.
		
		The text and target will have already been set, so we can easily get
		at them. The sizing portion of this is quite fiddly and easily broken.
		I've tried to get it as simple as I can."""

		if self.DoNotShowTooltip():
			return

		# set our target to what we were over at the time
		assert bool(position) ^ bool(self.new_target), "Target is None?!?"
		if self.new_target:
			self.target, target_rect, factor = self.new_target
		else:
			factor = 0
			target_rect = None
		self.Hide()

		# set the size
		self.html.SetSize((400, 50))
		
		# and the page
		path = protocol_handlers.TooltipConfigHandler.register(self.tooltip_config)
		self.html.OpenURI(path)
		
		self.html.size_intelligently(400, self._position_tooltip, position, target_rect, factor)
	
	def _position_tooltip(self, w, h, position, target_rect, factor):
		self.html.SetMinSize(self.html.Size)
		self.resize_tooltip()

		width, height = self.GetSize()

		if position:
			x, y = position
		else:			
			x, y = target_rect.BottomLeft
			

		y += factor
		
		# find screen size and position
		screen_rect = guiutil.get_screen_rect((x, y))
		#TODO: rows of refs
		
		if x + width > screen_rect.Right:
			x = max(screen_rect.Right - width - factor, screen_rect.Left)

		if y + height > screen_rect.Bottom:
			if position:
				y -= height
			else:
				y = target_rect.Top - factor - height
			# if we moved the x along, try to move the y so it is above
			#if x == screen_rect.Right - width - 2:
			#	y = target_rect.TopRighty - height - target_rect.Height - 10
			#else:
			#	y = screen_rect.Bottom - height - target_rect.Height

			y = max(y, screen_rect.Top)

		mouse_x, mouse_y = wx.GetMousePosition()
		if (x <= mouse_x <= x + width) and (y <= mouse_y <= y + height):
			x = mouse_x + 5
			if x + width > screen_rect.Right:
				x = max(mouse_x - width - factor, screen_rect.Left)

		if x + width > screen_rect.Right:
			x = max(screen_rect.Right - width - factor, screen_rect.Left)

		self.MoveXY(x, y)

		self.Show()

		wx.CallAfter(self.maybe_scroll_to_current)

	def DoNotShowTooltip(self):
		"""If a tooltip is shown when a top level window is active, then it
		will bring the main window up over the top of that top level window.
		For now, we work around this by just not showing the tooltip.
		"""
		if self.do_not_show_tooltip:
			return True

		from manage_topics_frame import ManageTopicsFrame
		from harmony.harmonyframe import HarmonyFrame
		from guess_verse import GuessVerseFrame
		window_types_to_ignore = (ManageTopicsFrame, HarmonyFrame, GuessVerseFrame)

		focused_window = wx.Window.FindFocus()
		if not focused_window:
			return False

		window = focused_window
		while window:
			if window.__class__ in window_types_to_ignore:
				# If the tooltip is a tooltip that is a child of this window,
				# then it should be shown, as it will not bring another window over
				# the top of that window.
				return not self.window_is_ancestor(window)
			window = window.Parent

		return False

	def window_is_ancestor(self, ancestor_window):
		window = self
		while window:
			if window is ancestor_window:
				return True
			window = window.Parent

		return False

	def resize_tooltip(self):
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
	
		self.SetClientSize((w, h))
		self.SetSize((w, h))
		
		self.Fit()

	def maybe_scroll_to_current(self):
		if self.tooltip_config.scroll_to_current:
			self.html.scroll_to_current()
	
	def get_popup_position(self):
		x, y = wx.GetMousePosition()

		# Add one so that it's not right under the cursor
		return x + 1, y + 1	

	def create_toolbar(self):
		# create the toolbar
		self.toolbar = wx.ToolBar(self.toolbarpanel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)

		self.toolbar.SetToolBitmapSize((16, 16))

		force_mask = False
		
		if osutils.is_msw() and not osutils.is_win2000():
			force_mask = not guiutil.is_xp_styled()

		self.tooltip_config.add_to_toolbar(self.toolbar, permanent=False)
		self.tooltip_config.bind_to_toolbar(self.toolbar)

		#	self.toolbar.AddSeparator()
		
		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			_("Anchor"), bmp("anchor.png", force_mask=force_mask),
			shortHelp=_("Don't hide this tooltip"))
		
		self.gui_copy = self.toolbar.AddLabelTool(wx.ID_ANY,  
			_("Copy All"), bmp("page_copy.png", force_mask=force_mask),
			shortHelp=_("Copy tooltip text (with links)"))
			

		self.toolbar.Bind(wx.EVT_TOOL, self.stay_on_top, id=self.gui_anchor.Id)
		self.toolbar.Bind(wx.EVT_TOOL, self.copy_all, id=self.gui_copy.Id)
		
		self.toolbar.Realize()
	
	def get_tooltip_config(self):
		return self._tooltip_config

	def set_tooltip_config(self, tooltip_config, update=False):
		old_config = self._tooltip_config
		if old_config:
			old_config.unbind_from_toolbar(self.toolbar)

		self._tooltip_config = tooltip_config
		self._tooltip_config.tooltip = self
		if self.toolbar_creator is not None:
			if type(self.tooltip_config) != self.toolbar_creator:
				self.recreate_toolbar()
				if self.set_toolbar_background:
					self.toolbar.SetBackgroundColour(self.colour)
					self.toolbarpanel.SetBackgroundColour(self.colour)
			else:
				self.tooltip_config.bind_to_toolbar(self.toolbar)
			

		# set for fonts
		if self.html: self.html.mod = tooltip_config.get_module()
		self.update_text(force=update)

	tooltip_config = property(get_tooltip_config, set_tooltip_config)

#TODO check how this works under (say) MAC
tooltip_parent = wx.MiniFrame
#if osutils.is_gtk():
#	tooltip_parent = wx.PopupWindow

class Tooltip(TooltipBaseMixin, tooltip_parent):
	"""A tooltip with some HTML in it.
	
	This is the specification for it:
	Will appear after 0.5 seconds of hovering over target area
	Will disappear after 0.5 seconds of moving off target area or self, 
	provided:
	a) it hasn't moved back over target area or self
	b) it's not over a child of this tooltip
	
	It will disappear instantaneously if:
	a) It is converted into a permanent tooltip
	b) A link on it is opened
	c) All tooltips are hidden (e.g. moving over a different window)"""

	set_toolbar_background = True

	def __init__(self, parent, style, logical_parent):
		self.style = style
		if tooltip_parent != wx.PopupWindow:
			self.style |= (
				wx.FRAME_TOOL_WINDOW  | 
				wx.FRAME_NO_TASKBAR   | 
				wx.FRAME_FLOAT_ON_PARENT
			)
			super(Tooltip, self).__init__(parent, style=self.style,
									title=_("Tooltip"))
		else:
			super(Tooltip, self).__init__(parent, self.style)
			
		
		self.interval = 400
		self.out_interval = 400
		self.timer = None
		self.out_timer = None
		self.mouse_is_over = True
		
		self.parent = parent
		self.logical_parent = logical_parent

		# create the container panels
		self.container_panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
		self.toolbarpanel = wx.Panel(self.container_panel)
		self.htmlpanel = wx.Panel(self.container_panel)

		# create the html control
		import displayframe
		self.html = displayframe.DisplayFrame(self.htmlpanel, logical_parent=logical_parent)
		self.html.book = biblemgr.bible
		self.html.parent = self

		# create button panel
		panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.toolbarpanel.SetSizer(panel_sizer)
		self.recreate_toolbar()

		# and set up the rest of the panels
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.toolbarpanel, 0, wx.ALIGN_CENTRE|wx.GROW)
		sizer.Add(self.htmlpanel, 1, wx.GROW)
		
		self.container_panel.SetSizer(sizer)
		self.container_panel.Fit()
		
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.container_panel, 1, wx.GROW)
		
		self.SetSizerAndFit(self.sizer)
		
		# get the colours for our tooltip
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		
		for item in self, self.toolbar, self.toolbarpanel, self.container_panel:
			item.SetBackgroundColour(self.colour)

		# and bind mouse enter and leave events to all children
		self.bind_mouse_events(self)
	
	def recreate_toolbar(self):
		super(Tooltip, self).recreate_toolbar()
		self.bind_mouse_events(self.toolbar)

	def bind_mouse_events(self, item):
		# callafter as under MSW, enter seems to come before leave in
		# places
		item.Bind(wx.EVT_ENTER_WINDOW, 
			lambda evt: wx.CallAfter(self.MouseIn))
		item.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		
		for child in item.Children:
			self.bind_mouse_events(child)

	


		

	def copy_all(self, event):
		self.html.copyall()

	def MouseIn(self, event=None):
		#TODO: make frame and this be able to veto tooltip goaway
		self.mouse_is_over = True

		# stop tooltip going away if there was just a mouseout
		self.wants_to_go_away = False
		
		# if we are about to pop up a new one, don't
		if self.timer:
			self.timer.Stop()

	def tooltip_children(self):
		x = self
		# yes, yes, we include ourselves...
		yield x
		while x.html.has_tooltip:
			x = x.html.tooltip
			yield x
	
	def tooltip_parents(self):
		item = self.logical_parent
		while item and item.logical_parent:
			item = item.logical_parent
			assert item.has_tooltip, "logical parent should have a tooltip "
			
			yield item.tooltip

	def MouseOut(self, event=None):
		# unless we get unset before the next event loop, disappear next event
		# loop. This is needed as under wxGTK, we get an out on the tooltip,
		# then an in on the panel on the tooltip, which is a tad weird.

		# Note: this assumes that MouseOut events get sent before MouseIn
		self.wants_to_go_away = True
		def disappear():
			# we may have been killed since the timer started...
			if not self:
				return
			
			for item in self.tooltip_children():
				if item.ScreenRect.Contains(wx.GetMousePosition()):
					return

			if self.wants_to_go_away and (
				not self.logical_parent.current_target
				or self.logical_parent.current_target[0] != self.target):
				dprint(TOOLTIP, 
					"Going away as mouse off and not vetoed by mousein")
				#self.parent.lastcell = ""

				dprint(TOOLTIP, "Stopping children")
				# hide all our children - this includes ourselves
				for item in self.tooltip_children():
					item.Stop()
				
				dprint(TOOLTIP, "Notifying parents")

				# and tell our parent tooltips that they need to reconsider
				# their need to live
				for item in self.tooltip_parents():
					if item.ScreenRect.Contains(wx.GetMousePosition()):
						break
					
					# don't send a MouseOut if it already is processing one
					if not item.out_timer.IsRunning():
						item.MouseOut(None)
	
		self.mouse_is_over = False

		if self.timer:
			self.timer.Stop()

		if self.out_timer:
			self.out_timer.Stop()

		self.out_timer = wx.CallLater(self.out_interval, disappear)

	def Start(self):
		# if we have an out timer, stop it
		if self.out_timer:
			self.out_timer.Stop()
		
		# if we have an in timer, stop it. It will be replaced by the new
		# timer
		if self.timer:
			self.timer.Stop()
		
		# set our new target
		self.new_target = self.logical_parent.current_target

		# and start our timer
		self.timer = wx.CallLater(self.interval, self.ShowTooltip)
	
	def Stop(self):
		self.target = None
		if self.timer:
			self.timer.Stop()

		if self.out_timer:
			self.out_timer.Stop()
			
		#self.Freeze()
		#self.Show()
		self.Hide()
		#self.Thaw()

	def HideTooltip(self):
		self.Stop()
	
# use a wxFrame to display this as we want:
# a) an icon
# b) it to appear in the task bar and task list
pclass = wx.Frame
class PermanentTooltip(TooltipBaseMixin, pclass):
	"""A permanent tooltip with some HTML in it."""
	def __init__(self, parent,
		style=wx.DEFAULT_FRAME_STYLE & ~(wx.MAXIMIZE_BOX), 
			tooltip_config=None):

		super(PermanentTooltip, self).__init__(
			parent, 
			title=_("Sticky Tooltip"), 
			style=style|wx.STAY_ON_TOP|wx.MINIMIZE_BOX,
		) 

		self.style = style
		self.stayontop = True

		self.container_panel = wx.Panel(self)
		self.toolbarpanel = wx.Panel(self.container_panel)		
		self.htmlpanel = wx.Panel(self.container_panel)

		# create the html control
		import displayframe
		self.html = displayframe.DisplayFrame(self.htmlpanel)
		self.html.book = biblemgr.bible
		self.html.parent = self
		html_sizer = wx.BoxSizer(wx.HORIZONTAL)
		html_sizer.Add(self.html, 1, wx.GROW)
		self.htmlpanel.SetSizer(html_sizer)

		# create button panel
		self.buttonsizer = wx.BoxSizer(wx.HORIZONTAL)		
		self.toolbarpanel.SetSizer(self.buttonsizer)		
		self.recreate_toolbar()

		# make sizer for panel
		sizer = wx.BoxSizer(wx.VERTICAL)		
		sizer.Add(self.toolbarpanel, 0, wx.ALIGN_CENTRE|wx.GROW)
		sizer.Add(self.htmlpanel, 1, wx.GROW)

		self.container_panel.SetSizer(sizer)
		self.container_panel.Fit()

		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.container_panel, 1, wx.GROW)
		
		self.SetSizerAndFit(self.sizer)
		
		# set colour
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		self.container_panel.SetBackgroundColour(self.colour)
		self.toolbarpanel.SetBackgroundColour(self.colour)
				
		# set icon
		self.SetIcons(guiconfig.icons)

		# Set the text
		self.tooltip_config = tooltip_config
		#self.update_text()
		
		self.Bind(wx.EVT_CLOSE, self.on_close)

		# non gui stuff
		self.parent = parent
		self.stayontop = True
	
	def create_toolbar(self):
		self.toolbar = wx.ToolBar(self.toolbarpanel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)
		
		if self.tooltip_config.add_to_toolbar(self.toolbar, permanent=True):
			self.toolbar.AddSeparator()
		
		self.tooltip_config.bind_to_toolbar(self.toolbar)			

		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			_("Stay on top"),
			guiutil.bmp("pushpin.gif"),
			shortHelp=_("Stay on top"), kind=wx.ITEM_CHECK)

		self.toolbar.Bind(wx.EVT_TOOL, self.toggle_topness, 
			id=self.gui_anchor.Id)

		self.toolbar.Bind(wx.EVT_UPDATE_UI, 
			lambda evt:evt.Check(self.stayontop), id=self.gui_anchor.Id)
			
		self.toolbar.Realize()

	def update_text(self, force=True):
		super(PermanentTooltip, self).update_text(force=force)
		self.Title = self.tooltip_config.get_title()

	def on_close(self, event):
		self.tooltip_config.unbind_from_toolbar(self.toolbar)
		self.Destroy()

	def toggle_topness(self, evt):
		styles = [wx.FRAME_FLOAT_ON_PARENT, wx.STAY_ON_TOP]
		self.stayontop = not(self.stayontop)
		self.SetWindowStyle(self.style|styles[self.stayontop])

	def Stop(self): pass

	def Start(self):
		self.ShowTooltip() 

	def HideTooltip(self):
		self.Close()

	#def SetTransparent(*args):pass

def BiblicalPermanentTooltip(parent, ref):
	"""Creates a Biblical permanent tooltip, open to the given ref."""
	tooltip_config = BibleTooltipConfig(ref.split("|"))
	return PermanentTooltip(parent, tooltip_config=tooltip_config)

class TooltipConfig(object):
	def __init__(self, mod=None, book=None):
		self.tooltip = None
		self.mod = mod
		self.book = book
		self.scroll_to_current = False

	def get_module(self):
		if self.book:
			return self.book.mod

		return self.mod

	def another(self):
		"""Possibly duplicate this config if it stores any state, otherwise
		just return it as is"""
		return self

	def tooltip_changed(self):
		if self.tooltip:
			self.tooltip.update_text()

	def hide_tooltip(self):
		if self.tooltip:
			self.tooltip.HideTooltip()

	def bind_to_toolbar(self, toolbar):
		"""Rebind toolbar events for this new config"""
		pass
	
	def unbind_from_toolbar(self, toolbar):
		"""Unbind events, etc. from the toolbar. Called when the current
		config is removed."""
	
	def add_to_toolbar(self, toolbar, permanent):
		"""Called to add things to the tooltip's toolbar 
		(if anything needs to be added).
		
		This should return True if any items were added to the toolbar.
		"""
		return False
	
	def get_title(self):
		"""Gets the title to be used on a sticky tooltip."""
		return _("Sticky Tooltip")

	def get_text(self):
		"""Returns the actual text to be used for the tooltip."""
		return ""

class TextTooltipConfig(TooltipConfig):
	def __init__(self, text, mod):
		super(TextTooltipConfig, self).__init__(mod)
		self.text = text

	def get_text(self):
		"""Returns the actual text to be used for the tooltip."""
		return self.text

class StrongsTooltipConfig(TooltipConfig):
	def __init__(self, type, value, module_for_search):
		self.type = type
		self.value = value
		self.module_for_search = module_for_search
		prefix = dict(Hebrew="H", Greek="G").get(type)
		
		module = "Strongs"+self.type #as module is StrongsHebrew
		mod = biblemgr.get_module(module)
		
		if prefix is not None:
			self.shortened = "%s%s" % (prefix, self.value)
		else:
			self.shortened = None	
	
		super(StrongsTooltipConfig, self).__init__(mod)
	
	def another(self):
		return StrongsTooltipConfig(self.type, self.value, self.module_for_search)

	def bind_to_toolbar(self, toolbar):
		toolbar.Bind(wx.EVT_TOOL,
			self.search,
			id=toolbar.gui_find.Id
		)

	def unbind_from_toolbar(self, toolbar):
		toolbar.Unbind(wx.EVT_TOOL)
		
	def add_to_toolbar(self, toolbar, permanent):
		#if not self.shortened: return False
		toolbar.gui_find = toolbar.AddLabelTool(wx.ID_ANY, 
			_("Find"),
			guiutil.bmp("find.png"),
			shortHelp=_("Search for this strong's number in the Bible"))

		self.bind_to_toolbar(toolbar)
		
		return True
	
	def search(self, event):
		if not self.shortened: return
		search_panel = guiconfig.mainfrm.bibletext.get_search_panel_for_frame()
		assert search_panel, "Search panel not found for %s" % guiconfig.mainfrm.bibletext
		self.hide_tooltip()
		search_panel.search_and_show("strongs:%s" % self.shortened, version=self.module_for_search)
	
	def get_text(self):
		if self.mod is None:
			tooltipdata = _("Module %s is not installed, "
			"so you cannot view "
			"details for this strong's number") %type
		
		else:
			#do lookup
			tooltipdata = biblemgr.dictionary.GetReferenceFromMod(
				self.mod, self.value)

		return tooltipdata

	
	
class BibleTooltipConfig(TooltipConfig):
	def __init__(self, references=None):
		super(BibleTooltipConfig, self).__init__(mod=None, book=biblemgr.bible)
		self.references = references
		self.toolbar = None
		self.is_bound = False
	
	def another(self):
		return BibleTooltipConfig(self.references)

	def bind_to_toolbar(self, toolbar):
		if not toolbar.permanent: return
		self.toolbar = toolbar
		import traceback
		assert not self.is_bound, self.is_bound
		self.set_refs(self.references, update=False)
		guiconfig.mainfrm.bible_observers += self.bible_ref_changed
		self.is_bound = ''.join(traceback.format_stack())
		
		toolbar.Bind(wx.EVT_TOOL, 
			lambda x:self.set_ref(toolbar.gui_reference.Value), 
			id=toolbar.gui_go.Id
		)
		
		toolbar.gui_reference.Bind(wx.EVT_TEXT_ENTER, 
			lambda x:self.set_ref(toolbar.gui_reference.Value))


		
		
	def unbind_from_toolbar(self, toolbar):
		if not toolbar.permanent: return

		assert self.is_bound
		guiconfig.mainfrm.bible_observers -= self.bible_ref_changed
		self.is_bound = False

		toolbar.Unbind(wx.EVT_TOOL, id=toolbar.gui_go.Id)
		toolbar.gui_reference.Unbind(wx.EVT_TEXT_ENTER)
		
	def add_to_toolbar(self, toolbar, permanent):
		toolbar.permanent = permanent
		if not permanent: return
		toolbar.gui_reference = wx.TextCtrl(toolbar,
				style=wx.TE_PROCESS_ENTER, size=(140, -1))

		toolbar.AddControl(toolbar.gui_reference)
		
		toolbar.gui_go = toolbar.AddLabelTool(wx.ID_ANY,  
			_("Go to verses"),
			guiutil.bmp("accept.png"),
			shortHelp=_("Open this reference")
		)

		return True

	def get_title(self):
		return "; ".join(GetBestRange(ref, userOutput=True) 
			for ref in self.references)

	def get_text(self):
		try:
			template = SmartVerseTemplate(
				header="<a href='nbible:$internal_range'><b>$range</b></a><br>",
				body=(config.body % ''),
			)

			#no footnotes
			if tooltip_settings["plain_xrefs"]:
				biblemgr.temporary_state(biblemgr.plainstate)
			#apply template
			biblemgr.bible.templatelist.append(template)

			import displayframe
			text = "<hr>".join(
				displayframe.process_html_for_module(biblemgr.bible.mod, item) 
				for item in biblemgr.bible.GetReferences(self.references)
			)

			return text

		finally:
			if tooltip_settings["plain_xrefs"]:
				biblemgr.restore_state()
			biblemgr.bible.templatelist.pop()
		
		
	def set_ref(self, reference):
		references = reference.split("|")
		return self.set_refs(references)
		
	def set_refs(self, refs, update=True):
		references = []
		try:
			context = "%s" % self.references[-1]
		except TypeError:
			context = ""
		for ref in refs:
			new_ref = self.get_verified_multi_verses(
				"%s" % ref, context
			)
			if new_ref is None:
				return

			context = new_ref
			references.append(new_ref)

		self.references = references

		reference_strings = '|'.join(
			GetBestRange(ref, userOutput=True) for ref in self.references
		)
		if self.toolbar.gui_reference:
			self.toolbar.gui_reference.ChangeValue(reference_strings)
		
		if update:
			self.tooltip_changed()

	def get_verified_multi_verses(self, ref, context):
		try:
			ref = GetBestRange(ref, context, raiseError=True, 
				userInput=True,	userOutput=False)
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(e.message, config.name())
	
	def bible_ref_changed(self, event):
		if event.settings_changed:
			self.tooltip_changed()

class TooltipDisplayer(object):
	def __init__(self, *args, **kwargs):
		super(TooltipDisplayer, self).__init__(*args, **kwargs)
		self.setup()
	
	def setup(self):
		self._tooltip = None	
		if not hasattr(self, "logical_parent"):
			self.logical_parent = None

		s = super(TooltipDisplayer, self)
		if hasattr(s, "setup"):
			s.setup()
	
	def show_tooltip(self, tooltip_config, mod=None):
		if guiconfig.mainfrm.preview_window.show_preview(
			self, tooltip_config
		):
			return

		self.tooltip.tooltip_config = tooltip_config
		self.tooltip.Start()

	@property
	def tooltip(self):
		if not self._tooltip:
			self._tooltip = Tooltip(guiutil.toplevel_parent(self), 
				style=wx.NO_BORDER, logical_parent=self)
			#self.Bind(wx.EVT_KILL_FOCUS, self.KillFocus)
			
			guiconfig.mainfrm.add_toplevel(self._tooltip)

		return self._tooltip
		
	@property
	def has_tooltip(self):
		return self._tooltip is not None
		



