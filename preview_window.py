from displayframe import AUIDisplayFrame, DisplayFrame
from tooltip import TooltipBaseMixin
from backend.bibleinterface import biblemgr
from util.i18n import N_
from gui import guiutil
import guiconfig
import wx

class PreviewWindow(AUIDisplayFrame, TooltipBaseMixin):
	id = N_("Preview")
	
	def __init__(self, parent):
		self.panel = wx.Panel(parent)		
		super(PreviewWindow, self).__init__(self.panel)
		TooltipBaseMixin.__init__(self)
		
		# create button panel
		self.toolbarpanel = wx.Panel(self.panel, -1)		
		self.buttonsizer = wx.BoxSizer(wx.HORIZONTAL)		
		self.toolbarpanel.SetSizer(self.buttonsizer)
		self.recreate_toolbar()
		self.toolbarpanel.Fit()

		# make sizer
		self.global_sizer = wx.BoxSizer(wx.VERTICAL)		
		self.global_sizer.Add(self.toolbarpanel, flag=wx.GROW)
		self.global_sizer.Add(self, flag=wx.GROW, proportion=3)
		self.panel.SetSizer(self.global_sizer)
		
		
		
		self.html = self
		self.mod = None
		self.html.SetPage('<font color="#888888"><i>%s</i></font>' % _(
				"Move over a link to see a preview for it"))
		
		self.html_type=DisplayFrame

		# required to get fonts working
		self.book = biblemgr.bible

		self.colour, self.text_colour = guiconfig.get_window_colours()

	def get_window(self):
		return self.panel

	def create_toolbar(self):
		self.toolbar = wx.ToolBar(self.toolbarpanel,
			style=wx.TB_FLAT|wx.TB_NODIVIDER|wx.TB_HORZ_TEXT)
		
		if self.tooltip_config.add_to_toolbar(self.toolbar, permanent=True):
			self.toolbar.AddSeparator()

		self.tooltip_config.bind_to_toolbar(self.toolbar)

		self.gui_anchor = self.toolbar.AddLabelTool(wx.ID_ANY,  
			_("Show in tooltip"), guiutil.bmp("anchor.png"),
			shortHelp=_("Show this in a tooltip"))
		self.toolbar.Bind(wx.EVT_TOOL, self.stay_on_top, id=self.gui_anchor.Id)
			
		
		#self.toolbar.Bind(wx.EVT_TOOL, self.toggle_topness, 
		#	id=self.gui_anchor.Id)

		#self.toolbar.Bind(wx.EVT_UPDATE_UI, 
		#	lambda evt:evt.Check(self.stayontop), id=self.gui_anchor.Id)
			
		self.toolbar.Realize()


	def show_preview(self, frame, tooltip_config):
		"""
		When hovering over a link, show a tooltip iff:
		a) previewer is hidden
		b) shift is held down
		c) moving over link in previewer (or descendant)

		Otherwise, we handle it in our previewer
		"""
		if not self.aui_pane.IsShown():
			return False

		if frame == self:
			return False

		if wx.GetKeyState(wx.WXK_SHIFT):
			return False
		
		f = frame
		while f.logical_parent:
			f = f.logical_parent
			if f == self:
				return False

		self.tooltip_config = tooltip_config
		self.ShowTooltip()
		return True
	
	def ShowTooltip(self, position=None):
		self.html.SetPage(self.text)#, body_colour=self.colour,
#				text_colour=self.text_colour)
	
	def get_permanent_tooltip_position(self):
		return self.ScreenPosition

