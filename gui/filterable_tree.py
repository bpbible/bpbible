import wx
from gui import guiutil
from util import osutils
from util.observerlist import ObserverList
import string

def GetPrevVisible(self, item):
	"""Taken from the wxgeneric GetPrevVisible. 
	
	This is missing in wxGTK 2.8.* and wxMac 2.8.4.1"""
	assert item.IsOk(), "invalid tree item"
	assert self.IsVisible(item), "this item itself should be visible"

	# find out the starting point
	prevItem = self.GetPrevSibling(item)
	if not prevItem.IsOk():
		prevItem = self.GetItemParent(item);

	# find the first visible item after it
	while prevItem.IsOk() and not self.IsVisible(prevItem):
		prevItem = self.GetNext(prevItem)
		if not prevItem.IsOk() or prevItem == item:
			# there are no visible items before item
			return wx.TreeItemId()

	# from there we must be able to navigate until this item
	while ( prevItem.IsOk() ):
		nextItem = self.GetNextVisible(prevItem);
		if not nextItem.IsOk() or nextItem == item:
			break;

		prevItem = nextItem

	return prevItem

if osutils.is_gtk() or osutils.is_mac():
	wx.TreeCtrl.GetPrevVisible = GetPrevVisible

class TreeItem(object):
	def __init__(self, text, data=None, filterable=True):
		self._children = []
		self._text = text
		self.data = data
		self.filterable = filterable
		#if self.parent:
		#	self.parent.children.append(self)
	
	@property
	def text(self):
		return self._text
	
	@property
	def children(self):
		return tuple(self._children)
	
	def has_children(self):
		return len(self.children) > 0
	
	def add_child(self, text, item=None, data=None, filterable=True):
		if item is None:
			item = TreeItem(text, data, filterable)

		self._children.append(item)
		return item
	
	def clone_item(self):
		return TreeItem(self.text, self.data)

	def null_item(self):
		# shouldn't be seen, so no i18n needed
		return TreeItem("No items")

def model_from_list(items):
	root = TreeItem("<Hidden root>")

	def process(parent, items):
		for item in items:
			if isinstance(item, tuple):
				child = parent.add_child(item[0])
				process(child, item[1])
			else:
				parent.add_child(item)
		
	process(root, items)

	return root

class SearchCtrl(wx.SearchCtrl):
	keys_to_pass_on = [wx.WXK_UP, wx.WXK_DOWN, wx.WXK_RETURN]

	def __init__(self, parent):
		super(SearchCtrl, self).__init__(parent, style=wx.WANTS_CHARS)
		self.bind_source = self.find_bind_source()
		self.bind_source.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

	def find_bind_source(self):
		for item in self.Children:
			if isinstance(item, wx.TextCtrl):
				return item

		return self
	
	def on_key_down(self, event):
		if event.KeyCode == wx.WXK_ESCAPE:
			evt = wx.CommandEvent(wx.EVT_SEARCHCTRL_CANCEL_BTN.typeId)
			evt.Id = self.Id
			self.EventHandler.ProcessEvent(evt)

		else:
			# under gtk, our tab messages get munged
			if event.KeyCode == wx.WXK_TAB and \
				(event.Modifiers in	(wx.MOD_SHIFT, wx.MOD_NONE)):
				self.Navigate(event.ShiftDown())

			if self.bind_source != self and \
				event.KeyCode in self.keys_to_pass_on:

				event.Id = self.Id
				self.EventHandler.AddPendingEvent(event)
			else:
				event.Skip()

