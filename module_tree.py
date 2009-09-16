import wx
from backend.bibleinterface import biblemgr
from swlib.pysw import SW
from gui.filterable_tree import TreeItem, FilterableTree
from util.observerlist import ObserverList
from util.unicode import to_unicode
from util.debug import dprint, ERROR

from moduleinfo import ModuleInfo
from util import languages
from wx.lib.customtreectrl import CustomTreeCtrl, \
	TR_AUTO_CHECK_CHILD, TR_AUTO_CHECK_PARENT, TR_HAS_VARIABLE_ROW_HEIGHT


class ModuleTree(FilterableTree):
	def __init__(self, parent):
		super(ModuleTree, self).__init__(parent, None)
		
		self.on_module_choice = ObserverList()
		self.on_category_choice = ObserverList()

		self.module_types = (
			(_("Bibles"), biblemgr.bible),
			(_("Commentaries"), biblemgr.commentary),
			(_("Dictionaries"), biblemgr.dictionary),
			(_("Other books"), biblemgr.genbook),
		)
		

		self.on_selection += self.on_version_tree
		self.recreate()
	
	@property
	def blank_text(self):
		return _("Find Book...")

	def bind_events(self):
		super(ModuleTree, self).bind_events()
		# ### Nasty hack ###
		# It seems that whenever all items are deleted, we get called by
		# sel_changed in a bad state, from which calling GetPyData crashes it.
		# So whenever an item is deleted, unbind all events.
		self.tree.Bind(wx.EVT_TREE_DELETE_ITEM, lambda evt:(evt.Skip(),
													self.unbind_events()))
		
		self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.version_tree_menu)
	
	def unbind_events(self):
		if not super(ModuleTree, self).unbind_events():
			return

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
		else:
			self.on_category_choice(item_data, parent_data)
		
	def recreate(self):
		self.model = TreeItem("Hidden root")
		
		self.add_first_level_groups()

		for tree_item in self.model.children:
			self.add_children(tree_item)

		if self.search.Value:
			self.filter(self.search.Value)
		else:
			self.create()
		
	def version_tree_tooltip(self, event):
		item = event.GetItem()
		data = self.tree.GetPyData(item)
		if isinstance(data.data, SW.Module):
			event.SetToolTip(to_unicode(data.data.Description(), data.data))
		
	def version_tree_menu(self, event):
		item = event.GetItem()
		if not item:
			return

		data = self.tree.GetPyData(item).data

		if not isinstance(data, SW.Module): 
			return

		menu = wx.Menu()
		self.add_menu_items(data, menu)
		self.tree.PopupMenu(menu, event.GetPoint())
	
	def add_menu_items(self, data, menu):
		def make_event(module):	
			def show_information(event):
				ModuleInfo(self, module).ShowModal()

			return show_information
	
		
		item = menu.Append(		
			wx.ID_ANY, 
			_("Show information for %s") % data.Name()
		)

		menu.Bind(wx.EVT_MENU, make_event(data), item)
	
	
	def add_first_level_groups(self):
		for text, book in self.module_types:
			self.model.add_child(text, data=book, filterable=False)	

	def add_children(self, tree_item):
		modules = tree_item.data.GetModules()
		for module in modules: 
			self.add_module(tree_item, module)
	
	def add_module(self, tree_item, module, inactive_description=""):
		text = "%s - %s" % (
			module.Name(), to_unicode(module.Description(), module))
		
		if biblemgr.all_modules[module.Name()] != module:
			text += inactive_description

		tree_item.add_child(text, data=module)
	
class PathModuleTree(ModuleTree):
	def CreateTreeCtrl(self, parent, style):
		tree = wx.lib.customtreectrl.CustomTreeCtrl(parent, 
			style=style^wx.TR_LINES_AT_ROOT|TR_AUTO_CHECK_CHILD|TR_AUTO_CHECK_PARENT|TR_HAS_VARIABLE_ROW_HEIGHT|wx.SUNKEN_BORDER)

		#tree.EnableSelectionGradient(False)
		#tree.EnableSelectionVista(True)
		return tree
	
	def AppendItemToTree(self, parent, text):
		return self.tree.AppendItem(parent, text, ct_type=1)
		
	
	def add_first_level_groups(self):
		for path, mgr, modules in reversed(biblemgr.mgrs):
			self.model.add_child(path, data=mgr)
	
	def add_children(self, tree_item):
		for path, mgr, modules in reversed(biblemgr.mgrs):
			if mgr == tree_item.data:
				for modname, mod in sorted(modules, key=lambda x:x[0].lower()):
					self.add_module(tree_item, mod, 
						"\nThis book is not active as it "
						"is shadowed by a book in a different path")
				break
		else:
			dprint(ERROR, "Did not find mgr in list", mgr)

class LanguageModuleTree(ModuleTree):
	def add_first_level_groups(self):
		def module_lang(x):
			if x == "Greek":
				return "grc"
			if x == "Hebrew":
				return "he"
			return module.Lang()
		language_mappings = {}
		self.data = {}
		for module in biblemgr.modules.values() + ["Greek", "Hebrew"]:
			lang = module_lang(module)
			if lang not in language_mappings:
				language_mappings[lang] = \
					languages.get_language_description(lang)

			d=self.data.setdefault(lang, [])
			if isinstance(module, SW.Module):
				d.append(module)
		
		for lang, mapping in sorted(language_mappings.items(), 
			key=lambda (lang, mapping): mapping):
			self.model.add_child(mapping, data=lang)
	
	def add_children(self, tree_item):
		for mod in sorted(self.data[tree_item.data], 
							key=lambda mod:mod.Name.lower()):
			self.add_module(tree_item, mod)
	
if __name__ == '__main__':
	from util import i18n
	i18n.initialize()

	a = wx.App(0)
	f = wx.Frame(None)
	tree = PathModuleTree(f)
	f.Show()
	a.MainLoop()
