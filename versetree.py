import wx.combo
import wx
from swlib.pysw import GetVerseStr, BookData, ChapterData
from swlib.pysw import VK, UserVK, VerseParsingError
from swlib import pysw
from gui.treecombo import LazyTreeCombo
		
class VerseTree(LazyTreeCombo):
	def __init__(self, parent, with_verses=False):
		super(VerseTree, self).__init__(parent, style=wx.TE_PROCESS_ENTER)
		self.currentverse = None
		self.with_verses = with_verses
		
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.Expand)
		#self.Bind(wx.EVT_TEXT, self.OnChoice)
		
		wx.CallAfter(self.setup)

	def setup(self):
		root = self.tree.GetRootItem()
		
		self.tree.DeleteChildren(self.tree.RootItem)
		
		self.tree.SetPyData(root, (UserVK.books, False))
		self.AddItems(root)
		#self.set_value(self.tree.GetFirstChild(root)[0])

	def has_children(self, item):
		data = self.get_data(item)
		if not self.with_verses:
			return isinstance(data, BookData) 

		return isinstance(data, (BookData, ChapterData))

	def format_tree(self, item):
		print `self.get_data(item)`
		return "%s" % self.get_data(item)
	
	def format_combo(self, item):
		data = self.get_data(item)
		if isinstance(data, BookData):
			return "%s" % data

		elif isinstance(data, ChapterData):
			parent_data = self.get_data(self.tree.GetItemParent(item))
			return "%s %s" % (parent_data, data)

		parent = self.tree.GetItemParent(item)
		parent_data = self.get_data(parent)
		grandparent_data = self.get_data(self.tree.GetItemParent(parent))
		print `grandparent_data`

		return "%s %s:%s " % (grandparent_data, parent_data, data)
	
	def set_current_verse(self, event):
		self.currentverse = event.ref
		self.SetText(pysw.internal_to_user(event.ref))

	def get_tree_item(self):
		root = self.tree.GetRootItem()
	
		text = self.GetValue()
		was_book = False
		for book in UserVK.books:
			if ("%s" % book) == text:
				was_book = True
				self.currentverse = book.bookname
				break
		else:
			try:
				# try updating verse based on user text
				# if we fail, just use old text (assuming there is any)
				self.currentverse = GetVerseStr(text, self.currentverse,
					raiseError=True, userInput=True, userOutput=False)

			except VerseParsingError:
				if not self.currentverse:
					return self.tree.GetFirstChild(root)[0]
					

		verse_key = UserVK(VK(self.currentverse))

		book, chapter = verse_key.getBookName(), verse_key.Chapter()
		verse = verse_key.Verse()

		item, cookie = self.tree.GetFirstChild(root)
		while item:
			if self.tree.GetItemText(item) == book:
				break

			item, cookie = self.tree.GetNextChild(root, cookie)

		assert item, book + " not found!"
		
		if was_book: 
			return item

		self.tree.Expand(item)
		
		item2, cookie = self.tree.GetFirstChild(item)

		while item2:
			data = self.get_data(item2)
			if data.chapter_number == chapter:
				# if : isn't in there, we take it as a chapter reference
				if not self.with_verses or ":" not in text:
					return item2
				else:
					break

			item2, cookie = self.tree.GetNextChild(item, cookie)
		
		assert item2, "Chapter '%d' not found in %s" % (chapter, book)

		self.tree.Expand(item2)
		
		item3, cookie = self.tree.GetFirstChild(item2)

		while item3:
			data = self.get_data(item3)
			if data == verse:
				return item3

			item3, cookie = self.tree.GetNextChild(item2, cookie)
		
		assert item3, "Verse '%d' not found in %s %s" % (verse, book, chapter)
