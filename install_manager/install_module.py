import wx
from xrc.install_module_xrc import xrcModuleInstallDialog, xrcModuleInfoPanel
from moduleinfo import ModuleInfo

INSTALL_QUERY_SINGLE = "Are you sure you want to install the following book?"
INSTALL_QUERY_MANY = "Are you sure you want to\ninstall the following books?"
modules_lookup = {}

class InfoButton(wx.BitmapButton):
	def __init__(self, parent, module, *args, **kwargs):
		super(InfoButton, self).__init__(parent, *args, **kwargs)
		self.module = modules_lookup[module]
		self.Bind(wx.EVT_BUTTON, self.on_info_button)
		self.SetBitmapLabel(
			wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(32,32))
		)
		
	def on_info_button(self, event):
		ModuleInfo(self, self.module).ShowModal()
		
		
class LineSeparator(wx.Window):
	def __init__(self, parent, *args, **kwargs):
		super(LineSeparator, self).__init__(parent, *args, **kwargs)
		self.Bind(wx.EVT_PAINT, self.paint)
	
	def paint(self, event):
		dc = wx.PaintDC(self)
		pen = wx.Pen((0, 0, 0), 1, wx.USER_DASH)
		pen.SetDashes([2])
		dc.SetPen(pen)
		dc.DrawLine(0, 0, self.Size[0], 0)

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
		self.Size = 400, 300
	
	def fill_modules(self):
		html = ""
		for module in self.modules:
			# enable lookup by name
			name = module.Name()
			modules_lookup[name] = module
			
			# and now output html for it
			html += "<table width='100%'><tr><td>"
			html += "%s<br><i>%s</i>" % (module.Description(), module.Name())
			html += "</td><td width=6></td><td align=RIGHT>"
			html += '''
			<wxp module="install_manager.install_module" class="InfoButton">
				<param name="module" value="%s" />
				<param name="size" value="(48,48)" />				
			</wxp>''' % module.Name()
			html += '''</td></tr>
			</table><hr>'''
			'''<table>
			<tr>
				<td width="100%">
			<wxp module="install_manager.install_module" class="LineSeparator" width="100%"/>
				
				</td>
			</tr>
			</table>
			'''
			

		self.modules_info.SetBorders(6)
		self.modules_info.SetPage(html)
		
		# and clear up modules_lookup
		wx.CallAfter(modules_lookup.clear)
			
def main():	
	app = wx.App(0)
	from swlib.pysw import SW
	mgr = SW.Mgr("\Sword")
	#mods = "KJV ESV".split() * 5
	#mods = [mgr.getModule(mod) for mod in mods]
	mods = mgr.getModules().values()
	ModuleInstallDialog(None, mods).ShowModal()

if __name__ == '__main__':
	# we want to make sure we have are running in the module of
	# install_module, not __main__!
	import install_manager.install_module as this_module
	this_module.main()

