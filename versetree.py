import wx.combo
import wx
import sys
from swlib.pysw import *
from backend.book import GetVerseStr
from gui.treecombo import LazyTreeCombo
		
class VerseTree(LazyTreeCombo):
	def __init__(self, parent):
		super(VerseTree, self).__init__(parent, style=wx.TE_PROCESS_ENTER)
		self.root = self.tree.GetRootItem()
		self.currentverse = None
		
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.Expand)
		self.Bind(wx.EVT_TEXT, self.OnChoice)
		
		wx.CallAfter(self.setup)

	def setup(self):
		self.root = self.tree.GetRootItem()
		#if not self.root
		
		self.tree.DeleteChildren(self.tree.RootItem)
		
		self.tree.SetPyData(self.root, (VK.books, False))
		self.AddItems(self.root)
		#self.set_value(self.tree.GetFirstChild(self.root)[0])

	def has_children(self, item):
		return isinstance(self.get_data(item), BookData)

	def format_tree(self, item):
		return str(self.get_data(item))
	
	def format_combo(self, item):
		data = self.get_data(item)
		if isinstance(data, BookData):
			return str(data)

		else:
			parent_data = str(self.get_data(self.tree.GetItemParent(item)))
			return parent_data+" "+str(data)
	
	def set_current_verse(self, event):
		self.currentverse = event.ref

	def get_tree_item(self):
		text = self.GetValue()
		was_book = False
		for book in VK.books:
			if str(book) == text:
				was_book = True
				self.currentverse = str(text)
				break
		else:
			try:
				# try updating verse based on user text
				# if we fail, just use old text (assuming there is any)
				self.currentverse = str(GetVerseStr(text, self.currentverse,
					raiseError=True))
			except VerseParsingError, e:
				if not self.currentverse:
					return self.tree.GetFirstChild(self.root)[0]
					

		vk = VK(self.currentverse)
		book, chapter = vk.getBookName(), vk.Chapter()
		root = self.tree.GetRootItem()
		item, cookie = self.tree.GetFirstChild(root)
		while item:
			if self.tree.GetItemText(item) == book:
				break
			item, cookie = self.tree.GetNextChild(root, cookie)

		assert item, book + " not found!"
		
		if was_book: return item
		self.tree.Expand(item)
		
		item2, cookie = self.tree.GetFirstChild(item)
		while item2:
			data = self.get_data(item2)
			if data == chapter:
				return item2

			item2, cookie = self.tree.GetNextChild(item, cookie)

		assert False, "Chapter '%d' not found in %s" % (chapter, book)
