import wx
from passage_list import get_primary_passage_list_manager, PassageEntry
import guiconfig
from passage_entry_dialog import PassageEntryDialog
from topic_creation_dialog import TopicCreationDialog
from xrc.passage_list_manager_xrc import xrcPassageListManagerFrame
from events import TOPIC_LIST

class PassageListManagerFrame(xrcPassageListManagerFrame):
	def __init__(self, parent):
		super(PassageListManagerFrame, self).__init__(parent)
		self._manager = get_primary_passage_list_manager()
		self._setup_tree()
		self._bind_events()
		guiconfig.mainfrm.bible_observers += self.passage_preview.RefreshUI
	
	def _setup_tree(self):
		self.root = self.tree.AddRoot("Topics")
		self.tree.SetPyData(self.root,
				PassageListData(self._manager, self.root))
		self._add_sub_topics(self._manager, self.root)
		self.tree.Expand(self.root)
	
	def _bind_events(self):
		self.Bind(wx.EVT_CLOSE, self._onClose)
		self.tree.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self._begin_tree_label_edit)
		self.tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self._end_tree_label_edit)
		self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._tree_item_activated)
		self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._tree_item_changed)
		self.tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self._get_tool_tip)
		self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self._get_context_menu)

	def _add_sub_topics(self, parent_list, parent_node):
		parent_list.add_subtopic_observers.add_observer(
				self._add_new_passage_list,
				(parent_node,))

		for subtopic in parent_list.subtopics:
			self._add_passage_list(subtopic, parent_node)
	
	def _add_passage_list(self, passage_list, parent_node):
		node = self._get_data(parent_node).insert_passage_list(passage_list, self.tree)
		self._add_sub_topics(passage_list, node)
		passage_list.add_passage_observers.add_observer(
				self._add_new_passage_entry, (node,))
		for passage in passage_list.passages:
			self._add_passage_entry(passage, node)
	
	def _add_passage_entry(self, passage_entry, parent):
		node = self.tree.AppendItem(parent, str(passage_entry))
		self.tree.SetPyData(node, PassageEntryData(passage_entry))
		passage_entry.observers.add_observer(
				self._update_passage_entry, (node,))
	
	def _update_passage_entry(self, item):
		"""Updates the passage label when the passage entry changes."""
		self.tree.SetItemText(
				item, str(self.tree.GetPyData(item).passage_entry))
	
	def _add_new_passage_entry(self, parent, passage_entry):
		self._add_passage_entry(passage_entry, parent)

	def _begin_tree_label_edit(self, event):
		"""This event is used to limit the labels the user can edit.

		Users are not permitted to edit passages, since their text is just
		the passage reference and is not changeable.
		"""
		if not self._get_data(event).can_edit_label:
			event.Veto()

	def _end_tree_label_edit(self, event):
		"""This event is used to update the names of passage lists.
		
		Any passage list node can be edited, and its name will then be set
		based on the new label text.
		Other types of data should never receive this event, since the
		begin label edit event above will veto the editing.
		"""
		if not event.IsEditCancelled():
			self._get_data(event).label_changed(event.GetLabel())

	def _tree_item_activated(self, event):
		"""Opens the passage the user has activated in the tree."""
		self._get_data(event).activated()
	
	def _tree_item_changed(self, event):
		"""Sets the verse preview window to the text for the selected item."""
		self._get_data(event).item_selected(self, self.passage_preview)
	
	def _get_tool_tip(self, event):
		"""Gets the description or comment for a passage or topic.
		
		Note that this is Windows only, but it doesn't appear that there is
		any way for us to make our own tool tips without tracking the
		underlying window's mouse movements.
		"""
		event.SetToolTip(self._get_data(event).comment)
	
	def _add_new_passage_list(self, node, passage_list):
		self._add_passage_list(passage_list, node)
	
	def _get_context_menu(self, event):
		menu = self._get_data(event).create_menu(self)
		self.PopupMenu(menu)
	
	def _onClose(self, event):
		self._remove_observers(self._manager)
		guiconfig.mainfrm.bible_observers -= self.passage_preview.RefreshUI
		self._manager.save()
		event.Skip()
	
	def _remove_observers(self, parent_list):
		parent_list.add_subtopic_observers.remove(self._add_new_passage_list)
		for subtopic in parent_list.subtopics:
			subtopic.add_passage_observers.remove(self._add_new_passage_entry)
			self._remove_observers(subtopic)

			for passage_entry in subtopic.passages:
				passage_entry.observers.remove(self._update_passage_entry)

	def _get_data(self, item):
		"""Gets the Python data for the given item.
		
		If the item is a TreeEvent, then the item that the event applies to
		is extracted.
		"""
		try:
			item = item.GetItem()
		except AttributeError:
			pass
		return self.tree.GetPyData(item)

