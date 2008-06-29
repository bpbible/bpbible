import wx
from passage_list import get_primary_passage_list_manager, \
		PassageEntry, PassageList
import passage_list.settings
from xrc.tag_passage_dialog_xrc import xrcTagPassageDialog
from xrc.xrc_util import attach_unknown_control
from topic_selector import TopicSelector
from topic_creation_dialog import TopicCreationDialog
import guiconfig
import events

class TagPassageDialog(xrcTagPassageDialog):
	def __init__(self, parent, passage_entry):
		super(TagPassageDialog, self).__init__(parent)
		self._passage_entry = passage_entry
		self._manager = get_primary_passage_list_manager()
		attach_unknown_control("topic_selector", TopicSelector, self)
		self.topic_selector.selected_topic = passage_list.settings.last_selected_topic
		self.topic_selector.SetFocus()
		self._bindEvents()
		self.Title = "Tag %s" % self._passage_entry

	def _bindEvents(self):
		self.Bind(wx.EVT_BUTTON, self._on_ok_button_clicked, self.wxID_OK)
		self.Bind(wx.EVT_BUTTON, self._on_new_tag_clicked, self.new_tag_button)
	
	def _on_ok_button_clicked(self, event):
		if self._topic_is_selected():
			event.Skip()

	def _on_new_tag_clicked(self, event):
		dialog = TopicCreationDialog(self)
		dialog.call_on_selection = self._on_new_tag_created
		dialog.Show()

	def _on_new_tag_created(self, passage_list):
		self.topic_selector.selected_topic = passage_list

	def _topic_is_selected(self):
		return self.topic_selector.selected_topic is not None

def tag_passage(parent, passage):
	"""Allows the user to tag the given passage.

	This shows the passage tagging dialog (modally), and allows the user to
	act on it.
	"""
	passage_entry = PassageEntry(passage)
	dialog = TagPassageDialog(parent, passage_entry)
	if dialog.ShowModal() == wx.ID_OK:
		passage_entry.comment = dialog.comment_text.GetValue()
		topic = dialog.topic_selector.selected_topic
		topic.add_passage(passage_entry)
		passage_list.settings.last_selected_topic = topic
		get_primary_passage_list_manager().save()
		guiconfig.mainfrm.UpdateBibleUIWithoutScrolling(
				source=events.PASSAGE_TAGGED)
	dialog.Destroy()
