import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import guiconfig
from events import TOPIC_LIST
from passage_list import (get_primary_passage_list_manager,
		lookup_passage_entry, PassageEntry)
from passage_entry_dialog import PassageEntryDialog
from topic_creation_dialog import TopicCreationDialog
from xrc.manage_topics_xrc import xrcManageTopicsFrame
from xrc.xrc_util import attach_unknown_control
from gui import guiutil
from manage_topics_operations import (ManageTopicsOperations,
		CircularDataException, PASSAGE_SELECTED, TOPIC_SELECTED)

class ManageTopicsFrame(xrcManageTopicsFrame):
	def __init__(self, parent):
		super(ManageTopicsFrame, self).__init__(parent)
		attach_unknown_control("topic_tree", lambda parent: TopicTree(self, parent), self)
		attach_unknown_control("passage_list_ctrl", lambda parent: PassageListCtrl(self, parent), self)
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
		self.Size = (650, 500)

	def _bind_events(self):
		self.Bind(wx.EVT_CLOSE, self._on_close)
		self.topic_tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._selected_topic_changed)
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_GETTOOLTIP, self._get_topic_tool_tip)
		self.topic_tree.Bind(wx.EVT_TREE_END_LABEL_EDIT, self._end_topic_label_edit)
		self.topic_tree.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self._begin_topic_label_edit)
		
		self.topic_tree.Bind(wx.EVT_TREE_ITEM_MENU, self._show_topic_context_menu)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._passage_selected)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._passage_activated)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._show_passage_context_menu)

		# Trap the events with the topic tree and the passage list when they
		# get focus, so that we can know which one last got focus for our
		# copy and paste operations.
		self.topic_tree.Bind(wx.EVT_SET_FOCUS, self._topic_tree_got_focus)
		self.passage_list_ctrl.Bind(wx.EVT_SET_FOCUS, self._passage_list_got_focus)

		self.passage_list_ctrl.Bind(wx.EVT_KEY_UP, self._on_char)
		self.topic_tree.Bind(wx.EVT_KEY_UP, self._on_char)

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
		# Topic nodes are selected as they are dragged past, but we shouldn't
		# change the selected topic and passage list until the dragging has
		# been finished.
		if self.topic_tree._dragging:
			event.Skip()
			return

		old_topic = self._selected_topic
		selected_topic = self._get_tree_selected_topic()
		if selected_topic is None:
			event.Skip()
			return

		self._selected_topic = selected_topic
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

	def _on_char(self, event):
		"""Handles all keyboard shortcuts."""
		guiutil.dispatch_keypress(self._get_actions(), event)

	def _get_actions(self):
		"""Returns a list of actions to be used when handling keyboard
		shortcuts.
		"""
		return {
			(ord("C"), wx.MOD_CMD): self._operations_manager.copy,
			(ord("X"), wx.MOD_CMD): self._operations_manager.cut,
			(ord("V"), wx.MOD_CMD): self._safe_paste,
			wx.WXK_DELETE: self._operations_manager.delete,
		}

	def _perform_toolbar_action(self, event, tool_id):
		"""Performs the action requested from the toolbar."""
		event.Skip()
		actions = {
			"copy_tool":	self._operations_manager.copy,
			"cut_tool":		self._operations_manager.cut,
			"paste_tool":	self._safe_paste,
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

		menu.AppendSeparator()
		
		item = menu.Append(wx.ID_ANY, "Cu&t")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.cut,
				id=item.Id)

		item = menu.Append(wx.ID_ANY, "&Copy")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.copy,
				id=item.Id)

		item = menu.Append(wx.ID_ANY, "&Paste")
		self.Bind(wx.EVT_MENU,
				lambda e: self._safe_paste,
				id=item.Id)

		menu.AppendSeparator()
		
		item = menu.Append(wx.ID_ANY, "Delete &Topic")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.delete(),
				id=item.Id)
		
		self.PopupMenu(menu)

	def _safe_paste(self, operation=None):
		"""A wrapper around the operations manager paste operation that
		catches the CircularDataException and displays an error message.
		"""
		if operation is None:
			operation = self._operations_manager.paste
		try:
			operation()
		except CircularDataException:
			wx.MessageBox("Cannot copy the topic to one of its children.",
					"Copy Topic", wx.OK | wx.ICON_ERROR, self)
	
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
	
	def _show_passage_context_menu(self, event):
		"""Shows the context menu for a topic in the topic tree."""
		self.selected_passage = self._selected_topic.passages[event.GetIndex()]
		menu = wx.Menu()
		
		item = menu.Append(wx.ID_ANY, "&Open")
		self.Bind(wx.EVT_MENU,
				lambda e: self._passage_activated(event),
				id=item.Id)
		
		menu.AppendSeparator()
		
		item = menu.Append(wx.ID_ANY, "Cu&t")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.cut,
				id=item.Id)

		item = menu.Append(wx.ID_ANY, "&Copy")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.copy,
				id=item.Id)

		item = menu.Append(wx.ID_ANY, "&Paste")
		self.Bind(wx.EVT_MENU,
				lambda e: self._safe_paste,
				id=item.Id)

		menu.AppendSeparator()
		
		item = menu.Append(wx.ID_ANY, "&Delete")
		self.Bind(wx.EVT_MENU,
				lambda e: self._operations_manager.delete,
				id=item.Id)
		
		self.PopupMenu(menu)

	def _topic_tree_got_focus(self, event):
		self.item_selected_type = TOPIC_SELECTED
		event.Skip()

	def _passage_list_got_focus(self, event):
		self.item_selected_type = PASSAGE_SELECTED
		event.Skip()

