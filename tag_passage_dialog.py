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
	def __init__(self, parent, passage_entry, show_topic, title, is_new_passage):
		super(TagPassageDialog, self).__init__(parent)
		self._show_topic = show_topic
		self.is_new_passage = is_new_passage
		attach_unknown_control("topic_selector", TopicSelector, self)
		if show_topic:
			self.topic_selector.selected_topic = passage_list.settings.last_selected_topic
			wx.CallAfter(self.topic_selector.SetFocus)
		else:
			flex_sizer = self.Sizer.Children[0].Sizer
			flex_sizer.Show(2, False)
			flex_sizer.Show(3, False)
			flex_sizer.Layout()
			self.comment_text.SetFocus()
		self._passage_entry = passage_entry
		self._manager = get_primary_passage_list_manager()
		self._bindEvents()
		self.passage_verse_key = VerseList([self._passage_entry.passage])
		passage_str = self.passage_verse_key.GetBestRange(userOutput=True)
		self.passage_text.Value = passage_str
		self.comment_text.Value = self._passage_entry.comment
		if title is None:
			title = _("Tag %s")
		self.Title = title % passage_str
		self.Size = (355, 282)

	def _bindEvents(self):
		self.Bind(wx.EVT_BUTTON, self._on_ok_button_clicked, self.wxID_OK)
		self.topic_selector.return_pressed_observers += self.comment_text.SetFocus
	
	def _on_ok_button_clicked(self, event):
		if self._topic_is_selected() and self._is_valid_passage():
			event.Skip()

	def _topic_is_selected(self):
		return (not self._show_topic or self.topic_selector.selected_topic is not None)

	def _is_valid_passage(self):
		passage_text = self.passage_text.Value
		passages = VerseList(passage_text, userInput=True)
		if len(passages) >= 1:
			self._passage_entry.set_passage(passages,
			new_passage=self.is_new_passage)
			return True
		else:
			wx.MessageBox(_(u"Unrecognised passage `%s'.") % passage_text,
					"", wx.OK | wx.ICON_INFORMATION, self)
			return False

def tag_passage(parent, passage, topic_to_apply=None, title=None):
	"""Allows the user to tag the given passage.

	This shows the passage tagging dialog (modally), and allows the user to
	act on it.

	If the topic that the user enters does not exist, then a new topic will
	be created.
	"""
	editing_comment = isinstance(passage, PassageEntry)
	if editing_comment:
		passage_entry = passage
	else:
		passage_entry = PassageEntry(passage)
	dialog = TagPassageDialog(
		parent,
		passage_entry,
		show_topic=(topic_to_apply is None),
		title=title,
		is_new_passage=not editing_comment,
	)
	if dialog.ShowModal() == wx.ID_OK:
		passage_entry.comment = dialog.comment_text.GetValue()
		if topic_to_apply is None:
			dialog.topic_selector.maybe_create_topic_from_text()
			topic = dialog.topic_selector.selected_topic
			passage_list.settings.last_selected_topic = topic
		else:
			topic = topic_to_apply

		if not editing_comment:
			topic.add_passage(passage_entry)

		get_primary_passage_list_manager().save()

		if not editing_comment:
			guiconfig.mainfrm.UpdateBibleUIWithoutScrolling(
					source=events.PASSAGE_TAGGED)
	dialog.Destroy()


def comment_on_passage(parent, passage):
	tag_passage(
		parent,
		passage,
		get_primary_passage_list_manager().comments_special_topic,
		title=_("Comment on %s"),
	)

def edit_comment(parent, passage_entry):
	tag_passage(
		parent,
		passage_entry,
		get_primary_passage_list_manager().comments_special_topic,
		title=_("Comment on %s"),
	)
