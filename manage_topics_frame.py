import wx
import guiconfig
from events import TOPIC_LIST
from passage_list import get_primary_passage_list_manager, PassageEntry
from passage_entry_dialog import PassageEntryDialog
from topic_creation_dialog import TopicCreationDialog
from xrc.manage_topics_xrc import xrcManageTopicsFrame
from manage_topics_operations import (ManageTopicsOperations,
		CircularDataException, PASSAGE_SELECTED, TOPIC_SELECTED)

class ManageTopicsFrame(xrcManageTopicsFrame):
	def __init__(self, parent):
		super(ManageTopicsFrame, self).__init__(parent)
		self.SetIcons(guiconfig.icons)
		self._manager = get_primary_passage_list_manager()
		self._operations_context = OperationsContext(self)
		self._operations_manager = ManageTopicsOperations(
				context=self._operations_context
			)
		self._selected_topic = None
		self.item_selected_type = TOPIC_SELECTED
		self.selected_passage = None
		self._init_passage_list_ctrl_headers()
		self._setup_passage_list_ctrl()
		self._setup_topic_tree()
		self._bind_events()

	def _bind_events(self):
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self.topic_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._selected_topic_changed)
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self._get_topic_tool_tip)
		self.topic_tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self._end_topic_label_edit)
		self.topic_tree.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self._begin_topic_label_edit)
		
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._show_topic_context_menu)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._passage_selected)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._passage_activated)

		# Trap the events with the topic tree and the passage list when they
		# get focus, so that we can know which one last got focus for our
		# copy and paste operations.
		self.topic_tree.Bind(wx.EVT_SET_FOCUS, self._topic_tree_got_focus)
		self.passage_list_ctrl.Bind(wx.EVT_SET_FOCUS, self._passage_list_got_focus)

		self.passage_list_ctrl.Bind(wx.EVT_CHAR, self._handle_accelerators)
		self.topic_tree.Bind(wx.EVT_CHAR, self._handle_accelerators)

		# Not yet supported: "undo_tool", "redo_tool".
		for tool in ("cut_tool", "copy_tool", "paste_tool", "delete_tool"):
			handler = lambda event, tool=tool: self._perform_toolbar_action(event, tool)
			self.toolbar.Bind(wx.EVT_TOOL, handler, id=wx.xrc.XRCID(tool))

	def _setup_topic_tree(self):
		root = self.topic_tree.AddRoot("Topics")
		self.topic_tree.SetPyData(root, self._manager)
		self._add_sub_topics(self._manager, root)
		self.topic_tree.Expand(root)

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
			old_topic.remove_passage_observers -= self._remove_topic_passage
		if self._selected_topic is not None:
			self._selected_topic.add_passage_observers += self._insert_topic_passage
			self._selected_topic.remove_passage_observers += self._remove_topic_passage

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
			id, cookie = self.topic_tree.GetNextChild(tree_item, cookie)

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

		parent_list.remove_subtopic_observers.add_observer(
				self._remove_topic_node,
				(parent_node,))

		for subtopic in parent_list.subtopics:
			self._add_topic_node(subtopic, parent_node)
	
	def _add_topic_node(self, passage_list, parent_node):
		node = self.topic_tree.AppendItem(parent_node, passage_list.name)
		self.topic_tree.SetPyData(node, passage_list)
		self._add_sub_topics(passage_list, node)
	
	def _add_new_topic_node(self, parent_node, topic):
		self._add_topic_node(topic, parent_node)

	def _remove_topic_node(self, parent_node, topic):
		topic_node = self._find_topic(parent_node, topic)
		self.topic_tree.Delete(topic_node)
	
	def _get_topic_tool_tip(self, event):
		"""Gets the description for a topic.
		
		Note that this is Windows only, but it doesn't appear that there is
		any way for us to make our own tool tips without tracking the
		underlying window's mouse movements.
		"""
		event.SetToolTip(self.topic_tree.GetPyData(event.GetItem()).description)

	def _begin_topic_label_edit(self, event):
		"""This event is used to stop us editing the root node."""
		if event.GetItem() == self.topic_tree.RootItem:
			event.Veto()
	
	def _end_topic_label_edit(self, event):
		"""This event is used to update the names of topics.
		
		Any topic node can be edited, and its name will then be set based on
		the new label text.
		"""
		if not event.IsEditCancelled():
			topic = self.topic_tree.GetPyData(event.GetItem())
			topic.name = event.GetLabel()

	def _handle_accelerators(self, event):
		"""Handle the keyboard shortcuts required by the frame."""
		if not event.GetModifiers() and event.KeyCode == wx.WXK_DELETE:
			self._operations_manager.delete()
		if event.GetModifiers() != wx.MOD_CMD:
			event.Skip()
			return

		actions = {
			"c":	self._operations_manager.copy,
			"x":	self._operations_manager.cut,
			"v":	self._operations_manager.paste,
		}
		# It appears that the KeyCode we get is the index of the letter in
		# the alphabet for some reason.
		char = chr(event.KeyCode + ord('a') - 1)
		try:
			actions[char]()
		except KeyError:
			event.Skip()
		except CircularDataException:
			wx.MessageBox("Cannot copy the topic to one of its children.",
					"Copy Topic", wx.OK | wx.ICON_ERROR, self)

	def _perform_toolbar_action(self, event, tool_id):
		"""Performs the action requested from the toolbar."""
		event.Skip()
		actions = {
			"copy_tool":	self._operations_manager.copy,
			"cut_tool":		self._operations_manager.cut,
			"paste_tool":	self._operations_manager.paste,
			"delete_tool":	self._operations_manager.delete,
			#"undo_tool":	self._operations_manager.undo,
			#"redo_tool":	self._operations_manager.redo,
		}
		actions[tool_id]()
	
	def _show_topic_context_menu(self, event):
		"""Shows the context menu for a topic in the topic tree."""
		self._selected_topic = self.topic_tree.GetPyData(event.Item)
		menu = wx.Menu()
		
		item = menu.Append(wx.ID_ANY, "&New Topic")
		self.Bind(wx.EVT_MENU,
				lambda e: self._create_topic(self._selected_topic),
				id=item.Id)
		
		item = menu.Append(wx.ID_ANY, "Add &Passage")
		self.Bind(wx.EVT_MENU,
				lambda e: self._create_passage(),
				id=item.Id)

		item = menu.Append(wx.ID_ANY, "Delete &Topic")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.delete(),
				id=item.Id)
		
		self.PopupMenu(menu)

	def _create_topic(self, topic):
		dialog = TopicCreationDialog(self, topic)
		
		# show it modally so we can destroy it afterwards
		dialog.ShowModal()
		dialog.Destroy()
	
	def _create_passage(self):
		passage_entry = PassageEntry(None)
		dialog = PassageEntryDialog(self, passage_entry)
		if dialog.ShowModal() == wx.ID_OK:
			self._operations_manager.add_passage(passage_entry)
		dialog.Destroy()
	
	def _on_close(self, event):
		self._remove_observers(self._manager)
		if self._selected_topic is not None:
			self._selected_topic.add_passage_observers -= self._insert_topic_passage
			self._selected_topic.remove_passage_observers -= self._remove_topic_passage
		self._manager.save()
		event.Skip()
	
	def _remove_observers(self, parent_topic):
		parent_topic.add_subtopic_observers.remove(self._add_new_topic_node)
		parent_topic.remove_subtopic_observers.remove(self._remove_topic_node)
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

	def _remove_topic_passage(self, passage_entry, index):
		self.passage_list_ctrl.DeleteItem(index)
		if not passage_entry.parent.passages:
			self.selected_passage = None
		else:
			if len(passage_entry.parent.passages) == index:
				index -= 1
			self._select_list_entry_by_index(index)

	def _passage_selected(self, event):
		passage_entry = self._selected_topic.passages[event.GetIndex()]
		self.selected_passage = passage_entry
		# Do nothing.

	def _passage_activated(self, event):
		passage_entry = self._selected_topic.passages[event.GetIndex()]
		guiconfig.mainfrm.set_bible_ref(str(passage_entry), source=TOPIC_LIST)

	def _select_list_entry_by_index(self, index):
		"""Selects the entry in the list control with the given index."""
		state = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
		self.passage_list_ctrl.SetItemState(index, state, state)

	def _topic_tree_got_focus(self, event):
		self.item_selected_type = TOPIC_SELECTED
		event.Skip()

	def _passage_list_got_focus(self, event):
		self.item_selected_type = PASSAGE_SELECTED
		event.Skip()

class OperationsContext(object):
	"""Provides a context for passage list manager operations.

	This gives access to which passage and topic are currently selected in
	the manager.
	"""
	def __init__(self, frame):
		self._frame = frame

	def get_selected_topic(self):
		#return self._frame._get_tree_selected_topic()
		return self._frame._selected_topic

	def get_selected_passage(self):
		return self._frame.selected_passage

	def get_selected_item(self):
		item_selected_type = self._frame.item_selected_type
		if item_selected_type == PASSAGE_SELECTED:
			item = self.get_selected_passage()
		elif item_selected_type == TOPIC_SELECTED:
			item = self.get_selected_topic()
		return (item, item_selected_type)
