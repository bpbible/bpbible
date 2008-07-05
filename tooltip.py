import wx
from wx import html
from util import util
import config, guiconfig
from gui import htmlbase
from backend.bibleinterface import biblemgr
from swlib.pysw import SW, VerseParsingError, GetBestRange

from gui import guiutil
from gui.guiutil import bmp
import re
from util.configmgr import config_manager

from util import osutils
from util.debug import dprint, TOOLTIP, WARNING

tooltip_settings = config_manager.add_section("Tooltip")

tooltip_settings.add_item("plain_xrefs", False, item_type=bool)
tooltip_settings.add_item("border", 6, item_type=int)

class TooltipBaseMixin(object):
	def __init__(self, *args, **kwargs):
		self.text = None
		self.target = None
		self.new_target = None

		
		self.is_biblical = kwargs.pop("is_biblical", False)
		self.references = [""]
		
		super(TooltipBaseMixin, self).__init__(*args, **kwargs)

	def SetText(self, text):
		# remove trailing new lines
		text = re.sub("(<br[^>]*>\s*)*$", "", text)

		self.text = text

	def set_biblical_text(self, references, force=False):
		try:
			template = util.VerseTemplate(
				header = "<a href='nbible:$range'><b>$range</b></a><br>", 
				body = "<font color='blue'><sup><small>$versenumber"
				"</small></sup></font> $text ", 
				footer = "<hr>")
			#no footnotes
			if tooltip_settings["plain_xrefs"]:
				biblemgr.temporary_state(biblemgr.plainstate)
			#apply template
			biblemgr.bible.templatelist.push(template)

			data = "".join(biblemgr.bible.GetReferences(references) or [])

			if(data.endswith("<hr>")):
				data = data[:-4]
			
			self.SetText(data)

			if force:
				self.html.SetPage(self.text, body_colour=self.colour,
					text_colour=self.text_colour)
			

		finally:
			if tooltip_settings["plain_xrefs"]:
				biblemgr.restore_state()
			biblemgr.bible.templatelist.pop()
		
	
	def show_bible_refs(self, href, url, x, y):
		# don't show a tooltip if there is no bible
		if biblemgr.bible.mod is None:
			return

		self.is_biblical = True
		if url is None:
			url = SW.URL(href)

		ref = url.getHostName()
		if ref:
			self.references = [ref]
		else:
			values = url.getParameterValue("values")
			if not values:
				return

			self.references = [
				url.getParameterValue("val%s" % value)
				for value in range(int(values))
			]

		self.set_biblical_text(self.references)

		self.Start()
		
	def ShowTooltip(self, position=None):
		"""Show the tooltip near the cursor.
		
		The text and target will have already been set, so we can easily get
		at them. The sizing portion of this is quite fiddly and easily broken.
		I've tried to get it as simple as I can."""

		# set our target to what we were over at the time
		self.target = self.new_target

		# set the size
		self.html.SetSize((400, 50))
		
		# and the borders
		self.html.SetBorders(tooltip_settings["border"])

		# and the page
		self.html.SetPage(self.text, body_colour=self.colour,
				text_colour=self.text_colour)
		
		# now we can get at the real size :)
		i = self.html.GetInternalRepresentation()

		w, h = (i.GetWidth() + tooltip_settings["border"], 
				i.GetHeight() + tooltip_settings["border"])

		self.html.SetDimensions(0, 0, w, h)
		self.resize_tooltip()

		width, height = self.GetSize()

		# pop it up at mouse point
		x, y = position or self.get_popup_position()
		
		# find screen size and position
		screen_rect = guiutil.get_screen_rect((x, y))
		
		if x + width > screen_rect.Right:
			x = max(screen_rect.Right - width - 2, screen_rect.Left)

		if y + height > screen_rect.Bottom:
			# if we moved the x along, try to move the y so it is above
			if x == screen_rect.Right - width - 2:
				y = y - height - 2
			else:
				y = screen_rect.Bottom - height - 2

			y = max(y, screen_rect.Top)

		self.MoveXY(x, y)

		self.Show()
	
	def get_popup_position(self):
		x, y = wx.GetMousePosition()

		# Add one so that it's not right under the cursor
		return x + 1, y + 1	

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

	def __init__(self, parent, style, logical_parent, html_type):
		self.style = style
		if tooltip_parent != wx.PopupWindow:
			self.style |= (
				wx.FRAME_TOOL_WINDOW  | 
				wx.FRAME_NO_TASKBAR   | 
				wx.FRAME_FLOAT_ON_PARENT
			)
			super(Tooltip, self).__init__(parent, style=style, title="Tooltip")
		else:
			super(Tooltip, self).__init__(parent, style)
			
		
		self.interval = 500
		self.timer = None
		self.out_timer = None
		self.mouse_is_over = True
		
		self.parent = parent
		self.logical_parent = logical_parent
		self.html_type = html_type
		
		# create the container panels
		self.container_panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
		self.toolbarpanel = wx.Panel(self.container_panel, -1)
		self.htmlpanel = wx.Panel(self.container_panel)

		# create the html control
		self.html = html_type(self.htmlpanel, 
			logical_parent=logical_parent, style=html.HW_SCROLLBAR_NEVER)

		self.html.parent = self

		# create the toolbar
		self.toolbar = wx.ToolBar(self.toolbarpanel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)

		self.toolbar.SetToolBitmapSize((16, 16))

		force_mask = False
		
		if osutils.is_msw() and not osutils.is_win2000():
			force_mask = not guiutil.is_xp_styled()

		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Anchor", bmp("anchor.png", force_mask=force_mask),
			shortHelp="Don't hide this tooltip")
		
		self.gui_copy = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Copy All", bmp("page_copy.png", force_mask=force_mask),
			shortHelp="Copy tooltip text (with links)")
			

		self.toolbar.Bind(wx.EVT_TOOL, self.stay_on_top, id=self.gui_anchor.Id)
		self.toolbar.Bind(wx.EVT_TOOL, self.copy_all, id=self.gui_copy.Id)
		
		self.toolbar.Realize()

		# put it on its panel
		panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
		panel_sizer.Add(self.toolbar, 1, wx.GROW)
		self.toolbarpanel.SetSizer(panel_sizer)

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
		def bind_mouse_events(item):
			# callafter as under MSW, enter seems to come before leave in
			# places
			item.Bind(wx.EVT_ENTER_WINDOW, 
				lambda evt: wx.CallAfter(self.MouseIn))
			item.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
			
			for child in item.Children:
				bind_mouse_events(child)

		bind_mouse_events(self)

	def copy_all(self, event):
		text = self.html.ToText()
		guiutil.copy(text)

	def stay_on_top(self, evt):
		new = PermanentTooltip(guiconfig.mainfrm, self.html_type,
			is_biblical=self.is_biblical)

		if not hasattr(self.html, "reference"):
			dprint(WARNING, "Tooltip html didn't have reference", self.html)
			self.html.reference = ""
		
		# the context of the note
		new.html.reference = self.html.reference
		
		if self.is_biblical:
			new.set_refs(self.references)
		else:
			#new.html.bibleframe=self.html.bibleframe
			new.text = self.text

		new.ShowTooltip(self.Position)
		
		dprint(TOOLTIP, "Stop on permanent popup")
		self.Stop()
		
	def MouseIn(self, event=None):
		#TODO: make frame and this be able to veto tooltip goaway
		self.mouse_is_over = True

		# stop tooltip going away if there was just a mouseout
		self.wants_to_go_away = False

	def MouseOut(self, event):
		# unless we get unset before the next event loop, disappear next event
		# loop. This is needed as under wxGTK, we get an out on the tooltip,
		# then an in on the panel on the tooltip, which is a tad weird.

		# Note: this assumes that MouseOut events get sent before MouseIn
		self.wants_to_go_away = True
		
		def disappear():
			# we may have been killed since the timer started...
			if not self:
				return

			if self.wants_to_go_away and \
				self.logical_parent.current_target != self.target:
				dprint(TOOLTIP, 
					"Going away as mouse off and not vetoed by mousein")
				#self.parent.lastcell = ""
				self.Stop()
	
		self.mouse_is_over = False

		if self.timer:
			self.timer.Stop()

		if self.out_timer:
			self.out_timer.Stop()

		self.out_timer = wx.CallLater(self.interval, disappear)

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
	
	def resize_tooltip(self):
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
	
		self.SetClientSize((w, h))
		self.SetSize((w, h))
		
		self.Fit()

