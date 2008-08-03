import wx
import guiconfig
from protocols import protocol_handler
from manage_topics_frame import ManageTopicsFrame
from topic_selector import TopicSelector
from passage_list import lookup_passage_list
from tooltip import TooltipConfig

TAG_COLOUR = (255, 0, 0)

def on_passage_tag_hover(frame, href, url, x, y):
	passage_list = _get_passage_list_from_href(href)

	frame.tooltip.tooltip_config = TopicTooltipConfig(passage_list)
	frame.tooltip.Start()

def _get_passage_list_from_href(href):
	"""Gets the passage list corresponding to the given passage tag HREF."""
	href_parts = href.split(":")
	assert len(href_parts) == 2
	assert href_parts[0] == "passage_tag"
	passage_list_id = int(href_parts[1])
	return lookup_passage_list(passage_list_id)

class TopicTooltipConfig(TooltipConfig):
	def __init__(self, topic):
		super(TopicTooltipConfig, self).__init__()
		self.topic = topic

	def get_title(self):
		return self.topic.full_name

	def add_to_toolbar(self, toolbar):
		self.topic_selector = TopicSelector(toolbar)
		toolbar.AddControl(self.topic_selector)
		self.topic_selector.selected_topic = self.topic
		self.topic_selector.topic_changed_observers += self._change_selected_topic

	def _change_selected_topic(self, new_topic):
		self.topic = new_topic
		self.tooltip_changed()

	def get_text(self):
		html = ""
		description = self.topic.description.replace("\n", "<br>")
		if description:
			html = "<p>%s</p>" % description

		passage_html = "<br>".join(self._passage_entry_text(passage_entry)
				for passage_entry in self.topic.passages)
		if passage_html:
			html += "<p>%s</p>" % passage_html
	
		return html

	def _passage_entry_text(self, passage_entry):
		"""Gets the HTML for the given passage entry with its comment."""
		comment = passage_entry.comment.replace("\n", "<br>")
		reference = str(passage_entry)
		return "<b><a href=\"bible:%(reference)s\">%(reference)s</a></b> " \
			"%(comment)s" % locals()

protocol_handler.register_hover("passage_tag", on_passage_tag_hover)

class PassageTag(wx.PyWindow):
	border = 2

	def __init__(self, parent, passage_list, passage_entry, *args, **kwargs):
		"""Creates a new passage tag window with the given parent.

		This is intended to be embedded in the bible display frame for verses
		which contain the given passage entry and are part of the given
		passage list.
		passage_list: The passage list that the tag is for.
		passage_entry: The passage entry that the tag is for.
		"""
		self._passage_list = passage_list
		self._tag_text = " > ".join(passage_list.topic_trail)
		self._passage_entry = passage_entry
		super(PassageTag, self).__init__(parent, *args, **kwargs)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
		# callafter as under MSW, enter seems to come before leave in
		# places.  This is taken from the header bar in subversion.
		self.Bind(wx.EVT_ENTER_WINDOW, 
			lambda evt:wx.CallAfter(self.on_enter, evt.X, evt.Y))
		self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
		self.Bind(wx.EVT_SET_FOCUS, self.on_focus)
		self._create_bitmap()
		self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

	def on_focus(self, event):
		"""Forces the focus to go to the parent HTML window.

		This is necessary to make the keyboard shortcuts (s, g, ...) work.
		"""
		self.Parent.SetFocusIgnoringChildren()

	def _create_bitmap(self):
		dc = wx.MemoryDC()
		dc.SetFont(self.Font)

		text_width, text_height = dc.GetTextExtent(self._tag_text)

		width = text_width + self.border * 2
		height = text_height + self.border * 2
		
		bmp = wx.EmptyBitmap(width, height)
		dc.SelectObject(bmp)

		dc.Clear()

		# set up the dc
		dc.Background = wx.WHITE_BRUSH
		dc.Pen = wx.BLACK_PEN
		dc.Brush = wx.Brush(TAG_COLOUR)

		dc.DrawRoundedRectangle(0, 0, width, height, 5)
		dc.DrawText(self._tag_text, self.border, self.border)
		
		# assign the resultant bitmap
		del dc
		self.bmp = bmp
		
		self.SetSize((width, height))

	def on_paint(self, event):
		wx.BufferedPaintDC(self, self.bmp)

	def on_left_button_up(self, event):
		frame = ManageTopicsFrame(self)
		frame.select_topic_and_passage(self._passage_list, self._passage_entry)
		frame.Show()
		event.Skip()

	def on_enter(self, x, y):
		self.Parent.current_target = self
		if self.Parent.tooltip.target == self:
			return

		protocol_handler.on_hover(self.Parent, 
			"passage_tag:%d" % self._passage_list.get_id(), x, y)

	def on_leave(self, event):
		self.Parent.current_target = None

		self.Parent.tooltip.MouseOut(None)
