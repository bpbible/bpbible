import wx
from passage_list import get_primary_passage_list_manager
from xrc.topic_creation_dialog_xrc import xrcTopicCreationDialog
from xrc.xrc_util import attach_unknown_control
from topic_selector import TopicSelector

class TopicCreationDialog(xrcTopicCreationDialog):
	"""This dialog is used to create a new passage list.

	This passage list will be added to the selected parent topic
	(an initial parent topic can be specified) when the OK button is clicked.
	If you set call_on_selection on the dialog, then it will be called with
	the new passage list when a new passage list is created.
	"""
	def __init__(self, parent, parent_topic=None):
		super(TopicCreationDialog, self).__init__(parent)
		if parent_topic is None:
			parent_topic = get_primary_passage_list_manager()
		self._setup_topic_selector(parent_topic)
		self.name_text.SetFocus()
		self.call_on_selection = None
		self.Bind(wx.EVT_BUTTON, self._on_ok_button_clicked, self.wxID_OK)

	def _setup_topic_selector(self, parent_topic):
		attach_unknown_control("topic_selector", TopicSelector, self)
		self.topic_selector.selected_topic = parent_topic

	def _on_ok_button_clicked(self, event):
		parent_topic = self.topic_selector.selected_topic
		if parent_topic is None:
			return

		new_passage_list = parent_topic.add_empty_subtopic(
				self.name_text.GetValue(),
				self.description_text.GetValue())
		if self.call_on_selection is not None:
			self.call_on_selection(new_passage_list)
		event.Skip()
