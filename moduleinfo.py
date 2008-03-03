import wx
from wx import html
import re
from gui import htmlbase

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
		super(ModuleInfo, self).__init__(parent, title="Module Information", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
		self.module = module
		panel = wx.Panel(self)
		fields = (
		 ("Name", process(module.Name()), -1), 
		 ("Description", process(module.Description()), 75),
		 ("About", process(module.getConfigEntry("About")), 115), 
		 ("License", process(module.getConfigEntry("DistributionLicense")),75)
				  )

		
		gs = wx.FlexGridSizer(len(fields), 2, 5, 5)
		gs.AddGrowableCol(1, 1)
		for id, (item, value, height) in enumerate(fields):
			panel2 = wx.Panel(panel)
			label = wx.StaticText(panel2, label=item+":", style=wx.ALIGN_RIGHT)
			font = label.Font
			font.Weight = wx.FONTWEIGHT_BOLD
			label.Font = font
			s = wx.BoxSizer(wx.HORIZONTAL)
			s.Add(label, 1, wx.GROW|wx.ALL, border=2)
			panel2.SetSizerAndFit(s)
			
			


			panel1 = wx.Panel(panel, style=wx.SUNKEN_BORDER)
			field = htmlbase.HtmlBase(panel1)
			field.SetBorders(1)
			
			field.SetPage(value)
			if height == -1:
				w, height = field.GetTextExtent(value)
				height += 8
				#d = field.Size[1] - field.ClientSize[1]
			
			gs.AddGrowableRow(id, height)

			field.SetSize((250, height))
			s = wx.BoxSizer(wx.HORIZONTAL)
			s.Add(field, 1, wx.GROW|wx.ALL)
			panel1.SetSizerAndFit(s)
			
			gs.Add(panel2, 0, flag=wx.GROW)
			gs.Add(panel1, 1, flag=wx.GROW)

		panel.SetSizerAndFit(gs)
		sizer = wx.BoxSizer(wx.VERTICAL)
		b = wx.Button(self, id=wx.ID_OK)
		#panel2 = wx.Panel(self)
		s = wx.StdDialogButtonSizer()
		s.AddButton(b)
		s.Realize()

		sizer.Add(panel, 1, wx.GROW|wx.ALL, 10)
		sizer.Add(s, 0, wx.GROW|wx.ALL, 6)
		self.SetSizerAndFit(sizer)

if __name__ == '__main__':
	from backend.bibleinterface import biblemgr
	wx.App(0)
	ModuleInfo(None, biblemgr.bible.mod).ShowModal()
