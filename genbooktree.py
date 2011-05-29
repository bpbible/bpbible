import wx.combo
import wx
from swlib.pysw import TK, ImmutableTK
from gui.treecombo import LazyTreeCombo
		
class GenBookTree(LazyTreeCombo):
	def __init__(self, parent, book, frame):
		super(GenBookTree, self).__init__(parent, style=wx.CB_READONLY)
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.Expand)
		#self.Bind(wx.EVT_COMBOBOX, self.OnChoice)
		#self.Bind(wx.EVT_TEXT, self.OnChoice)
		
		self.frame = frame
		wx.CallAfter(self.SetBook, book)

	def SetBook(self, book, old=""):
		### TODO: the following code triggers treekey detected mutating
		### exceptions. Haven't found out why they are changing yet.
		#for item in self.data_items:
		#	item.check_changed()

		#for item in self.data_items:
		#	print `item.Persist()`, `item.getText()`
		#	if not item.thisown:
		#		print "*** WARNING: not thisown (%r)" % item
		#	else:
		#		item.thisown = False
		#		item.__swig_destroy__(item)

		self.tree.DeleteAllItems()#Children(self.tree.RootItem)
		#import gc;gc.collect()
		root = self.tree.AddRoot("<hidden root>")
		
		
		self.book = book
			

		if book.mod:
			tk = TK(book.mod.getKey(), book.mod)
			tk.root()
			itk = ImmutableTK(tk)
			self.tree.SetPyData(root, (itk, False))
			#self.data_items = [itk]

			self.AddItems(root)
			
			# clear error
			tk.Error()


			if old:
				tk.text = old
			first_child = self.tree.GetFirstChild(root)[0]
			if first_child:
				if not ord(tk.Error()) and tk.text:
					self.go_to_key(tk)
			
				else:
					self.set_value(first_child)
			
				return
		
		self.tree.SetPyData(root, (["<empty>"], False))
		self.AddItems(root)
		self.set_value(self.tree.GetFirstChild(root)[0])
				
			

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
		
		
	def go_to_key(self, tk):
		# keep a copy
		ref_to_aim_for = ImmutableTK(tk)
		
		# position both at root
		tk.root()
		tree = self.popup.tree
		tree_item = tree.RootItem

		def look_for(tree_item):
			while tk != ref_to_aim_for:
				succeeded = tk.nextSibling()
				if not succeeded or tk > ref_to_aim_for:
					if succeeded:
						# too far, go back
						tk.previousSibling()
					
					# now try in the children
					result = tk.firstChild()
					assert result, \
						"Couldn't get child even though should have a child"

					if tree_item != tree.RootItem: 
						tree.Expand(tree_item)
					tree_item, cookie = tree.GetFirstChild(tree_item)
					assert tree_item, "Couldn't find it in wx tree"

					look_for(tree_item)
					return
				else:
					tree_item = tree.GetNextSibling(tree_item)
					assert tree_item, "wxTree finished too early"

			self.popup.set_value(tree_item)
		
		look_for(tree_item)
