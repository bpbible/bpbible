import wx
import guiconfig
from xrc.topic_dialog_xrc import xrcTopicDialog
from xrc.xrc_util import attach_unknown_control
from topic_selector import TopicSelector
from events import TOPIC_LIST

class TopicDialog(xrcTopicDialog):
	"""This dialog is used to view and edit a passage list.
	
	It is displayed when a tag is clicked on.
	"""
	def __init__(self, parent, passage_list):
		"""Creates the dialog.

		parent: The parent window.
		passage_list: The passage list to display.
		"""
		super(TopicDialog, self).__init__(parent)

		self._setup_topic_selector(passage_list)
		self._init_passage_list_ctrl_headers()
		self._bind_events()
		self.set_passage_list(passage_list)
		self.passage_list_ctrl.SetFocus()

	def set_passage_list(self, passage_list):
		"""Sets the passage list for the dialog to the given passage list."""
		self._passage_list = passage_list
		self._setup_passage_list_ctrl()
		self.Title = self._passage_list.full_name
		self.description_text.ChangeValue(passage_list.description)

	def select_passage_entry(self, passage_entry):
		"""Selects the given passage entry as the currently selected passage.

		This requires the passage entry to be part of the passage list that
		is being viewed.
		"""
		assert passage_entry in self._passage_list.passages
		index = self._passage_list.passages.index(passage_entry)
		self._select_list_entry_by_index(index)
	
	def _bind_events(self):
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self._passage_item_selected)
		self.passage_list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._passage_item_activated)
		self.topic_selector.topic_changed_observers += self._topic_changed

	def _setup_topic_selector(self, passage_list):
		attach_unknown_control("topic_selector", TopicSelector, self)
		self.topic_selector.selected_topic = passage_list
	
	def _init_passage_list_ctrl_headers(self):
		self.passage_list_ctrl.InsertColumn(0, "Passage")
		self.passage_list_ctrl.InsertColumn(1, "Comment")

	def _setup_passage_list_ctrl(self):
		self.passage_list_ctrl.DeleteAllItems()
		for index, passage_entry in enumerate(self._passage_list.passages):
			self.passage_list_ctrl.InsertStringItem(index, str(passage_entry))
			self.passage_list_ctrl.SetStringItem(index, 1, passage_entry.comment)

		#self.passage_list_ctrl.SetColumnWidth(0, wx.LIST_AUTOSIZE)
		#self.passage_list_ctrl.SetColumnWidth(1, wx.LIST_AUTOSIZE)
		if self._passage_list.passages:
			self._select_list_entry_by_index(0)
		else:
			self.passage_preview.SetPage("")

	def _select_list_entry_by_index(self, index):
		"""Selects the entry in the list control with the given index."""
		assert 0 <= index < len(self._passage_list.passages), \
				"The index that is being selected is out of range."
		state = wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED
		self.passage_list_ctrl.SetItemState(index, state, state)

	def _passage_item_selected(self, event):
		passage_entry = self._passage_list.passages[event.GetIndex()]
		self.passage_preview.SetReference(
				str(passage_entry), exclude_topic_tag=self._passage_list,
			)

	def _passage_item_activated(self, event):
		passage_entry = self._passage_list.passages[event.GetIndex()]
		guiconfig.mainfrm.set_bible_ref(str(passage_entry), source=TOPIC_LIST)

	def _topic_changed(self, new_topic):
		if self:
			self.set_passage_list(new_topic)