# Specifies what type of dragging is currently happening with the topic tree.
# This is needed since it has to select and unselect topics when dragging and
# after dragging differently depending on whether a passage or a topic is
# being dragged.
DRAGGING_NONE = 0
DRAGGING_TOPIC = 1
DRAGGING_PASSAGE = 2

class TopicTree(wx.TreeCtrl):
	"""A tree control that handles dragging and dropping for topics.
	
	This contains code taken from the DragAndDrop tree mixin, but adapted to
	the topic tree (the DragAndDrop mixin doesn't work when you want to use
	the root node), and it selected the nodes it was being dragged past,
	meaning that the passage list kept changing.
	"""
	def __init__(self, topic_frame, *args, **kwargs):
		style = wx.TR_EDIT_LABELS | wx.TR_HAS_BUTTONS | wx.TR_LINES_AT_ROOT
		kwargs["style"] = style
		self._topic_frame = topic_frame
		super(TopicTree, self).__init__(*args, **kwargs)
		self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.on_begin_drag)
		self._drag_item = None
		self._dragging = DRAGGING_NONE
		self.SetDropTarget(TopicPassageDropTarget(self))

	def on_begin_drag(self, event):
		# We allow only one item to be dragged at a time, to keep it simple
		self._drag_item = event.GetItem()
		if self._drag_item and self._drag_item != self.GetRootItem():
			self.start_dragging_topic()
			event.Allow()
		else:
			event.Veto()

	def on_end_drag(self, event):
		self.stop_dragging()
		drop_target = event.GetItem()
		if not drop_target:
			drop_target = None
		if self.is_valid_drop_target(drop_target):
			self.UnselectAll()
			if drop_target is not None:
				self.SelectItem(drop_target)
			self.on_drop_topic(drop_target, self._drag_item)

	def on_motion_event(self, event):
		if not event.Dragging():
			self.stop_dragging()
			return
		self.on_dragging(event.GetX(), event.GetY())
		event.Skip()

	def on_dragging(self, x, y):
		item, flags = self.HitTest(wx.Point(x, y))
		if not item:
			item = None
		if self.is_valid_drop_target(item):
			if self._dragging == DRAGGING_TOPIC:
				self.set_cursor_to_dragging()
		else:
			self.set_cursor_to_dropping_impossible()
		if flags & wx.TREE_HITTEST_ONITEMBUTTON:
			self.Expand(item)
		if self.GetSelections() != [item]:
			self.UnselectAll()
			if item:
				self.SelectItem(item)
		
	def start_dragging_topic(self):
		self._dragging = DRAGGING_TOPIC
		self.Bind(wx.EVT_MOTION, self.on_motion_event)
		self.Bind(wx.EVT_TREE_END_DRAG, self.on_end_drag)
		self.set_cursor_to_dragging()

	def start_dragging_passage(self, x, y):
		self._dragging = DRAGGING_PASSAGE
		self._drag_item = self.GetSelection()
		self.set_cursor_to_dragging()
		self.on_dragging(x, y)

	def stop_dragging(self):
		self._dragging = DRAGGING_NONE
		self.Unbind(wx.EVT_MOTION)
		self.Unbind(wx.EVT_TREE_END_DRAG)
		self.reset_cursor()
		self.UnselectAll()
		self.SelectItem(self._drag_item)

	def set_cursor_to_dragging(self):
		self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
		
	def set_cursor_to_dropping_impossible(self):
		self.SetCursor(wx.StockCursor(wx.CURSOR_NO_ENTRY))
		
	def reset_cursor(self):
		self.SetCursor(wx.NullCursor)

	def is_valid_drop_target(self, drop_target):
		if not drop_target: 
			return False
		elif self._dragging == DRAGGING_TOPIC:
			all_children = self._get_item_children(self._drag_item, recursively=True)
			parent = self.GetItemParent(self._drag_item) 
			return drop_target not in [self._drag_item, parent] + all_children
		else:
			return True

	def on_drop_topic(self, drop_target, drag_target):
		drag_topic = self.GetPyData(drag_target)
		drop_topic = self.GetPyData(drop_target)
		if drag_topic is drop_topic:
			return
		parent = self.GetParent()
		self._topic_frame._safe_paste(
			lambda: self._topic_frame._operations_manager.do_copy(
				drag_topic, TOPIC_SELECTED,
				drop_topic, keep_original=False
			)
		)

	def on_drop_passage(self, passage_entry, x, y, drag_result):
		"""Drops the given passage onto the topic with the given x and y
		coordinates in the tree.
		The drag result specifies whether the passage should be copied or
		moved.
		"""
		self.stop_dragging()

		drop_target, flags = self.HitTest(wx.Point(x, y))
		if not drop_target:
			return

		if drag_result not in (wx.DragCopy, wx.DragMove):
			return

		self.UnselectAll()
		self.SelectItem(self._drag_item)
		drop_topic = self.GetPyData(drop_target)
		keep_original = (drag_result != wx.DragMove)
		self._topic_frame._operations_manager.do_copy(
				passage_entry, PASSAGE_SELECTED,
				drop_topic, keep_original
			)

	def _get_item_children(self, item=None, recursively=False):
		""" Return the children of item as a list. """
		if not item:
			item = self.GetRootItem()
			if not item:
				return []
		children = []
		child, cookie = self.GetFirstChild(item)
		while child:
			children.append(child)
			if recursively:
				children.extend(self._get_item_children(child, True))
			child, cookie = self.GetNextChild(item, cookie)
		return children

class PassageListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
	"""A list control for the passage list in the topic manager.

	This is included so that we can get the auto width mixin for the list
	control, meaning that the comment will be resized to take all the
	available space.
	"""
	def __init__(self, parent, topic_frame):
		wx.ListCtrl.__init__(self, parent,
			style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
		)
		ListCtrlAutoWidthMixin.__init__(self)
		self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._start_drag)
		self._drag_index = -1
		self._topic_frame = topic_frame
		self.SetDropTarget(PassageListDropTarget(self))

	def _start_drag(self, event):
		"""Starts the drag and registers a drop source for the passage."""
		self._drag_index = event.GetIndex()
		passage_entry = self._topic_frame._selected_topic.passages[self._drag_index]
		id = passage_entry.get_id()

		data = wx.CustomDataObject("PassageEntry")
		data.SetData(str(id))
		drop_source = wx.DropSource(self)
		drop_source.SetData(data)
		result = drop_source.DoDragDrop(wx.Drag_DefaultMove)

	def _handle_drop(self, x, y, drag_result):
		"""Handles moving the passage to the new location."""
		index, flags = self.HitTest(wx.Point(x, y))
		if index == wx.NOT_FOUND or index == self._drag_index:
			return

		# XXX: This does not handle copying the passage.
		self._topic_frame._operations_manager.move_current_passage(new_index=index)

class PassageListDropTarget(wx.PyDropTarget):
	"""Allows passages to be reordered in the current topic.

	XXX: This just displays an ordinary mouse cursor.  It doesn't give any
	indication whether the passage is going to be dropped above or below the
	current topic.
	"""
	def __init__(self, list_ctrl):
		wx.PyDropTarget.__init__(self)
		self._list_ctrl = list_ctrl

		self.data = wx.CustomDataObject("PassageEntry")
		self.SetDataObject(self.data)

	def OnData(self, x, y, result):
		"""Handles a drop event by passing it back to the list control."""
		if self.GetData():
			self._list_ctrl._handle_drop(x, y, result)
		return result

class TopicPassageDropTarget(wx.PyDropTarget):
	"""This drop target allows passages to be moved to different topics in
	the topic tree.
	"""
	def __init__(self, topic_tree):
		wx.PyDropTarget.__init__(self)
		self._topic_tree = topic_tree

		self.data = wx.CustomDataObject("PassageEntry")
		self.SetDataObject(self.data)

	def OnEnter(self, x, y, result):
		self._topic_tree.start_dragging_passage(x, y)
		return result

	def OnLeave(self):
		self._topic_tree.stop_dragging()

	def OnDragOver(self, x, y, result):
		self._topic_tree.on_dragging(x, y)
		return result

	def OnData(self, x, y, result):
		if self.GetData():
			passage_id = int(self.data.GetData())
			passage_entry = lookup_passage_entry(passage_id)
			self._topic_tree.on_drop_passage(passage_entry, x, y, result)
		return result

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