class FilterableTree(wx.PyPanel):
	blank_text = "Search"
	def __init__(self, parent, model):
		self.model = model
		super(FilterableTree, self).__init__(parent)

		self.bound = False
		
		self.tree = wx.TreeCtrl(self, 
			style=wx.TR_HAS_BUTTONS   |
				  wx.TR_LINES_AT_ROOT |
				  wx.TR_HIDE_ROOT
		)
		
		self.search = SearchCtrl(self)

		self.search.SetDescriptiveText(self.blank_text)
		self.search.ShowCancelButton(True)
		
		self.search.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
		self.search.Bind(wx.EVT_TEXT, lambda evt:self.filter(self.search.Value))
		self.search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN,
			self.clear_filter)

		self.on_selection = ObserverList()

		sizer = wx.BoxSizer(wx.VERTICAL)

		if osutils.is_mac():
			sizer.Add(self.search, 0, wx.GROW|wx.ALL, 3)
			sizer.Add(self.tree, 1, wx.GROW|wx.TOP, 6)
		else:
			sizer.Add(self.search, 0, wx.GROW|wx.BOTTOM, 3)
			sizer.Add(self.tree, 1, wx.GROW)

		self.SetSizer(sizer)
		self.expansion_state = None
		self.bind_events()
		
	
	def select_without_event(self, item):
		self.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)
		self.tree.SelectItem(item)
		self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, 
			lambda evt:self.on_selection(evt.Item))
		
	def on_key_down(self, event):
		selection = self.tree.GetSelection()
		
		if event.KeyCode == wx.WXK_UP:
			prev = self.tree.GetPrevVisible(selection)
			if prev:
				self.select_without_event(prev)

		elif event.KeyCode == wx.WXK_DOWN:
			prev = self.tree.GetNextVisible(selection)
			if prev:
				self.select_without_event(prev)
		
		elif event.KeyCode == wx.WXK_RETURN:
			self.on_selection(selection)
		else:
			event.Skip()

	def create(self, model=None):
		self.unbind_events()
	
		d = guiutil.FreezeUI(self)
		if model is None:
			model = self.model

		self.tree.DeleteAllItems()
		root = self.tree.AddRoot(model.text)
		self.tree.SetPyData(root, model)
		
		def add(parent, model_item):
			child = self.tree.AppendItem(parent, model_item.text)
			self.tree.SetPyData(child, model_item)
			
			for item in model_item.children:
				add(child, item)

		for item in model.children:
			add(root, item)

		self.bind_events()
		
		self.ExpandAll()
		
	def bind_events(self):
		self.bound = True
		self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, 
			lambda evt:self.on_selection(evt.Item))
		
	
	def unbind_events(self):
		if not self.bound:
			return False

		self.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)

		self.bound = False
		return True
	
	
	def filter(self, text):
		def get_filtered_items(model_item):
			return_item = model_item.clone_item()
			for item in model_item.children:
				ansa = get_filtered_items(item)
				if ansa:
					return_item.add_child(text=None, item=ansa)

			# if we are not filterable, or the text is not in our text, and we
			# haven't any children matching, return None
			if (not model_item.filterable 
				or text.upper() not in model_item.text.upper()) \
				and not return_item.children:
				return None

			return return_item

		root = get_filtered_items(self.model)
		if not root:
			root = self.model.null_item()

		self.create(root)
	
	def ExpandAll(self):
		root = self.tree.GetRootItem()
		assert root
		item, cookie = self.tree.GetFirstChild(root)

		first_child = None
		
		while item:
			if first_child is None:
				first_child = item
			
			self.tree.ExpandAllChildren(item)
			item, cookie = self.tree.GetNextChild(root, cookie)			
			
		if first_child:
			self.tree.ScrollTo(first_child)
			self.select_without_event(first_child)

	def clear_filter(self, evt=None):
		self.search.SetValue("")
		self.create()
		
	def show_item(self, item_data):
		if self.search.Value:
			self.clear_filter()

		def FindTreeItem(current):
			child, cookie = self.tree.GetFirstChild(current)
			while child:
				if self.tree.GetPyData(child) == item_data:
					return child

				r = FindTreeItem(child)
				if r: 
					return r

				child, cookie = self.tree.GetNextChild(current, cookie)

		item = FindTreeItem(self.tree.RootItem)
		assert item, "Didn't find pericope in tree"
		
		self.select_without_event(item)

if __name__ == '__main__':
	a = wx.App(0)
	f = wx.Frame(None)
	L = [
		"test", 
		"ing", 
		("what", (
			"test", 
			("ing", (
				"bip",
				"bop",
				"bitje"
				)
			)
		))
		
	]	
	
	def print_(x):
		print x

	model = model_from_list(L)
	tree = FilterableTree(f, model)
	tree.create()
	tree.on_selection += print_
	f.Show()
	tree.SetFocus()
	
	a.MainLoop()