# use a wxFrame to display this as we want:
# a) an icon
# b) it to appear in the task bar and task list
pclass = wx.Frame
class PermanentTooltip(TooltipBaseMixin, pclass):
	"""A permanent tooltip with some HTML in it."""
	def __init__(self, parent, html_type, 
		style=wx.DEFAULT_FRAME_STYLE & ~(wx.MAXIMIZE_BOX), 
			is_biblical=False):

		super(PermanentTooltip, self).__init__(
			parent, 
			title="Sticky Tooltip", 
			style=style|wx.STAY_ON_TOP|wx.MINIMIZE_BOX , 
			is_biblical=is_biblical
		) 

		self.style = style
		self.stayontop = True

		self.container_panel = wx.Panel(self)

		# create button panel
		self.buttonpanel = wx.Panel(self.container_panel, -1)		
		
		self.toolbar = wx.ToolBar(self.buttonpanel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)
		
		if self.is_biblical:
			self.gui_reference = wx.TextCtrl(self.toolbar,
					style=wx.TE_PROCESS_ENTER, size=(140, -1))
			
			self.toolbar.AddControl(self.gui_reference)
			
			self.gui_reference.Bind(wx.EVT_TEXT_ENTER, 
				lambda x:self.set_ref(self.gui_reference.Value))

			guiconfig.mainfrm.bible_observers += self.bible_ref_changed
			self.Bind(wx.EVT_CLOSE, self.on_close)
			self.gui_go = self.toolbar.AddLabelTool(wx.ID_ANY,  
				"Go to verses",
				guiutil.bmp("accept.png"),
				shortHelp="Open this reference")

			self.toolbar.AddSeparator()
			self.toolbar.Bind(wx.EVT_TOOL, 
				lambda x:self.set_ref(self.gui_reference.Value), 
				id=self.gui_go.Id
			)

		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Stay on top",
			guiutil.bmp("pushpin.gif"),
			shortHelp="Stay on top", kind=wx.ITEM_CHECK)

		self.toolbar.Bind(wx.EVT_TOOL, self.toggle_topness, 
			id=self.gui_anchor.Id)

		self.toolbar.Bind(wx.EVT_UPDATE_UI, 
			lambda evt:evt.Check(self.stayontop), id=self.gui_anchor.Id)
			
		self.toolbar.Realize()

		# make buttonsizer
		self.buttonsizer = wx.BoxSizer(wx.HORIZONTAL)		
		self.buttonsizer.Add(self.toolbar, 1, wx.GROW)
		self.buttonpanel.SetSizerAndFit(self.buttonsizer)

		# make html
		self.html = html_type(self.container_panel, 
			style=html.HW_SCROLLBAR_AUTO)
		
		# make sizer for panel
		self.global_sizer = wx.BoxSizer(wx.VERTICAL)		
		self.global_sizer.Add(self.buttonpanel, flag=wx.GROW)
		self.global_sizer.Add(self.html, flag=wx.GROW, proportion=3)
		self.container_panel.SetSizer(self.global_sizer)
		
		# set colour
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		self.container_panel.SetBackgroundColour(self.colour)
		self.buttonpanel.SetBackgroundColour(self.colour)
				
		# set icon
		self.SetIcons(guiconfig.icons)
		
		# non gui stuff
		self.parent = parent
		self.stayontop = True

	def on_close(self, event):
		guiconfig.mainfrm.bible_observers -= self.bible_ref_changed
		self.Destroy()
		
	def set_refs(self, refs):
		references = []
		context = "%s" % self.references[-1]
		for ref in refs:
			new_ref = self.get_verified_multi_verses(
				"%s" % ref, context
			)
			if new_ref is None:
				return

			context = new_ref
			references.append(new_ref)

		self.references = references

		reference_strings = '|'.join(self.references)
		self.gui_reference.ChangeValue(reference_strings)
		self.Title = reference_strings.replace("|", "; ")
		
		self.set_biblical_text(self.references, force=True)
		
	def set_ref(self, reference):
		references = reference.split("|")
		return self.set_refs(references)
	
	def bible_ref_changed(self, event):
		if event.settings_changed:
			self.set_biblical_text(self.references, force=True)

	def get_verified_multi_verses(self, ref, context):
		try:
			ref = GetBestRange(ref, context, raiseError=True)
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(e.message, config.name)
		
	def toggle_topness(self, evt):
		styles = [wx.FRAME_FLOAT_ON_PARENT, wx.STAY_ON_TOP]
		self.stayontop = not(self.stayontop)
		self.SetWindowStyle(self.style|styles[self.stayontop])

	def Stop(self): pass

	def Start(self):
		self.ShowTooltip() 

	#def SetTransparent(*args):pass
	def resize_tooltip(self):
		# set the container panel to fit
		self.container_panel.Fit()

		# get the required size
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
		
		# and set our size
		self.ClientSize = w, h
