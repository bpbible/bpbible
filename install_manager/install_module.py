import wx
from xrc.install_module_xrc import xrcModuleInstallDialog, xrcModuleInfoPanel
from moduleinfo import ModuleInfo

INSTALL_QUERY_SINGLE = "Are you sure you want to install the following book?"
INSTALL_QUERY_MANY = "Are you sure you want to install the following books?"

def chop_text(dc, text, max_size):
	# first check if the text fits with no problems
	x, y = dc.GetTextExtent(text)
	if x <= max_size:
		return text
		
	last_good_length = 0
	for i in range(len(text)):
		s = text[:i]
		s += "..."
		
		x, y = dc.GetTextExtent(s)
		if (x > max_size):
			break
		
		last_good_length = i

	ret = text[:last_good_length]
	ret += "..."
	return ret

class ModuleInstallDialog(xrcModuleInstallDialog):
	def __init__(self, parent, modules):	
		self.modules = modules
		super(ModuleInstallDialog, self).__init__(parent)
		if len(modules) == 1:
			self.static_text.SetLabel(INSTALL_QUERY_SINGLE)
		else:
			self.static_text.SetLabel(INSTALL_QUERY_MANY)

		modules_info = VListCtrl(self.modules_info, self.modules)
		self.modules_info.Sizer.Add(modules_info, 1, wx.GROW)
		
		self.SetSizerAndFit(self.Sizer)
		self.Size = 400, 300
	

class VListCtrl(wx.VListBox):
	def __init__(self, parent, items):
		super(VListCtrl, self).__init__(parent)
		self.base = self.GetTextExtent("ABCDEFHXfgkj")[1]
		
		self.focus_item = wx.Window(self, size=(0, 0))
		self.focus_item.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
		self.focus_item.Bind(wx.EVT_SET_FOCUS, self.on_focus)
		
		#self.button_panel = wx.Panel(self, style=wx.TRANSPARENT_WINDOW)
		self.info_button = wx.Button(self, label="Information")
		self.info_button.Bind(wx.EVT_BUTTON, self.on_info_button)
		
		
		#self.uninstall_button = wx.Button(self, label="Uninstall")
		
		self.buttons = self.uninstall_button, self.info_button
		self.Bind(wx.EVT_SIZE, self.on_size)

		#sizer = wx.BoxSizer(wx.HORIZONTAL)
		#sizer.Add((6, 6))
		#sizer.Add(self.info_button)
		#sizer.Add((6, 6), 1, wx.GROW)
		#sizer.Add(self.uninstall_button)
		#sizer.Add((6, 6))

		#self.button_panel.SetSizerAndFit(sizer)
		#self.button_panel.SetBackgroundColour(self.GetSelectionBackground())
		#self.button_panel.Refresh()
		

		self.modules = items
		
		self.SetItemCount(len(items))
		self.SetSelection(0)
		self.layout_buttons()
		
		
		self.Bind(wx.EVT_LISTBOX, self.on_selected)
	
	def on_size(self, event):
		self.layout_buttons()
		event.Skip()

	def layout_buttons(self):
		self.info_button.Position = 6, -1
		self.uninstall_button.Position = (
			self.ClientSize[0] - self.uninstall_button.Size[0] - 6, 
			-1
		)
		
	def on_info_button(self, event):
		if self.Selection == -1:
			return

		ModuleInfo(self, self.modules[self.Selection]).ShowModal()
	
	def on_focus(self, event):
		self.SetFocusIgnoringChildren()

	def on_key_down(self, event):
		event.EventItem = self
		event.Skip()
		#if event.KeyCode == wx.WXK_UP:
		#	new_selection = self.Selection - 1

		#elif event.KeyCode == wx.WXK_DOWN:
		#	new_selection = self.Selection + 1
		#else:
		#	event.Skip()
		#	return
		#
		#if 0 <= new_selection < len(self.items):
		#	self.Selection = new_selection
		#	self.RefreshAll()
		#	self.Update()
		
		
	def OnMeasureItem(self, item):
		if self.IsCurrent(item):
			return self.base * 2 + 6 + self.buttons[0].Size[1] + 12 + 6

		return self.base * 2 + 6 + 6 + 6
	
	def on_selected(self, event):
		print "Skipping"
		event.Skip()
		self.Freeze()
		for item in self.buttons:
			item.Hide()		
		self.RefreshAll()
		self.Thaw()

	def OnDrawItem(self, dc, rect, n):
		if not self.IsVisible(self.Selection):
			for item in self.buttons:
				item.Hide()		
		
		if self.IsCurrent(n):
			for item in self.buttons:
				item.Show()

			pos = self.base * 2 + 6 + 6 + 6

			if self.buttons[0].Position[-1] != rect.Y + pos:
				for button in self.buttons:
					button.Position = -1, rect.Y + pos
				
			colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
			

		else:
			colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)

		
		dc.SetTextForeground(colour)
		
		
		font = self.Font
		font.SetWeight(wx.FONTWEIGHT_BOLD)
		dc.Font = font

		name = self.modules[n].Name()
		version = self.modules[n].getConfigEntry("Version")

		w, h = dc.GetTextExtent(name)
		dc.DrawText(name, rect.X + 6, rect.Y + 6, )
		
		font.SetWeight(wx.FONTWEIGHT_NORMAL)
		dc.Font = font
		
		if version:
			dc.DrawText(version, rect.X + 6 + w + 12, rect.Y + 6)
		
		description = self.modules[n].Description()
		description = chop_text(dc, description, rect.Width - 12)
		dc.DrawText(description, 
			rect.X + 6, rect.Y + 6 + self.base + 6, )
		
		

	def OnDrawBackground(self, dc, rect, n):
		if self.IsCurrent(n):
			colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
			from auilayer import wxAuiStepColour as light_contrast
	
			dc.GradientFillLinear(rect, colour, light_contrast(colour, 120), 
				wx.SOUTH)
		else:
			dc.Brush = wx.Brush(
				wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
			)
			
			dc.Pen = wx.TRANSPARENT_PEN
			dc.DrawRectangle(*rect)


	
	def OnDrawSeparator(self, dc, rect, n):
		dc.Pen = wx.Pen((192, 192, 192))

		for item in range(rect.Width)[::2]:
			dc.DrawPoint(item, rect.Y + rect.Height - 1)
		#dc.DrawLine(
		#	0,
		#	rect.Y + rect.Height - 1, 
		#	rect.Width, 
		#	rect.Y + rect.Height - 1
		#)
		
		rect.Height -= 1
	
	def SetFocus(self):
		print "TTEST"
		


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

