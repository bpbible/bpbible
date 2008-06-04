import wx
from backend.bibleinterface import biblemgr
from swlib.pysw import SW
from gui.filterable_tree import TreeItem, FilterableTree
from util.observerlist import ObserverList
from util.unicode import to_unicode

from moduleinfo import ModuleInfo


class ModuleTree(FilterableTree):
	blank_text = "Find Book..."
	def __init__(self, parent):
		super(ModuleTree, self).__init__(parent, None)
		
		self.on_module_choice = ObserverList()

		self.module_types = (
			("Bibles", biblemgr.bible),
			("Commentaries", biblemgr.commentary),
			("Dictionaries", biblemgr.dictionary),
			("Other books", biblemgr.genbook),
		)
		

		self.on_selection += self.on_version_tree
		self.recreate()
		
	def bind_events(self):
		super(ModuleTree, self).bind_events()
		# ### Nasty hack ###
		# It seems that whenever all items are deleted, we get called by
		# sel_changed in a bad state, from which calling GetPyData crashes it.
		# So whenever an item is deleted, unbind all events.
		self.tree.Bind(wx.EVT_TREE_DELETE_ITEM, lambda evt:(evt.Skip(),
													self.unbind_events()))
		
		self.tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self.version_tree_tooltip)
		self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.version_tree_menu)
	
	def unbind_events(self):
		if not super(ModuleTree, self).unbind_events():
			return

		self.tree.Unbind(wx.EVT_TREE_ITEM_GETTOOLTIP)
		self.tree.Unbind(wx.EVT_TREE_ITEM_MENU)
		self.tree.Unbind(wx.EVT_TREE_DELETE_ITEM)
		
	def on_version_tree(self, item):
		item_data = self.tree.GetPyData(item).data

		parent = self.tree.GetItemParent(item)
		assert parent, "Item hadn't a parent!!!"

		parent_data = self.tree.GetPyData(parent)
		parent_data = parent_data.data

		if isinstance(item_data, SW.Module):
			self.on_module_choice(item_data, parent_data)
		
	def recreate(self):
		self.model = TreeItem("Hidden root")
		
		for text, book in self.module_types:
			self.model.add_child(text, data=book, filterable=False)

		for tree_item in self.model.children:
			modules = tree_item.data.GetModules()
			for module in modules: 
				tree_item.add_child(module.Name(), data=module)

		if self.search.Value:
			self.filter(self.search.Value)
		else:
			self.create()
		
	def version_tree_tooltip(self, event):
		item = event.Item
		data = self.tree.GetPyData(item)
		if isinstance(data.data, SW.Module):
			event.SetToolTip(to_unicode(data.data.Description(), data.data))
		

	def version_tree_menu(self, event):
		def make_event(module):	
			def show_information(event):
				ModuleInfo(self, module).ShowModal()

			return show_information
	
		item = event.Item
		data = self.tree.GetPyData(item).data

		if not isinstance(data, SW.Module): 
			return

		menu = wx.Menu()
		item = menu.Append(
			wx.ID_ANY, 
			"Show information for %s" % data.Name()
		)

		menu.Bind(wx.EVT_MENU, make_event(data), item)
		self.tree.PopupMenu(menu, event.Point)

if __name__ == '__main__':
	a = wx.App(0)
	f = wx.Frame(None)
	tree = ModuleTree(f)
	f.Show()
	a.MainLoop()
