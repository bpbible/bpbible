import wx
from displayframe import DisplayFrame
import protocol_handlers

class ModuleInfo(wx.Dialog):
	def __init__(self, parent, module):
		super(ModuleInfo, self).__init__(parent, title=_("Book Information"), 
			style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		panel = wx.Panel(self)

		# XXX: Make the sunken border style work?
		info_frame = DisplayFrame(panel)
		info_frame.mod = module
		info_sizer = wx.BoxSizer(wx.HORIZONTAL)
		info_sizer.Add(info_frame, 1, wx.GROW)
		panel.SetSizer(info_sizer)

		# it's not in our usual book hierarchy, we have to supply a module
		info_frame.OpenURI(protocol_handlers.ModuleInformationHandlerModule.register(module))
		
		# now put the OK button on
		b = wx.Button(self, id=wx.ID_OK)
		s = wx.StdDialogButtonSizer()
		s.AddButton(b)
		s.Realize()

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(panel, 1, wx.GROW|wx.ALL, 10)
		sizer.Add(s, 0, wx.GROW|wx.ALL, 6)
		self.SetSizerAndFit(sizer)
		# XXX: Make sizing work properly later.
		self.Size = (600, 500)

if __name__ == '__main__':
	from backend.bibleinterface import biblemgr
	app = wx.App(0)
	ModuleInfo(None, biblemgr.bible.mod).ShowModal()
