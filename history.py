import wx
from util.observerlist import ObserverList
from gui.guiutil import FreezeUI
from events import HISTORY
import guiconfig

use_history_as_tree = False

class HistoryItem(object):
	def __init__(self, parent, ref):
		self.parent = parent
		self.children = []
		self.ref = ref
	
	def trim(self, child):
		assert child in self.children, "Can't trim item when not in children"
		self.remove(child)

class History(object):
	"""Manages history

	>>> from history import *
	>>> h = History()
	>>> h.can_forward()
	False
	>>> h.can_back()
	False
	>>> h.new_location("first location")
	>>> h.can_back()
	True
	>>> h.can_forward()
	False
	>>> h.new_location("second location")
	>>> h.pprint()
	 first location
	        > second location
	>>> h.can_back()
	True
	>>> h.back()
	>>> h.pprint()
	 > first location
	        second location
	>>> h.can_forward()
	True
	>>> h.new_location("third location")
	>>> h.can_forward()
	False
	>>> h.can_back()
	True
	>>> h.pprint()
	 first location
	        second location
	        > third location
	>>> h.back()
	>>> h.pprint()
	 > first location
	        second location
	        third location
	>>> h.forward()
	>>> h.pprint()
	 first location
	        second location
	        > third location
	"""

	def __init__(self):
		self.history = HistoryItem(None, None)
		self.current_item = self.history
		self.on_history_changed = ObserverList()

	def back(self):
		self.current_item = self.current_item.parent
		self.on_history_changed(self.current_item)
		return self.current_item
		

	def forward(self):
		self.current_item = self.current_item.children[-1]
		self.on_history_changed(self.current_item)
		return self.current_item

	def can_back(self):
		return self.current_item.parent is not self.history

	def can_forward(self):
		return bool(self.current_item.children)

	def new_location(self, new_location):
		if new_location == self.current_item.ref:
			return

		history_item = HistoryItem(self.current_item, new_location)
		self.current_item.children.append(history_item)
		self.current_item = history_item
		self.on_history_changed(self.current_item)

	def clear(self):
		self.history = HistoryItem(None, None)
		self.current_item = self.history
		
	def go(self, direction):
		if direction < 0:
			return self.back()
		if direction > 0:
			return self.forward()
		
	def pprint(self, item=None, level=0):
		if item is None:
			item = self.history

		for child in item.children:
			print "\t"*level, 
			if child == self.current_item:
				print ">",
			print child.ref
			self.pprint(child, level+1)

class HistoryTree(wx.TreeCtrl):
	def __init__(self, parent, history):
		self.history = history
		style = wx.TR_HIDE_ROOT|wx.TR_DEFAULT_STYLE
		if not use_history_as_tree:
			style |= wx.TR_NO_LINES
		super(HistoryTree, self).__init__(parent, style=style)
		self.history.on_history_changed += \
			lambda item:wx.CallAfter(self.rebuild_tree, item)
		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_selected)
	
		self.rebuild_tree()
		#self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.on_tree_selected)
		
		
	
	def on_tree_selected(self, event):
		item = event.GetItem()
		history_item = self.GetPyData(item)
		parent = self.history.current_item
		# if it is in our back list, go back to it
		while parent:
			if history_item == parent:
				self.history.current_item = history_item			
				break

			parent = parent.parent
		else:
			child = self.history.current_item
			# if it is in our forward list, go forward to it
			while child.children:
				child = child.children[-1]
				if history_item == child:
					self.history.current_item = history_item			
					break
			else:
				self.history.new_location(history_item.ref)

		guiconfig.mainfrm.set_bible_ref(history_item.ref, source=HISTORY)
		wx.CallAfter(self.rebuild_tree)

	def create_item(self, parent, item):
		new_tree_item = self.AppendItem(parent, text=item.ref)
		if item == self.history.current_item:
			self.SetItemBold(new_tree_item)

		self.SetPyData(new_tree_item, item)
		self.build_tree(item, new_tree_item)
	
	def build_tree(self, history_item=None, tree_item=None):
		if tree_item is None:
			tree_item = self.AddRoot("History")
			#tree_item = self.AppendItem(tree_item, "TES")

		if history_item is None:
			history_item = self.history.history

		# don't display extra ones for now...
		if use_history_as_tree:
			for item in history_item.children[:-1]:
				self.create_item(tree_item, item)

		# Put the last item as a sibling, not a child.
		# this is good way to do it
		if history_item.children[-1:]:
			item = history_item.children[-1]

			# if no parent, it is a root, so just do as sibling
			p = self.GetItemParent(tree_item) or tree_item

			self.create_item(p, item)
		
	def rebuild_tree(self, item=None):
		self.Unbind(wx.EVT_TREE_SEL_CHANGED)
	
		freeze = FreezeUI(self)
		self.DeleteAllItems()
		self.build_tree()
		root = self.GetRootItem()
		id, cookie = self.GetFirstChild(root)
		while id:
			self.ExpandAllChildren(id)
			id, cookie = self.GetNextChild(root, cookie)
		
		self.Bind(wx.EVT_TREE_SEL_CHANGED, self.on_tree_selected)
	
			

def _test_HistoryTree():
	a = wx.App(0)
	f = wx.Frame(None)
	h = History()
	h.new_location("Gen 3:16")
	h.new_location("Gen 3:17")
	h.new_location("Gen 3:18")
	h.new_location("Gen 3:19")
	h.new_location("Gen 3:20")
	h.back()
	h.back()
	h.back()
	
	h.new_location("Gen 3:20")
	ht = HistoryTree(f, h)
	f.Show()
	a.MainLoop()
	
	

	
	
def _test():
	import doctest
	doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

if __name__ == '__main__':
	_test_HistoryTree()

