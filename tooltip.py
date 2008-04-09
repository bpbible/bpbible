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
from util.debug import dprint, TOOLTIP

tooltip_settings = config_manager.add_section("Tooltip")

tooltip_settings.add_item("plain_xrefs", False, item_type=bool)
tooltip_settings.add_item("border", 6, item_type=int)

class TooltipBaseMixin(object):
	def __init__(self, *args, **kwargs):
		self.x = self.y = 0
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
		
		
	
	def set_pos(self, x, y):
		self.x, self.y = x, y
	
#	def SetTransparent(*args):pass
	def set_biblical_text(self, references):
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

			data = "".join(biblemgr.bible.GetReferences(references))


			if(data.endswith("<hr>")):
				data = data[:-4]
			
			self.SetText(data)

		finally:
			if tooltip_settings["plain_xrefs"]:
				biblemgr.restore_state()
			biblemgr.bible.templatelist.pop()
		
	
	def show_bible_refs(self, href, url, x, y):
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

			self.references = []

			for value in range(int(values)):
				self.references.append(
					url.getParameterValue("val"+str(value))
				)

		self.set_biblical_text(self.references)

		self.set_pos(x, y)
		self.Start()
		
	def ShowTooltip(self):
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

		#find screen width
		screen_width = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X)
		screen_height = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)

		width, height = self.html.GetSize()

		# pop it up at mouse point
		self.x, self.y = wx.GetMousePosition()
		
		# add one so that it's not right under the cursor
		self.x += 1
		self.y += 1
		if(self.x + width > screen_width):
			self.x = self.x - width - 2
			if(self.x < 0):
				self.x = 0

		if(self.y + height > screen_height):
			self.y = self.y - height - 2#- self.GetCharHeight()
			if(self.y < 0):
				self.y = 0

		self.MoveXY(self.x, self.y)
		self.size()

		self.Show()

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

	tooltips = []
	def __init__(self, parent, style, logical_parent, html_type):
		self.style = style
		if tooltip_parent != wx.PopupWindow:
			self.style |= (
				wx.FRAME_TOOL_WINDOW  | 
				wx.FRAME_NO_TASKBAR   | 
				wx.FRAME_FLOAT_ON_PARENT
				# | wx.STAY_ON_TOP
			)
			super(Tooltip, self).__init__(parent, style=style, title="Tooltip")
		else:
			super(Tooltip, self).__init__(parent, style)#=style)
			
		self.container_panel = wx.Panel(self, -1, style=wx.RAISED_BORDER)
		
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		self.panel = wx.Panel(self.container_panel, -1)
		self.panel.SetBackgroundColour(self.colour)
		self.SetBackgroundColour(self.colour)
		self.container_panel.SetBackgroundColour(self.colour)
		
		self.interval = 500
		self.timer = None
		self.out_timer = None
		
		self.parent = parent
		self.logical_parent = logical_parent
		
		self.htmlpanel = wx.Panel(self.container_panel)

		self.html = html_type(self.htmlpanel, 
			logical_parent=logical_parent, style=html.HW_SCROLLBAR_NEVER)

		self.html.parent = self
		self.html_type = html_type

		self.Bind(wx.EVT_ENTER_WINDOW, lambda evt:(
			wx.CallAfter(self.MouseIn)
		))
		self.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		
		self.tooltips.append(self)
		
