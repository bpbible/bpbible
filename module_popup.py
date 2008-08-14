import wx
from util.observerlist import ObserverList

class ModulePopup(wx.PopupTransientWindow):
	def __init__(self, parent, event, rect, book, style=wx.NO_BORDER):
		super(ModulePopup, self).__init__(parent, style)
	
		panel = wx.Panel(self, style=wx.RAISED_BORDER, pos=(0, 0))
		
		self.box = wx.ListBox(
			panel, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.NO_BORDER,
			pos=(0, 0)
		)

		self.box.Bind(wx.EVT_LEFT_UP, self.ProcessLeftDown)
		self.box.Bind(wx.EVT_MOTION, self.OnMotion)
		
		self.box.Items = book.GetModuleList()
		if book.version:
			self.box.SetStringSelection(book.version)

		self.box.Size = self.box.GetBestSize()

		panel.ClientSize = self.box.Size
		size_combo = 0
		
		# Show the popup right below or above the button
		# depending on available screen space...
		btn = event.EventObject
		
		pos = btn.ClientToScreen(rect.BottomLeft) + (0, 1)
		self.SetSize(panel.GetSize())# - (0, size_combo)
		self.Position(pos, (0, 0))#win.Size[1]))
		self.on_dismiss = ObserverList()

	def ProcessLeftDown(self, evt):
		self.Dismiss()
		chosen = self.box.HitTest(evt.GetPosition())
		if chosen == -1:
			chosen = None
		
		self.on_dismiss(chosen)
	
	def OnMotion(self, evt):
		item = self.box.HitTest(evt.GetPosition())
		if item >= 0:
			self.box.Select(item)
	
	def OnDismiss(self):
		self.on_dismiss(None)
