import wx
from passage_list import get_primary_passage_list_manager, \
		PassageEntry, PassageList
import passage_list.settings
from swlib.pysw import VerseList
from xrc.tag_passage_dialog_xrc import xrcTagPassageDialog
from xrc.xrc_util import attach_unknown_control
from topic_selector import TopicSelector
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
		self.passage_verse_key = VerseList([self._passage_entry.passage])
		passage_str = self.passage_verse_key.GetBestRange(userOutput=True)
		self.passage_text.Value = passage_str
		self.Title = _("Tag %s") % passage_str
		self.Size = (355, 282)

	def _bindEvents(self):
		self.Bind(wx.EVT_BUTTON, self._on_ok_button_clicked, self.wxID_OK)
		self.topic_selector.return_pressed_observers += self.comment_text.SetFocus
	
	def _on_ok_button_clicked(self, event):
		if self._topic_is_selected() and self._is_valid_passage():
			event.Skip()

	def _topic_is_selected(self):
		return self.topic_selector.selected_topic is not None

	def _is_valid_passage(self):
		passage_text = self.passage_text.Value
		passages = VerseList(passage_text, userInput=True)
		if len(passages) >= 1:
			self._passage_entry.passage = passages
			return True
		else:
			wx.MessageBox(_(u"Unrecognised passage `%s'.") % passage_text,
					"", wx.OK | wx.ICON_INFORMATION, self)
			return False

def tag_passage(parent, passage):
	"""Allows the user to tag the given passage.

	This shows the passage tagging dialog (modally), and allows the user to
	act on it.

	If the topic that the user enters does not exist, then a new topic will
	be created.
	"""
	passage_entry = PassageEntry(passage)
	dialog = TagPassageDialog(parent, passage_entry)
	if dialog.ShowModal() == wx.ID_OK:
		passage_entry.comment = dialog.comment_text.GetValue()
		dialog.topic_selector.maybe_create_topic_from_text()
		topic = dialog.topic_selector.selected_topic
		topic.add_passage(passage_entry)
		passage_list.settings.last_selected_topic = topic
		get_primary_passage_list_manager().save()
		guiconfig.mainfrm.UpdateBibleUIWithoutScrolling(
				source=events.PASSAGE_TAGGED)
	dialog.Destroy()
