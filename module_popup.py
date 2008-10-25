import wx
from util.observerlist import ObserverList
from gui import virtuallist
from util.unicode import to_str
from backend.dictionary import Dictionary
from backend.genbook import GenBook
from swlib.pysw import SW


class PopupList(virtuallist.VirtualListBox):
	def __init__(self, parent, book, key):
		super(PopupList, self).__init__(parent)
		self.book = book
		self.modules = book.GetModules()
		self.set_data(list(x.Name() for x in self.modules))
		for idx, item in enumerate(self.modules):
			if item == book.mod:
				self.EnsureVisible(idx)
		
		self.key = key
	
	def on_mouse_wheel(self, event):
		self.ScrollLines(
			-float(event.WheelRotation)/event.WheelDelta * event.LinesPerAction
		)

	def is_bold(self, item):
		module = self.modules[item]
		key = to_str(self.key, module)
		k = SW.Key(key)
		module.setKey(k)
		is_bold = bool(module.getRawEntry())

		# dictionaries snap to nearest - only give if it is the same
		if is_bold and isinstance(self.book, (Dictionary, GenBook)):
			is_bold = module.getKeyText() == key

		return is_bold

class ModulePopup(wx.PopupTransientWindow):
	def __init__(self, parent, event, rect, book, key, style=wx.NO_BORDER):
		super(ModulePopup, self).__init__(parent, style)
	
		panel = wx.Panel(self)#, style=wx.RAISED_BORDER, pos=(0, 0))
		
		self.box = PopupList(panel, book, key)
		#wx.ListBox(
		#	panel, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.NO_BORDER,
		#	pos=(0, 0)
		#)

		self.box.Bind(wx.EVT_LEFT_DOWN, self.ProcessLeftDown)		
		self.box.Bind(wx.EVT_LEFT_UP, self.ProcessLeftDown)
		self.box.Bind(wx.EVT_MOTION, self.OnMotion)
		
		#self.box.Items = book.GetModuleList()
		#if book.version:
		#	self.box.SetStringSelection(book.version)
#I:\python\bpbible\gui\virtuallist.py:46: RuntimeWarning: tp_compare didn't retur
#n -1 or -2 for exception
		


		self.box.Size = self.box.GetBestSize() + (50, 200)

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
		chosen, flags = self.box.HitTest(evt.GetPosition())
		if chosen == -1:
			chosen = None
		
		self.on_dismiss(chosen)
	
	def OnMotion(self, evt):
		item, flags = self.box.HitTest(evt.GetPosition())
		if item >= 0:
			self.box.Select(item)
	
	def OnDismiss(self):
		self.on_dismiss(None)