#		bitmap = wx.BitmapFromImage(wx.Image("pushpin.gif"))
		
		#self.button = wx.Button(self.panel, -1, "Stay on top")
		#self.button.Bind(wx.EVT_BUTTON, self.StayOnTop)
		self.toolbar = wx.ToolBar(self.panel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)

		self.toolbar.SetToolBitmapSize((16, 16))

		self.toolbar.BackgroundColour = self.colour

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

		panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

		panel_sizer.Add(self.toolbar, 1, wx.GROW)
		self.panel.SetSizer(panel_sizer)

		
		


		#s = wx.Sizer(wx.HORIZONTAL)
		#s.Add(self.container_panel, 1, wx.GROW)
		#self.SetSizer
		self.htmloffset = (0, self.panel.GetSizeTuple()[1])


		self.mouse_is_over = True
		
		sizer = wx.BoxSizer(wx.VERTICAL)#HORIZONTAL)
		sizer.Add(self.panel, 0, wx.ALIGN_CENTRE|wx.GROW)
		sizer.Add(self.htmlpanel, 1, wx.GROW)
		
		self.container_panel.SetSizer(sizer)
		self.container_panel.Fit()
		
		
		self.sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.sizer.Add(self.container_panel, 1, wx.GROW)
		
		self.SetSizerAndFit(self.sizer)
		# p = self.parent
		# q = p
		# while(p):
		# 	q=p
		# 	p=p.Parent
		def bind_mouse_events(item):
			for child in item.Children:
				# callafter as under MSW, enter seems to come before leave in
				# places
				child.Bind(wx.EVT_ENTER_WINDOW, 
					lambda evt:wx.CallAfter(self.MouseIn))
				child.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
				bind_mouse_events(child)

		bind_mouse_events(self)


		

	def copy_all(self, event):
		text = self.html.ToText()
		guiutil.copy(text)

	def stay_on_top(self, evt):
		#return

		new = PermanentTooltip(guiconfig.mainfrm, self.html_type,
			is_biblical=self.is_biblical)
		
		if self.is_biblical:
			new.set_refs(self.references)
		else:
			#new.html.bibleframe=self.html.bibleframe
			new.x, new.y = self.x, self.y
			new.text = self.text

		new.ShowTooltip()
		
		dprint(TOOLTIP, "Stop on permanent popup")
		self.Stop()
		

		#SetWindowStyle(self.style | wx.STAY_ON_TOP)
		#self.parent.tooltip = Tooltip(self.parent, self.style)
		#self.parent.tooltip.html.bibleframe = self.html.bibleframe
	
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
	
	def size(self):
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
	
		self.SetClientSize((w, h))
		self.SetSize((w, h))
		
		self.Fit()
	
	

	#def show_tooltip(self, x, y):
	#	xx, yy = self.CalcScrolledPosition(x, y) 
	#	point= (xx,yy)#+self.GetCharHeight())
	#	point= self.ClientToScreen(point) #screen point
	#	self.tooltip.set_pos(point)
	#	self.tooltip.Start()



# use a wxFrame to display this as we want:
# a) an icon
# b) it to appear in the task bar and task list
pclass = wx.Frame
class PermanentTooltip(TooltipBaseMixin, pclass):
	"""A permanent tooltip with some HTML in it."""
	def __init__(self, parent, html_type, 
		style=wx.DEFAULT_FRAME_STYLE & ~(wx.MINIMIZE_BOX | wx.MAXIMIZE_BOX), 
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

		# set colour
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		self.container_panel.SetBackgroundColour(self.colour)
		
		# set icon
		self.SetIcons(guiconfig.icons)
		
		# create button panel
		self.buttonpanel = wx.Panel(self.container_panel, -1)		
		self.buttonpanel.SetBackgroundColour(self.colour)
		
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
			wx.BitmapFromImage(wx.Image(config.graphics_path + "pushpin.gif")),
			shortHelp="Stay on top", kind=wx.ITEM_CHECK)#Open this reference")

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
		#self.SetSizer(self.global_sizer)
		self.container_panel.SetSizer(self.global_sizer)
		
		
		# non gui stuff
		self.parent = parent
		#self.html.parent=self		
		self.x = self.y = 0
		self.stayontop = True
		self.htmloffset=(0,0)

	def on_close(self, event):
		guiconfig.mainfrm.bible_observers -= self.bible_ref_changed
		self.Destroy()
		
	def set_refs(self, refs):
		references = []
		context = str(self.references[-1])
		for ref in refs:
			new_ref = self.get_verified_multi_verses(str(ref), context)
			if new_ref is None:
				return

			context = new_ref
			references.append(new_ref)

		self.references = references

		reference_strings = '|'.join(self.references)
		self.gui_reference.ChangeValue(reference_strings)
		self.Title = reference_strings.replace("|", "; ")
		
		self.set_biblical_text(self.references)
		
	def set_ref(self, reference):
		references = reference.split("|")
		return self.set_refs(references)
		[self.get_verified_multi_verses(str(reference))]
		self.gui_reference.ChangeValue('|'.join(self.references))
		self.set_biblical_text(self.references)
	
	def bible_ref_changed(self, event):
		if event.settings_changed:
			self.set_biblical_text(self.references)

	def get_verified_multi_verses(self, ref, context):
		try:
			ref = str(GetBestRange(ref, context, raiseError=True))
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(str(e), config.name)	
		
	def toggle_topness(self, evt):
		styles = [wx.FRAME_FLOAT_ON_PARENT, wx.STAY_ON_TOP]
		self.stayontop = not(self.stayontop)
		self.SetWindowStyle(self.style|styles[self.stayontop])

	def Stop(self): pass

	def Start(self):
		self.ShowTooltip() 

	#def SetTransparent(*args):pass
	def size(self):
		# set the container panel to fit
		self.container_panel.Fit()

		# get the required size
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
		
		# and set our size
		self.ClientSize = w, h
