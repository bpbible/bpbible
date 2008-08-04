import wx
import guiconfig
from events import TOPIC_LIST
from passage_list import get_primary_passage_list_manager, PassageEntry
from passage_entry_dialog import PassageEntryDialog
from topic_creation_dialog import TopicCreationDialog
from xrc.manage_topics_xrc import xrcManageTopicsFrame

class ManageTopicsFrame(xrcManageTopicsFrame):
	def __init__(self, parent):
		super(ManageTopicsFrame, self).__init__(parent)
		self._manager = get_primary_passage_list_manager()
		self._selected_topic = None
		self._init_passage_list_ctrl_headers()
		self._setup_passage_list_ctrl()
		self._setup_topic_tree()
		self._bind_events()

	def _bind_events(self):
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self.topic_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._selected_topic_changed)
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self._get_topic_tool_tip)
		self.topic_tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self._end_topic_label_edit)
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._show_topic_context_menu)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._passage_selected)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._passage_activated)

	def _setup_topic_tree(self):
		self.root = self.topic_tree.AddRoot("Topics")
		self.topic_tree.SetPyData(self.root, self._manager)
		self._add_sub_topics(self._manager, self.root)
		self.topic_tree.Expand(self.root)

	def select_topic_and_passage(self, topic, passage_entry):
		"""Selects the given topic in the tree, and the given passage entry
		in the passage list.

		This allows the correct topic and passage to be displayed when a tag
		is clicked on.

		This assumes that the passage entry is one of the passages in the
		topic.
		"""
		self._set_selected_topic(topic)
		assert passage_entry in topic.passages
		index = topic.passages.index(passage_entry)
		self._select_list_entry_by_index(index)
		self.passage_list_ctrl.SetFocus()

	def _get_tree_selected_topic(self):
		selection = self.topic_tree.GetSelection()
		if not selection.IsOk():
			return None
		return self.topic_tree.GetPyData(selection)
	
	def _set_selected_topic(self, topic):
		tree_item = self._find_topic(self.topic_tree.GetRootItem(), topic)
		assert tree_item is not None
		self.topic_tree.SelectItem(tree_item)
		self.topic_tree.EnsureVisible(tree_item)
		return tree_item

	def _selected_topic_changed(self, event):
		old_topic = self._selected_topic
		self._selected_topic = self._get_tree_selected_topic()
		self._setup_passage_list_ctrl()

		if old_topic is not None:
			old_topic.add_passage_observers -= self._insert_topic_passage
		if self._selected_topic is not None:
			self._selected_topic.add_passage_observers += self._insert_topic_passage

		self.Title = self._get_title()
		event.Skip()

	def _find_topic(self, tree_item, topic):
		if self.topic_tree.GetPyData(tree_item) is topic:
			return tree_item

		id, cookie = self.topic_tree.GetFirstChild(tree_item)
		while id.IsOk():
			node = self._find_topic(id, topic)
			if node is not None:
				return node
			id, cookie = self.topic_tree.GetNextChild(id, cookie)

	def _get_title(self):
		"""Gets a title for the frame, based on the currently selected topic."""
		topic = self._selected_topic
		title = "Manage Topics"
		if topic is not self._manager:
			title = "%s - %s" % (topic.full_name, title)
		return title

	def _add_sub_topics(self, parent_list, parent_node):
		parent_list.add_subtopic_observers.add_observer(
				self._add_new_topic_node,
				(parent_node,))

		for subtopic in parent_list.subtopics:
			self._add_topic_node(subtopic, parent_node)
	
	def _add_topic_node(self, passage_list, parent_node):
		node = self.topic_tree.AppendItem(parent_node, passage_list.name)
		self.topic_tree.SetPyData(node, passage_list)
		self._add_sub_topics(passage_list, node)
	
	def _add_new_topic_node(self, parent_node, topic):
		try:
			self._add_topic_node(topic, parent_node)
		except:
			pass
	
	def _get_topic_tool_tip(self, event):
		"""Gets the description for a topic.
		
		Note that this is Windows only, but it doesn't appear that there is
		any way for us to make our own tool tips without tracking the
		underlying window's mouse movements.
		"""
		event.SetToolTip(self.topic_tree.GetPyData(event.GetItem()).description)

	def _end_topic_label_edit(self, event):
		"""This event is used to update the names of topics.
		
		Any topic node can be edited, and its name will then be set based on
		the new label text.
		"""
		if not event.IsEditCancelled():
			topic = self.topic_tree.GetPyData(event.GetItem())
			topic.name = event.GetLabel()
	
	def _show_topic_context_menu(self, event):
		"""Shows the context menu for a topic in the topic tree."""
		menu = wx.Menu()
		id = wx.NewId()
		self.Bind(wx.EVT_MENU,
				lambda event: self._create_topic,
				id=id)
		menu.Append(id, "&New Topic")
		id = wx.NewId()
		self.Bind(wx.EVT_MENU,
				lambda event: self._create_passage(),
				id=id)
		menu.Append(id, "Add &Passage")
		self.PopupMenu(menu)

	def _create_topic(self):
		dialog = TopicCreationDialog(self, self._selected_topic)
		dialog.Show()
	
	def _create_passage(self):
		passage_entry = PassageEntry(None)
		dialog = PassageEntryDialog(self, passage_entry)
		if dialog.ShowModal() == wx.ID_OK:
			self._selected_topic.add_passage(passage_entry)
		dialog.Destroy()
	
	def _on_close(self, event):
		self._remove_observers(self._manager)
		if self._selected_topic is not None:
			self._selected_topic.add_passage_observers -= self._insert_topic_passage
		self._manager.save()
		event.Skip()
	
	def _remove_observers(self, parent_topic):
		parent_topic.add_subtopic_observers.remove(self._add_new_topic_node)
		for subtopic in parent_topic.subtopics:
			self._remove_observers(subtopic)
	
	def _init_passage_list_ctrl_headers(self):
		self.passage_list_ctrl.InsertColumn(0, "Passage")
		self.passage_list_ctrl.InsertColumn(1, "Comment")

	def _setup_passage_list_ctrl(self):
		self.passage_list_ctrl.DeleteAllItems()
		if self._selected_topic is None:
			return

		for index, passage_entry in enumerate(self._selected_topic.passages):
			self._insert_topic_passage(passage_entry, index)

		if self._selected_topic.passages:
			self._select_list_entry_by_index(0)

	def _insert_topic_passage(self, passage_entry, index=None):
		if index is None:
			index = self._selected_topic.passages.index(passage_entry)
		self.passage_list_ctrl.InsertStringItem(index, str(passage_entry))
		self.passage_list_ctrl.SetStringItem(index, 1, passage_entry.comment)

	def _passage_selected(self, event):
		passage_entry = self._selected_topic.passages[event.GetIndex()]
		# Do nothing.

	def _passage_activated(self, event):
		passage_entry = self._selected_topic.passages[event.GetIndex()]
		guiconfig.mainfrm.set_bible_ref(str(passage_entry), source=TOPIC_LIST)

	def _select_list_entry_by_index(self, index):
		"""Selects the entry in the list control with the given index."""
		state = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
		self.passage_list_ctrl.SetItemState(index, state, state)
