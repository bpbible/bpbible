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
		self.cache.clear()

		for id, column in enumerate(columns):
			self.InsertColumn(id, column)

		if data is None:
			assert length is not None
			self.SetItemCount(length)
		else:
			self.data = data
			if length is not None:
				self.SetItemCount(length)
			else:
				self.SetItemCount(len(self.data))

		self._doResize()

	def OnGetItemText(self, item, column):
		# It seems that clicking on the dictionary list to dismiss the module 
		# popup will give error messages about ints being requireed when
		# looking things up in the cache. By looking up an attribute on self
		# that doesn't exist, we don't get these problems for some reason
		# Probably a wx problem, I'd guess.
		# To reproduce this problem easily, comment out the next two lines and
		# replace with import cPickle. Otherwise, you will need to scroll down 
		# to the 257th item (or even further down if you want) 
		has = hasattr(self, "broken")
		assert not has, "Don't set broken!"


		key = item, column
		if key in self.cache:
			return self.cache[key]
		
		# return text encoded as utf-8; wxPython 2.9.1.1 on Mac crashes if
		# non-ascii unicode text in there, but utf-8 works fine.
		data = self.get_data(item, column).encode("utf8")
		self.cache[key] = data
		return data
	
	def get_data(self, item, column):
		return self.data[item][column]
	
	#def GetSelection(self):
	#	return self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)

	#def SetSelection(self, item):
	#	selection = self.GetSelection()
	#	if selection != -1:
	#		self.SetItemState(
	#			0, 
	#			wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED 
	#		)
	#	self.SetItemState(item, 
	#		wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED,
	#		wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED 
	#	)
	#
	#Select = GetSelection
	

class VirtualListBox(VirtualListCtrl):
	def __init__(self, parent):
		super(VirtualListBox, self).__init__(parent, style=wx.LC_NO_HEADER)
		
		width = 200
		self.ClientSize = (width, 200)
		self.bold_cache = {}
		self.attr1 = wx.ListItemAttr()
		f = self.Font
		f.SetWeight(wx.FONTWEIGHT_BOLD)
		self.attr1.SetFont(f)
		self.Bind(wx.EVT_LIST_CACHE_HINT, self.on_cache_hint)
	
	def on_cache_hint(self, event):
		for item in range(event.CacheFrom, event.CacheTo+1):
			self.get_is_bold(item)
		
		
		
		#self.Bind(wx.EVT_SIZE, self.on_size)
		#self.Size = self.Size[0] + 1, self.Size[1]
	
	def refresh(self, start, end=None):
		if end is None:
			self.RefreshItem(start)
		else:
			self.RefreshItems(start, end)
	
	def get_data(self, item, column):
		return self.data[item]
	
	def set_data(self, data):
		super(VirtualListBox, self).set_data("0", data, length=len(data))
	
	def get_is_bold(self, item):
		if item not in self.bold_cache:
			self.bold_cache[item] = self.is_bold(item)

		return self.bold_cache[item]

	def is_bold(self, item):
		return False
	
	def OnGetItemAttr(self, item):
		if self.get_is_bold(item):
			return self.attr1

	#def on_size(self, event):
	#	self.SetColumnWidth(0, self.ClientSize[0])
	
class VirtualListCtrlXRC(VirtualListCtrl):
	def __init__(self):
		pre = wx.PreListCtrl()
		self.PostCreate(pre)
		self.setup()

