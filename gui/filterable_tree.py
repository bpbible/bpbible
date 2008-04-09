import wx
from gui import guiutil

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

from wx.lib.mixins.treemixin import ExpansionState

class FilterableTreeCtrl(ExpansionState, wx.TreeCtrl):
	pass

class FilterableTree(wx.PyPanel):
	blank_text = "Search"
	def __init__(self, parent, model):
		self.model = model
		super(FilterableTree, self).__init__(parent)

		self.tree = FilterableTreeCtrl(self, 
			style=wx.TR_HAS_BUTTONS   |
				  wx.TR_LINES_AT_ROOT |
				  wx.TR_HIDE_ROOT  
		)
		
		self.search = wx.SearchCtrl(self, style=wx.TE_PROCESS_ENTER)

		style = self.search.WindowStyle
		
		if style & wx.SIMPLE_BORDER:
			style ^= wx.SIMPLE_BORDER
			self.search.WindowStyle = style

		self.search.SetDescriptiveText(self.blank_text)
		self.search.ShowCancelButton(True)
		self.search.Bind(wx.EVT_TEXT, lambda evt:self.filter(self.search.Value))
		self.search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN,
			self.clear_filter)

		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add(self.search, 0, wx.GROW)
		sizer.Add(self.tree, 1, wx.GROW)
		
		self.SetSizer(sizer)
		self.expansion_state = None
	
	def create(self, model=None):
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
		self.ExpandAll()
	
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

	
	def clear_filter(self, evt=None):
		#expansion_state = self.tree.GetExpansionState()
		self.search.SetValue("")
		self.create()
		#self.tree.SetExpansionState(expansion_state)
		
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

		item = FindTreeItem(self.root)
		assert item, "Didn't find pericope in tree"
		
		self.tree.SelectItem(item)

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

	model = model_from_list(L)
	tree = FilterableTree(f, model)
	tree.create()
	f.Show()
	a.MainLoop()
