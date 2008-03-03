import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin


class VirtualListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
	def __init__(self, parent, style):
		super(VirtualListCtrl, self).__init__(parent,
		style=style|wx.LC_REPORT|wx.LC_VIRTUAL|wx.LC_SINGLE_SEL)
		self.setup()
	
	def setup(self):

		# we have to call this as presumably list ctrl doesn't call super
		# properly
		ListCtrlAutoWidthMixin.__init__(self)
		
		#self.Size = self.Size[0] + 1, self.Size[1]
		self.cache = {}
		
	
	#def refresh(self, start, end=None):
	#	if end is None:
	#		self.RefreshItem(start)
	#	else:
	#		self.RefreshItems(start, end)
	
	def set_data(self, columns, data=None, length=None):
		self.ClearAll()
		self.cache = {}

		for id, column in enumerate(columns):
			self.InsertColumn(id, column)

		if data is None:
			assert length is not None
			self.SetItemCount(length)
		else:
			self.data = data
		
			self.SetItemCount(len(self.data))

		self._doResize()

	def OnGetItemText(self, item, column):
		key = (item, column) 
		if key in self.cache:
			return self.cache[key]
		
		data = self.get_data(item, column)
		self.cache[key] = data
		return data
	
	def get_data(self, item, column):
		return self.data[item][column]

class VirtualListBox(VirtualListCtrl):
	def __init__(self, parent):
		super(VirtualListBox, self).__init__(parent, style=wx.LC_NO_HEADER)
		
		width = 200
		self.ClientSize = (width, 200)
		#self.set_book(book)
		
		#self.Bind(wx.EVT_SIZE, self.on_size)
		#self.Size = self.Size[0] + 1, self.Size[1]
	
	def refresh(self, start, end=None):
		if end is None:
			self.RefreshItem(start)
		else:
			self.RefreshItems(start, end)
	
	def set_data(self, data):
		super(VirtualListBox, self).set_data("0", [(item,) for item in data])

	#def on_size(self, event):
	#	self.SetColumnWidth(0, self.ClientSize[0])
	
class VirtualListCtrlXRC(VirtualListCtrl):
	def __init__(self):
		pre = wx.PreListCtrl()
		self.PostCreate(pre)
		self.setup()