class PassageListData(object):
	"""This class manages a passage list node data.

	It adds additional information that is necessary for the management of
	the node, as well as the passage list.
	"""
	def __init__(self, passage_list, node):
		self.passage_list = passage_list
		self.node = node
		self.last_topic_node = None
	
	can_edit_label = True
	
	def label_changed(self, new_label):
		self.passage_list.name = new_label

	def activated(self):
		"""This method is called when the associated tree item is activated.

		It does nothing with the event.
		"""
	
	def item_selected(self, parent, preview_pane):
		"""Acts on this item becoming the currently selected item.

		parent: The parent frame.
		previewPane: A pane that can be filled with any text or reference
			that this item requires.
		"""
		preview_pane.SetPage(self.passage_list.description)

	def get_comment(self):
		return self.passage_list.description
	
	comment = property(get_comment)
	
	def insert_passage_list(self, passage_list, tree):
		node = self._insert_node(passage_list.name, tree)
		self.last_topic_node = node
		tree.SetPyData(node, PassageListData(passage_list, node))
		# XXX: Noting an item as having children is fairly misleading if it
		# doesn't.  In the future, we should use images to distinguish the
		# different types of nodes in the tree.
		# tree.SetItemHasChildren(node)
		return node

	def _insert_node(self, name, tree):
		if self.last_topic_node is None:
			if tree.GetChildrenCount(self.node, False) > 0:
				node = tree.InsertItemBefore(self.node, 0, name)
			else:
				node = tree.AppendItem(self.node, name)
		else:
			node = tree.InsertItem(self.node, self.last_topic_node, name)
		return node
	
	def create_menu(self, parent):
		"""Creates and returns the popup menu that should be displayed.

		parent: The parent frame.
		"""
		menu = wx.Menu()
		id = wx.NewId()
		parent.Bind(wx.EVT_MENU,
				lambda event: self._createTopic(parent),
				id=id)
		menu.Append(id, "&New Topic")
		id = wx.NewId()
		parent.Bind(wx.EVT_MENU,
				lambda event: self._createPassage(parent),
				id=id)
		menu.Append(id, "Add &Passage")
		return menu

	def _createTopic(self, parent):
		dialog = TopicCreationDialog(parent, self.passage_list)
		dialog.Show()
	
	def _createPassage(self, parent):
		passage_entry = PassageEntry(None)
		dialog = PassageEntryDialog(parent, passage_entry)
		if dialog.ShowModal() == wx.ID_OK:
			self.passage_list.add_passage(passage_entry)
		dialog.Destroy()

class PassageEntryData(object):
	def __init__(self, passage_entry):
		self.passage_entry = passage_entry

	can_edit_label = False

	def activated(self):
		"""This method is called when the associated tree item is activated.

		It sets the reference for the application to the reference for this
		passage entry.
		"""
		guiconfig.mainfrm.set_bible_ref(
				str(self.passage_entry), source=TOPIC_LIST)
	
	def item_selected(self, parent, previewPane):
		"""Acts on this item becoming the currently selected item.

		parent: The parent frame.
		previewPane: A pane that can be filled with any text or reference
			that this item requires.
		"""
		previewPane.SetReference(str(self.passage_entry))

	def get_comment(self):
		return self.passage_entry.comment
	
	comment = property(get_comment)
	
	def create_menu(self, parent):
		menu = wx.Menu()
		id = wx.NewId()
		parent.Bind(wx.EVT_MENU,
				lambda event: self._edit_passage_entry(parent),
				id=id)
		menu.Append(id, "&Edit")
		return menu
	
	def _edit_passage_entry(self, parent):
		dialog = PassageEntryDialog(parent, self.passage_entry)
		dialog.ShowModal()
