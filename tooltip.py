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
		self.is_biblical = kwargs.pop("is_biblical", False)
		self.references = [""]
		
		super(TooltipBaseMixin, self).__init__(*args, **kwargs)

	def SetText(self, text):
		# remove trailing new lines
		text = re.sub("(<br[^>]*>\s*)*$", "", text)

		self.text = text
		self.html.SetPage(self.text, body_colour=self.colour,
				text_colour=self.text_colour) #set data
		
		
	
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
		
		#self.show_tooltip(x, y)
	def ShowTooltip(self):
		# popup it up at mouse point
		self.x, self.y = wx.GetMousePosition()#guiutil.get_mouse_pos(self)
		def wh():
			i = self.html.GetInternalRepresentation()
			return (i.GetWidth() + tooltip_settings["border"], 
					i.GetHeight() + tooltip_settings["border"])
					#+self.GetCharHeight()
			

		self.html.SetSize((400, 50))
		
		self.html.SetBorders(tooltip_settings["border"])
		self.html.SetPage(self.text, body_colour=self.colour,
				text_colour=self.text_colour) #set data

		w, h = wh()
		#self.Position = self.x, self.y
		self.html.SetDimensions(0, 0, w, h)
		
		self.container_panel.SetDimensions(0, 0, w, h)
		
		
		#find screen width
		screen_width = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_X)
		screen_height = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)

		width, height = self.html.GetSize()

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
		#self.Raise()
		#self.container_panel.Raise()
		#for item in self.tooltips:
		#	if item.IsShown() and item != self:
		#		item.Lower()#ShowTooltip(False)
		
		

#TODO check how this works under (say) MAC
tooltip_parent = wx.MiniFrame
#if osutils.is_gtk():
#	tooltip_parent = wx.PopupWindow

class Tooltip(TooltipBaseMixin, tooltip_parent):
	"""A tooltip with some HTML in it."""
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
		
		self.timer = None

		self.parent = parent
		self.logical_parent = logical_parent
		
		self.htmlpanel = wx.Panel(self.container_panel)

		self.html = html_type(self.htmlpanel, 
			logical_parent=logical_parent, style=html.HW_SCROLLBAR_NEVER)

		self.html_type = html_type
		self.html.parent = self

		self.interval = 500
		self.Bind(wx.EVT_ENTER_WINDOW, self.MouseIn)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		
		self.tooltips.append(self)
		
#		bitmap = wx.BitmapFromImage(wx.Image("pushpin.gif"))
		
		#self.button = wx.Button(self.panel, -1, "Stay on top")
		#self.button.Bind(wx.EVT_BUTTON, self.StayOnTop)
		self.toolbar = wx.ToolBar(self.panel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)

		self.toolbar.SetToolBitmapSize((16, 16))

		self.toolbar.BackgroundColour = self.colour

		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Anchor", bmp("anchor.png", ),#force_mask=True),
			shortHelp="Don't hide this tooltip")
		
		self.gui_copy = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Copy All", bmp("page_copy.png"),# force_mask=True),
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


		self.veto = True
		
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
		for item in self.Children:
			item.Bind(wx.EVT_ENTER_WINDOW, self.MouseIn)
			item.Bind(wx.EVT_LEAVE_WINDOW, self.MouseOut)
		

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
	
	def MouseIn(self, evt=None):
		#TODO: make frame and this be able to veto tooltip goaway
		self.veto = True

		# stop tooltip going away if there was just a mouseout
		self.wants_to_go_away = False

	def MouseOut(self, evt=None):
		# unless we get unset before the next event loop, disappear next event
		# loop. This is needed as under wxGTK, we get an out on the tooltip,
		# then an in on the panel on the tooltip, which is a tad weird.

		# Note: this assumes that MouseOut events get sent before MouseIn
		self.wants_to_go_away = True
		
		def disappear():
			if self.wants_to_go_away:
				dprint(TOOLTIP, 
					"Going away as mouse off and not vetoed by mousein")
				self.parent.lastcell = ""
				self.Stop()
				self.parent.veto = False
	
		wx.CallAfter(disappear)

	def Start(self):
		self.timer = wx.CallLater(self.interval, self.ShowTooltip)
	
	def Stop(self):
		if self.timer:
			self.timer.Stop()
		#self.Freeze()
		#self.Show()
		self.Hide()
		#self.Thaw()


	def OnTimer(self, event):
		self.ShowTooltip()
		
	
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
		#self.colour=GetColours()[0]#"#FFFF00"
		self.colour, self.text_colour = guiconfig.get_tooltip_colours()
		self.container_panel.SetBackgroundColour(self.colour)
		
		
		
		# set icon
		#icon = wx.Icon("Bible.ico",  wx.BITMAP_TYPE_ICO)
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

		self.toolbar.Bind(wx.EVT_TOOL, self.ChangeStyle, id=self.gui_anchor.Id)
		self.toolbar.Bind(wx.EVT_UPDATE_UI, 
			lambda evt:evt.Check(self.stayontop), id=self.gui_anchor.Id)
		
		
			
		self.toolbar.Realize()

		# make buttonsizer
		self.buttonsizer = wx.BoxSizer(wx.HORIZONTAL)		
		self.buttonsizer.Add(self.toolbar, 1, wx.GROW)
		self.buttonpanel.SetSizerAndFit(self.buttonsizer)

		# make horizontal separator
		self.line = wx.StaticLine(self.container_panel, style=wx.LI_HORIZONTAL)				

		# make html
		self.html = html_type(self.container_panel, style=html.HW_SCROLLBAR_AUTO)
		
		# make sizer for panel
		self.global_sizer = wx.BoxSizer(wx.VERTICAL)		
		self.global_sizer.Add(self.buttonpanel, flag=wx.GROW)
		self.global_sizer.Add(self.line, flag=wx.GROW)
		self.global_sizer.Add(self.html, flag=wx.GROW, proportion=3)
		#self.SetSizer(self.global_sizer)
		self.container_panel.SetSizer(self.global_sizer)

		
		#self.global_sizer.SetSizeHints(self)
		#self.Fit()
		#self.SetTransparent(178)		
		
		
		# non gui stuff
		self.parent=parent
		#self.html.parent=self		
		self.x=self.y=0
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
		
	def ChangeStyle(self, evt):
		styles = [wx.FRAME_FLOAT_ON_PARENT, wx.STAY_ON_TOP]
		self.stayontop = not(self.stayontop)
		self.SetWindowStyle(self.style|styles[self.stayontop])

	def Stop(self): pass

	def Start(self):
		self.ShowTooltip() 

	#def SetTransparent(*args):pass
	def size(self):
		w, h = self.container_panel.Size
		h += self.toolbar.Size[1]
	
		self.ClientSize = w, h
		#self.Size = w, h
		#
		#
		#self.Fit()	
