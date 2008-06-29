"""\
The selector that is used to select a topic from a list of topics.
"""
import wx
import  wx.lib.mixins.listctrl  as  listmix
from passage_list import get_primary_passage_list_manager
from util.observerlist import ObserverList

class TopicListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class TopicSelector(wx.TextCtrl):
	"""This control is used to select a topic.

	It uses a filterable drop down list to suggest topics, somewhat similar
	to the Firefox URL suggestion list.
	"""
	def __init__(self, parent):
		super(TopicSelector, self).__init__(parent, style=wx.TE_PROCESS_ENTER)
		self._manager = get_primary_passage_list_manager()
		self._dropdown = wx.PopupWindow(self)
		self._setup_list()
		self._selected_topic = None
		self.topic_changed_observers = ObserverList() 
		self._bind_events()
		self.selected_topic = self._manager

	def get_selected_topic(self):
		return self._selected_topic

	def set_selected_topic(self, topic):
		self._selected_topic = topic
		self._update_topic_text()
		self.topic_changed_observers(topic)

	selected_topic = property(get_selected_topic, set_selected_topic,
			doc="The currently selected topic for the control.")

	def _bind_events(self):
		self.Bind(wx.EVT_TEXT, self._on_text_changed)
		self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
		self.Bind(wx.EVT_SET_FOCUS, self._on_focus_got)
		self.Bind(wx.EVT_KILL_FOCUS, self._on_focus_lost)

	def _setup_list(self):
		self._topic_list = TopicListCtrl(self._dropdown,
				pos=(0, 0),
				style=wx.LC_REPORT | wx.LC_NO_HEADER | wx.LC_SINGLE_SEL)
		self._topic_list.Bind(wx.EVT_LEFT_DOWN, self._on_list_clicked)

	def _setup_dropdown_data(self):
		filter = self.GetValue()
		if filter:
			# XXX: Handle individual words.
			filtered_topics = [(name, index) for index, (name, _) in enumerate(self._topics) if filter.lower() in name.lower()]
		else:
			filtered_topics = [(name, index) for index, (name, _) in enumerate(self._topics)]

		if not filtered_topics:
			return False

		longest_topic = max(len(name) for name, _ in filtered_topics)

		width = self.GetSize()[0]

		width = max(self._topic_list.GetCharWidth() * (longest_topic + 10), width)
		height = self._topic_list.GetCharHeight() * (min(len(filtered_topics), 7) + 2)

		size = (width, height)
		self._topic_list.SetSize(size)
		self._dropdown.SetClientSize(size)
		self._topic_list.DeleteAllColumns()
		self._topic_list.DeleteAllItems()
		self._topic_list.InsertColumn(0, "")
		for index, (name, index2) in enumerate(filtered_topics):
			self._topic_list.InsertStringItem(index, name)
			self._topic_list.SetItemData(index, index2)

		self._topic_list._doResize()
		return True

	def _update_topics(self):
		"""Updates the list of topics used in the dropdown.

		XXX: This list is rebuilt far too frequently.  We should be more
		clever about rebuilding it.
		"""
		self._topics = []
		self._get_topics(self._manager)

	def _get_topics(self, topic):
		self._topics.append((topic.full_name, topic))
		for subtopic in topic.subtopics:
			self._get_topics(subtopic)

	def _update_topic_text(self):
		if self._selected_topic is None:
			self.ChangeValue("None")
		else:
			self.ChangeValue(self._selected_topic.full_name)

	def _on_text_changed(self, event):
		self._show_dropdown()

	def _on_key_down(self, event):
		keycode = event.GetKeyCode()
		selection = self._topic_list.GetFirstSelected()

		skip = True

		if not self._dropdown.IsShown():
			event.Skip()
			return

		keycode = event.GetKeyCode()
		if keycode == wx.WXK_DOWN:
			if selection + 1 < self._topic_list.GetItemCount():
				self._topic_list.Select(selection + 1)
				self._topic_list.EnsureVisible(selection + 1)
		elif keycode == wx.WXK_UP:
			if selection > 0 :
				self._topic_list.Select(selection - 1)
				self._topic_list.EnsureVisible(selection - 1)

		elif keycode == wx.WXK_RETURN:
			self._hide_dropdown()
			self._select_currently_selected()

		elif keycode == wx.WXK_ESCAPE:
			self._hide_dropdown()
			self._update_topic_text()
		else:
			event.Skip()

	def _on_list_clicked(self, event):
		selection, flag = self._topic_list.HitTest(event.GetPosition())
		if selection == -1:
			return

		self._topic_list.Select(selection)
		self._select_currently_selected()
		self._hide_dropdown()

	def _select_currently_selected(self):
		selection = self._topic_list.GetFirstSelected()
		if selection == -1:
			if self._topic_list.GetItemCount() == 1:
				selection = 0
			else:
				return

		topic_index = self._topic_list.GetItemData(selection)
		if topic_index == -1:
			# Create new topic.
			return
			
		self.selected_topic = self._topics[topic_index][1]

	def _on_focus_got(self, event):
		self.SetSelection(-1, -1)

	def _on_focus_lost(self, event):
		self._hide_dropdown()

	def _show_dropdown(self):
		if not self._dropdown.IsShown():
			self._update_topics()

		if not self._setup_dropdown_data():
			self._hide_dropdown()
			return

		position = self.ClientToScreen((0, 0))
		width, height = self.GetSize()
		self._dropdown.Position(position, (0, height))
		self._dropdown.Show()

	def _hide_dropdown(self):
		self._dropdown.Hide()
