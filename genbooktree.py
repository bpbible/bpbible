import wx.combo
import wx
import sys
from swlib.pysw import *
from gui.treecombo import LazyTreeCombo
		
class GenBookTree(LazyTreeCombo):
	def __init__(self, parent, book, frame):
		super(GenBookTree, self).__init__(parent, style=wx.CB_READONLY)
		self.root = self.tree.GetRootItem()
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.Expand)
		#self.Bind(wx.EVT_COMBOBOX, self.OnChoice)
		#self.Bind(wx.EVT_TEXT, self.OnChoice)
		
		self.frame = frame
		wx.CallAfter(self.SetBook, book)

	def SetBook(self, book):
		self.root = self.tree.GetRootItem()
		#if not self.root
		
		self.tree.DeleteChildren(self.tree.RootItem)
		
		self.book = book
		if not book.mod:
			self.tree.SetPyData(self.root, (["<empty>"], False))

		else:
			self.tk = TK(book.mod.getKey(), book.mod)
			self.tree.SetPyData(self.root, (TK(self.tk), False))
			self.tk.root()
		self.AddItems(self.root)
		self.set_value(self.tree.GetFirstChild(self.root)[0])

	def has_children(self, item):
		data = self.get_data(item)
		
		if not isinstance(data, TK):
			return isinstance(data, list)

		return self.get_data(item).hasChildren()

	def format_tree(self, item):
		data = self.get_data(item)

		if not isinstance(data, TK):
			return "<empty>"

		return unicode(self.get_data(item))
	
	def format_combo(self, item):
		data = self.get_data(item)
		if not isinstance(data, TK):
			return "<empty>"
		
		#TODO: some unicoding of this
		# Institutes uses unicode in key strings
		return self.get_data(item).breadcrumb()
	
	def get_item(self, dir):
		if dir == -1:
			value = self.popup.get_previous()

		else:
			value = self.popup.get_next()

		if not value:
			return None

		return self.popup.tree.GetItemText(value)
	
	def go(self, dir):
		if dir == -1:
			return self.popup.go_up()

		return self.popup.go_down()
		
	def go_to_parent(self, amount):
		item = self.popup.get_value()
		if not item:
			return

		for idx in range(amount):
			if not item:
				return

			item = self.popup.tree.GetItemParent(item)
		
		self.popup.set_value(item)
		
		
	
