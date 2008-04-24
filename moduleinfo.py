import wx
from wx import html
import re

import displayframe

def process(info):
	if not info: return ""
	# I haven't tested the unicode bits, so it's probably broken
	def uniconvert(object):
		return unichr(int(object.group(1)))
		
	info = re.sub(r"\\qc ?(.*?)(\pard|$)", r"<center>\1</center>\2", info)
	info = re.sub(r"\\pard", "", info)
	
	info = re.sub(r"\\par ?", "<br />", info)
	info = re.sub(r"\\u(\d+)\?", uniconvert, info)
	return info

class ModuleInfo(wx.Dialog):
	def __init__(self, parent, module):
		super(ModuleInfo, self).__init__(parent, title="Module Information", 
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		self.module = module
		panel = wx.Panel(self)
		fields = (
			("Name", process(module.Name()), -1), 
			("Description", process(module.Description()), 75),
			("About", process(module.getConfigEntry("About")), 115), 
			("License", 
				process(module.getConfigEntry("DistributionLicense")),75)
		)

		self.add_fields(fields, panel)
		
		# now put the OK button on
		b = wx.Button(self, id=wx.ID_OK)
		s = wx.StdDialogButtonSizer()
		s.AddButton(b)
		s.Realize()

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(panel, 1, wx.GROW|wx.ALL, 10)
		sizer.Add(s, 0, wx.GROW|wx.ALL, 6)
		self.SetSizerAndFit(sizer)
	
	def add_fields(self, fields, panel):
		gs = wx.FlexGridSizer(len(fields) + 1, 2, 5, 5)
		gs.AddGrowableCol(1, 1)
		for id, (item, value, height) in enumerate(fields):
			label = wx.StaticText(panel, label=item+":", style=wx.ALIGN_RIGHT)
			font = label.Font
			font.Weight = wx.FONTWEIGHT_BOLD
			label.Font = font

			field = displayframe.DisplayFrame(panel, style=wx.SUNKEN_BORDER)
			field.SetBorders(1)
			
			wx.CallAfter(field.SetPage, value)
			if height == -1:
				w, height = field.GetTextExtent(value)
				height += 8
			
			gs.AddGrowableRow(id, height)

			field.SetSize((250, height))

			gs.Add(label, 0, wx.GROW|wx.TOP, 3)
			gs.Add(field, 1, flag=wx.GROW)
		
		self.make_choice_field(panel, gs, fields)
		panel.SetSizerAndFit(gs)
			

	def make_choice_field(self, panel, gs, fields):
		self.variable_choice = wx.Choice(panel)
		
		config_map = self.module.getConfigMap()
		
		items = [
			(item.c_str(), value.c_str()) for item, value in config_map.items()
		]

		self.variable_items = [(item, value) for item, value in items 
			if item not in (y[0] for y in fields)]
		
		self.variable_choice.Items = [x for x, y in self.variable_items]
		self.variable_choice.Selection = 0
		self.variable_choice.Bind(wx.EVT_CHOICE, self.update_value)

		self.variable_field = displayframe.DisplayFrame(panel, 
			style=wx.SUNKEN_BORDER)
		self.variable_field.SetBorders(1)
		self.update_value()
		
		
		gs.AddGrowableRow(len(fields), 75)
		gs.Add(self.variable_choice, 0, wx.GROW|wx.TOP, 3)
		gs.Add(self.variable_field, 1, flag=wx.GROW)
		
		self.variable_field.SetSize((250, 75))
	
	def update_value(self, event=None):
		if self.variable_choice.Selection == -1:
			return

		value = self.variable_items[self.variable_choice.Selection][1]
		wx.CallAfter(self.variable_field.SetPage, value)

if __name__ == '__main__':
	from backend.bibleinterface import biblemgr
	app = wx.App(0)
	ModuleInfo(None, biblemgr.bible.mod).ShowModal()
