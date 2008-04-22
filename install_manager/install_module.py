import wx
from xrc.install_module_xrc import xrcModuleInstallDialog, xrcModuleInfoPanel
from moduleinfo import ModuleInfo

INSTALL_QUERY_SINGLE = "Are you sure you want to install the following book?"
INSTALL_QUERY_MANY = "Are you sure you want to install the following books?"

class LineSeparator(wx.Window):
	def __init__(self, parent):
		super(LineSeparator, self).__init__(parent)
		self.Bind(wx.EVT_PAINT, self.paint)
	
	def paint(self, event):
		dc = wx.PaintDC(self)
		dc.SetPen(wx.BLACK_DASHED_PEN)
		dc.DrawLine(0, 0, self.Size[0], 0)

class ModuleInfoPanel(xrcModuleInfoPanel):
	def __init__(self, parent, module, width=300):
		super(ModuleInfoPanel, self).__init__(parent)
		self.module = module
		self.info_button.SetBitmapLabel(
			wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(40,40))
		)
		self.SetBackgroundColour(
			wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
		)
		
		self.module_description.SetLabel(self.module.Description())
		self.module_name.SetLabel(self.module.Name())
		font = self.module_name.Font
		font.SetStyle(wx.FONTSTYLE_ITALIC)
		self.module_name.Font = font
		for item in self.module_name, self.module_description:
			item.Wrap(width)
		
		self.info_button.Bind(wx.EVT_BUTTON, self.on_info_button)
	
	def on_info_button(self, event):
		ModuleInfo(self, self.module).ShowModal()
	
class ModuleInstallDialog(xrcModuleInstallDialog):
	def __init__(self, parent, modules):	
		self.modules = modules
		super(ModuleInstallDialog, self).__init__(parent)
		if len(modules) == 1:
			self.static_text.SetLabel(INSTALL_QUERY_SINGLE)
		else:
			self.static_text.SetLabel(INSTALL_QUERY_MANY)

		self.fill_modules()
		self.SetSizerAndFit(self.Sizer)
	
	def fill_modules(self):
		self.modules_info.SetScrollRate(0, 15)
	
		self.modules_info.SetBackgroundColour(
			wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
		)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.AddSpacer((0, 6), 0, wx.GROW)
	
		for module in self.modules:
			module_info = ModuleInfoPanel(self.modules_info, module)

			sizer.Add(module_info, 0, wx.GROW)
			linesep = LineSeparator(self.modules_info)
			linesep.Size = (-1, 1)
			linesep.MinSize = (-1, 1)
			sizer.Add(linesep, 0, wx.GROW|wx.ALL, 6)
		
		self.modules_info.SetSizer(sizer)
		
		self.modules_info.MinSize = 300, 150#self.modules_info.Size[0] + 12, 150
			
	
if __name__ == '__main__':
	app = wx.App(0)
	from swlib.pysw import SW
	mgr = SW.Mgr()
	mods = "KJV ESV".split() * 5
	mods = [mgr.getModule(mod) for mod in mods]
	mods = mgr.getModules().values()
	ModuleInstallDialog(None, mods).ShowModal()

