import wx
import guiconfig
import guiutil
from protocols import protocol_handler
from manage_topics_frame import ManageTopicsFrame
from topic_selector import TopicSelector
import passage_list
from passage_list import lookup_passage_list, lookup_passage_entry
from swlib.pysw import VerseList
from tooltip import TooltipConfig
from backend.bibleinterface import biblemgr
from util.string_util import text2html
from util.observerlist import ObserverList

# colour schemes - the top ones here are the original ones, and aren't really
# used any more.
_rgbSelectOuter = wx.Colour(170, 200, 245)
_rgbSelectInner = wx.Colour(230, 250, 250)
_rgbSelectTop = wx.Colour(210, 240, 250)
_rgbSelectBottom = wx.Colour(185, 215, 250)
_rgbNoFocusTop = wx.Colour(250, 250, 250)
_rgbNoFocusBottom = wx.Colour(235, 235, 235)
_rgbNoFocusOuter = wx.Colour(220, 220, 220)
_rgbNoFocusInner = wx.Colour(245, 245, 245)

import colorsys
def r(c):
	return ["%.8f" % x for x in colorsys.rgb_to_hsv(*[x / 255. for x in [c.Red(), c.Green(), c.Blue()]])]

# our mixing parameters - takes a hue, returns hsv
original = lambda b: [
	[b + 0.1,		.30612245,	245/255.],
	[b,				.08,		250/255.],
	[b + 1/24.,		.16,		250/255.],
	[b + .08974,	.26,		250/255.],
]

unsaturated = lambda b: [
	[b + 0.1,		.6, 	245/255.],
	[b,				.16,	250/255.],
	[b + 1/24.,		.32,	250/255.],
	[b + .08974,	.52,	250/255.],
]

d_unsaturated = lambda b: [
	[b + 0.1,		.12, 	245/255.],
	[b,				.32,	250/255.],
	[b,		.64,	250/255.],
	[b + .1,	.99,	250/255.],
]

flat = lambda b: [
	[b + 0.05,	.99,	250/255.],
	[b + 0.05,	.99,	250/255.],
	[b + 0.05,	.99,	250/255.],
	[b + 0.05,	.99,	250/255.],
]

def get_colours(b, scheme=original):
	# original, b=0.5
	return convert(scheme(b))

# (Colour transform, use white text, default look to use with this colour)
colours = [
	(0.5, 0, 0),
	(0.6, 1, 1),
	(0.7, 1, 1),
	(0.8, 1, 0),
	(0.9, 1, 0),
	(0.0, 1, 1),
	(0.1, 0, 1),
	(0.2, 0, 1),
	(0.3, 0, 1),
	(0.4, 0, 1),
]

# our list of looks
looks = [
	(original, False, 2),
	(unsaturated, False, 2),
	(d_unsaturated, True, 4),
	(flat, True, 2),
]

def convert(l):
	return [wx.Colour(
		*[c * 255 for c in colorsys.hsv_to_rgb(*[i % 1 for i in x])])
		for x in l
	]

def use_colours(hue, look):
	global _rgbSelectOuter,_rgbSelectInner,_rgbSelectTop, _rgbSelectBottom
	_rgbSelectOuter,_rgbSelectInner,_rgbSelectTop, _rgbSelectBottom = get_colours(hue, look)

	#print r(_rgbSelectOuter)
	#print r(_rgbSelectInner)
	#print r(_rgbSelectTop)
	#print r(_rgbSelectBottom)

# testing
upto = 0.5
def generate_new_colour():
	print "Here"
	global upto
	upto += 0.001
	upto %= 1
	if upto % 0.001 < 0.00001:
		use_colours(upto, original)
		print "UPTO", upto

def on_passage_tag_hover(frame, href, url, x, y):
	passage_list, passage_entry = _get_passage_list_and_entry_from_href(href)

	frame.show_tooltip(TopicTooltipConfig(passage_list, passage_entry))

def on_passage_tag_clicked(frame, href, url):
	passage_list, passage_entry = _get_passage_list_and_entry_from_href(href)
	guiconfig.mainfrm.hide_tooltips()
	frame = ManageTopicsFrame(guiconfig.mainfrm)
	frame.select_topic_and_passage(passage_list, passage_entry)
	frame.Show()

def _get_passage_list_and_entry_from_href(href):
	"""Gets the passage list corresponding to the given passage tag HREF."""
	from gui.webconnect_protocol_handler import get_url_host_and_page
	url_host, page = get_url_host_and_page(href)
	assert url_host == "passage"
	page_parts = page.split("/")
	assert len(page_parts) == 2
	passage_list_id = int(page_parts[0])
	passage_entry_id = int(page_parts[1])
	return (lookup_passage_list(passage_list_id),
			lookup_passage_entry(passage_entry_id))

class TopicTooltipConfig(TooltipConfig):
	def __init__(self, topic, selected_passage_entry):
		super(TopicTooltipConfig, self).__init__(book=biblemgr.bible)
		self.topic = topic
		self.selected_passage_entry = selected_passage_entry
		self.scroll_to_current = True
		self.expand_passages = passage_list.settings.expand_topic_passages
		self.text_needs_reloading = True
		self.text = u""

	def get_title(self):
		try:
			return self.topic.full_name
		except AttributeError:
			# The topic has been deleted.
			return u""

	def add_to_toolbar(self, toolbar, permanent):
		if not permanent: return
		self.topic_selector = TopicSelector(toolbar)
		toolbar.AddControl(self.topic_selector)
		self.topic_selector.selected_topic = self.topic
		self.topic_selector.topic_changed_observers += self._change_selected_topic

		self.gui_expand_passages = toolbar.AddLabelTool(wx.ID_ANY,  
			_("Expand"),
			guiutil.bmp("book_open.png"),
			shortHelp=_("Expand all of the passages in this topic"), kind=wx.ITEM_CHECK)
		toolbar.ToggleTool(self.gui_expand_passages.Id, self.expand_passages)

		toolbar.Bind(wx.EVT_TOOL, self.toggle_expand_passages,
			id=self.gui_expand_passages.Id)

	def _change_selected_topic(self, new_topic):
		self.topic = new_topic
		self.tooltip_changed()

	def toggle_expand_passages(self, event):
		self.expand_passages = not self.expand_passages
		self.text_needs_reloading = True
		self.tooltip_changed()

	def get_text(self):
		if not self.text_needs_reloading:
			return self.text

		try:
			html = u"<p><b>%s</b></p>" % text2html(self.topic.full_name)
		except AttributeError:
			# The topic has been deleted.
			return u""
		description = text2html(self.topic.description)
		if description:
			html += u"<p>%s</p>" % description

		passage_html = u"<br>".join(self._passage_entry_text(passage_entry)
				for passage_entry in self.topic.passages)
		if passage_html:
			html += u"<p>%s</p>" % passage_html
	
		self.text = html
		self.text_needs_reloading = False

		return html

	def _passage_entry_text(self, passage_entry):
		"""Gets the HTML for the given passage entry with its comment."""
		comment = text2html(passage_entry.comment)
		if self.expand_passages:
			comment = u"<i>%s</i>" % comment
		reference = str(passage_entry)
		localised_reference = text2html(passage_entry.passage.GetBestRange(userOutput=True))
		if self.expand_passages:
			passage_text = u"<br>" + biblemgr.bible.GetReference(
				reference, exclude_topic_tag=self.topic, remove_extra_whitespace=True)
			if comment:
				comment = u"<p>%s<p>" % comment
		else:
			passage_text = ""

		current_anchor = u""
		if passage_entry is self.selected_passage_entry:
			comment = u'<span style="color: #008000">%s</span>' % comment
			passage_text = u'<span style="color: #008000">%s</span>' % passage_text
			current_anchor = u'<a name="current" />'
		return (u"%(current_anchor)s<b><a href=\"bible:%(reference)s\">%(localised_reference)s</a></b> "
			u"%(passage_text)s%(comment)s" % locals())

protocol_handler.register_handler("passagetag", on_passage_tag_clicked)
protocol_handler.register_hover("passagetag", on_passage_tag_hover)

class PassageTagLook(wx.PyWindow):
	def __init__(self, parent, tag_text, look=0, colour=0, *args, **kwargs):
		self.tag_text = tag_text
		super(PassageTagLook, self).__init__(parent, *args, **kwargs)
		self.set_scheme(look, colour)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))

	def set_scheme(self, look, colour):
		self.look, self.colour = look, colour
		self.look_scheme, self.white_text, self.border = looks[look]
		self.colour_id, white_text, default_look = colours[colour]
		self.white_text = self.white_text and white_text
		use_colours(self.colour_id, self.look_scheme)
		self._create_bitmap()
		self.Refresh()
	
	def on_paint(self, event):
		wx.BufferedPaintDC(self, self.bmp)

	def _create_bitmap(self):
		dc = wx.MemoryDC()
		dc.SetFont(self.Font)
		dc.SelectObject(wx.EmptyBitmap(1, 1))

		text_width, text_height = dc.GetTextExtent(self.tag_text)

		width = text_width + self.border * 2
		height = text_height + self.border * 2
		
		bmp = wx.EmptyBitmap(width, height)
		dc.SelectObject(bmp)

		dc.Clear()

		# set up the dc
		#dc.Background = wx.WHITE_BRUSH
		#dc.Pen = wx.BLACK_PEN
		#dc.Brush = wx.Brush(TAG_COLOUR)

		#dc.DrawRoundedRectangle(0, 0, width, height, 5)
		self.DrawVistaRectangle(dc, wx.Rect(0, 0, width, height), True)
		if self.white_text: dc.SetTextForeground(wx.WHITE)
		dc.DrawText(self.tag_text, self.border, self.border)
		
		# assign the resultant bitmap
		del dc
		self.bmp = bmp
		
		self.SetSize((width, height))
		self.SetMinSize((width, height))

	# taken from wx.lib.customtreectrl
	def DrawVistaRectangle(self, dc, rect, hasfocus):
		"""Draw the selected item(s) with the Windows Vista style."""

		if hasfocus:
			
			outer = _rgbSelectOuter
			inner = _rgbSelectInner
			top = _rgbSelectTop
			bottom = _rgbSelectBottom

		else:
			
			outer = _rgbNoFocusOuter
			inner = _rgbNoFocusInner
			top = _rgbNoFocusTop
			bottom = _rgbNoFocusBottom

		oldpen = dc.GetPen()
		oldbrush = dc.GetBrush()

		bdrRect = wx.Rect(*rect.Get())
		filRect = wx.Rect(*rect.Get())
		filRect.Deflate(1,1)
		
		r1, g1, b1 = int(top.Red()), int(top.Green()), int(top.Blue())
		r2, g2, b2 = int(bottom.Red()), int(bottom.Green()), int(bottom.Blue())

		flrect = float(filRect.height)
		if flrect < 1:
			flrect = self._lineHeight

		rstep = float((r2 - r1)) / flrect
		gstep = float((g2 - g1)) / flrect
		bstep = float((b2 - b1)) / flrect

		rf, gf, bf = 0, 0, 0
		dc.SetPen(wx.TRANSPARENT_PEN)
		
		for y in xrange(filRect.y, filRect.y + filRect.height):
			currCol = (r1 + rf, g1 + gf, b1 + bf)
			dc.SetBrush(wx.Brush(currCol, wx.SOLID))
			dc.DrawRectangle(filRect.x, y, filRect.width, 1)
			rf = rf + rstep
			gf = gf + gstep
			bf = bf + bstep
		
		dc.SetBrush(wx.TRANSPARENT_BRUSH)
		dc.SetPen(wx.Pen(outer))
		dc.DrawRoundedRectangleRect(bdrRect, self.border + 1)
		bdrRect.Deflate(1, 1)
		dc.SetPen(wx.Pen(inner))
		dc.DrawRoundedRectangleRect(bdrRect, self.border)

		dc.SetPen(oldpen)
		dc.SetBrush(oldbrush)
	
class PassageTag(PassageTagLook):
	def __init__(self, parent, passage_list, passage_entry, *args, **kwargs):
		"""Creates a new passage tag window with the given parent.

		This is intended to be embedded in the bible display frame for verses
		which contain the given passage entry and are part of the given
		passage list.
		passage_list: The passage list that the tag is for.
		passage_entry: The passage entry that the tag is for.
		"""
		self._passage_list = passage_list
		self._passage_entry = passage_entry
		look, colour = passage_list.resolve_tag_look()
		super(PassageTag, self).__init__(parent, " > ".join(passage_list.topic_trail), look, colour, *args, **kwargs)
		self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
		# callafter as under MSW, enter seems to come before leave in
		# places.  This is taken from the header bar in subversion.
		self.Bind(wx.EVT_ENTER_WINDOW, 
			lambda evt:wx.CallAfter(self.on_enter, evt.X, evt.Y))
		self.Bind(wx.EVT_LEAVE_WINDOW, self.on_leave)
		self.Bind(wx.EVT_SET_FOCUS, self.on_focus)

	def on_focus(self, event):
		"""Forces the focus to go to the parent HTML window.

		This is necessary to make the keyboard shortcuts (s, g, ...) work.
		"""
		self.Parent.SetFocusIgnoringChildren()

	def on_left_button_up(self, event):
		guiconfig.mainfrm.hide_tooltips()
		frame = ManageTopicsFrame(guiconfig.mainfrm)
		frame.select_topic_and_passage(self._passage_list, self._passage_entry)
		frame.Show()
		event.Skip()

	def on_enter(self, x, y):
		self.Parent.current_target = self, self.ScreenRect, 5
		if self.Parent.tooltip.target == self:
			return

		href = "passage_tag:%d:%d" % (self._passage_list.get_id(), self._passage_entry.get_id())
		protocol_handler.on_hover(self.Parent, href, x, y)

	def on_leave(self, event):
		self.Parent.current_target = None

		self.Parent.tooltip.MouseOut(None)

class Border(wx.Panel):
	DEFAULT_BORDER_WIDTH = 5
	def __init__(self, parent, border_width=DEFAULT_BORDER_WIDTH, rounded_rectangle_radius=5):
		super(Border, self).__init__(parent)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.Sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.border = False
		self.border_width = border_width
		self.rounded_rectangle_radius = rounded_rectangle_radius

	def on_paint(self, event):
		dc = wx.PaintDC(self)
		if self.border:
			dc.Pen = wx.Pen(wx.SystemSettings_GetColour(wx.SYS_COLOUR_GRAYTEXT))
			top = left = self.border_width - self.w - 3
			width = self.Size[0] - 2 * left
			height = self.Size[1] - 2 * top
			dc.DrawRoundedRectangle(top, left, width, height, self.rounded_rectangle_radius)
	
	def set_child(self, child):
		self.Sizer.Add(child, 0, wx.ALL)
		self.update_width(child.border)
	
	def update_width(self, w):
		self.w = w - 2
		self.Sizer.Children[0].Border = self.border_width - self.w

class ColourRect(wx.PyWindow):
	def __init__(self, parent, colour=0, *args, **kwargs):
		super(ColourRect, self).__init__(parent, *args, **kwargs)
		self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
		self.look = looks[3]
		self.border = self.look[1]
		self.colour = colour
		_rgbSelectOuter, _rgbSelectInner, _rgbSelectTop, _rgbSelectBottom = get_colours(colours[self.colour][0], self.look[0])
		self.BackgroundColour = _rgbSelectInner
		self.Size = (12, 12)

class LookPicker(wx.PopupTransientWindow):
	COLUMNS = 5
	def __init__(self, parent, text, position, 
		look=0, colour=0, parent_look=0, parent_colour=0, using_parent=True):
		super(LookPicker, self).__init__(parent, style=wx.NO_BORDER)
		self.look = look
		self.colour = colour
		self.parent_look = parent_look
		self.parent_colour = parent_colour
		self.using_parent_look = using_parent

		panel = wx.Panel(self, style=wx.RAISED_BORDER)
		main_sizer = wx.FlexGridSizer(6, 1, 3, 6)
		use_parent_look_label = wx.StaticText(panel, label=_("Use Parent Look:"))
		colour_label = wx.StaticText(panel, label=_("Colour:"))
		look_label = wx.StaticText(panel, label=_("Appearance:"))
		label_font = use_parent_look_label.Font
		label_font.Weight = wx.FONTWEIGHT_BOLD
		colour_label.Font = look_label.Font = use_parent_look_label.Font = label_font
		
		# Use parent look.
		use_parent_look_tag_border = Border(panel)
		use_parent_look_tag = PassageTagLook(use_parent_look_tag_border, text, 
			look=self.parent_look, colour=self.parent_colour)
		use_parent_look_tag_border.set_child(use_parent_look_tag)
		self.parent = use_parent_look_tag

		use_parent_look_tag.Bind(wx.EVT_LEFT_UP, self.on_select_parent_look)

		# Choose colour.
		self.colours = []
		colour_sizer = wx.GridSizer(len(colours)/self.COLUMNS, self.COLUMNS, 0, 0)
		for colour in range(len(colours)):
			colour_rect_border = Border(panel, border_width=4, rounded_rectangle_radius=3)
			colour_rect = ColourRect(colour_rect_border, colour=colour)
			colour_rect_border.set_child(colour_rect)
			self.colours.append(colour_rect)
			colour_sizer.Add(colour_rect_border, 0, wx.ALIGN_CENTRE)

			colour_rect.Bind(wx.EVT_LEFT_UP, self.on_select_colour)

		# Choose looks.
		self.looks = []
		look_sizer = wx.GridSizer(len(looks)/2, 2, 3, 3)
		for look in range(len(looks)):
			look_tag_border = Border(panel)
			look_tag = PassageTagLook(look_tag_border, text, look=look, colour=self.colour)
			look_tag_border.set_child(look_tag)
			self.looks.append(look_tag)
			look_sizer.Add(look_tag_border, 0, wx.ALIGN_CENTRE)

			look_tag.Bind(wx.EVT_LEFT_UP, self.on_select_look)

		def AddItemWithPadding(item, padding):
			new_sizer = wx.BoxSizer(wx.HORIZONTAL)
			new_sizer.AddSpacer(padding)
			new_sizer.Add(item)
			new_sizer.AddSpacer(padding)
			main_sizer.Add(new_sizer)

		main_sizer.Add(use_parent_look_label, 0, wx.CENTRE)
		AddItemWithPadding(use_parent_look_tag_border, 5)
		main_sizer.Add(colour_label)
		AddItemWithPadding(colour_sizer, 5)
		main_sizer.Add(look_label)
		AddItemWithPadding(look_sizer, 5)

		self.update_borders()

		panel.SetSizer(main_sizer)
		o = wx.BoxSizer(wx.HORIZONTAL)
		o.Add(panel, 1, wx.GROW)
		self.SetSizer(o)
		self.Fit()
		self.Layout()
		self.look_updated = ObserverList()
		self.Position(*position)
	
	def update_borders(self):
		for item in self.colours:
			item.Parent.border = item.colour == self.colour
			item.Parent.Refresh()
				
		for item in self.looks:
			item.Parent.border = item.look == self.look
			item.Parent.Refresh()
			
		self.parent.Parent.border = self.using_parent_look
		self.parent.Parent.Refresh()

	def on_select_colour(self, event):
		self.using_parent_look = False
		colour_rect = event.EventObject
		#self.Dismiss()
		self.colour = colour_rect.colour
		# Set the look to the default look for that colour.
		self.look = colours[self.colour][2]
		for item in self.looks:
			item.set_scheme(item.look, self.colour)

		self.update_borders()

		self.Fit()
		self.Layout()
		self.look_updated(self.look, self.colour)

	def on_select_look(self, event):
		self.using_parent_look = False
		look_passage_tag = event.EventObject
		#self.Dismiss()
		self.look = look_passage_tag.look
		self.update_borders()
		for item in self.colours:
			item.Parent.update_width(item.border)
		self.update_borders()
		self.Fit()
		self.Layout()
		self.look_updated(self.look, self.colour)

	def on_select_parent_look(self, event):
		self.using_parent_look = True
		parent_look_passage_tag = event.EventObject
		#self.Dismiss()
		self.colour = parent_look_passage_tag.colour
		self.look = parent_look_passage_tag.look
		self.update_borders()
		for item in self.looks:
			item.set_scheme(item.look, self.colour)

		self.update_borders()
		self.Fit()
		self.Layout()
		self.look_updated(None, None, is_parent=True)

def run():
	import util.i18n
	util.i18n.initialize()
	a = wx.App(0)
	d = wx.Dialog(None, size=(400, 400))
	d.Sizer = wx.FlexGridSizer(5, 4, 5, 5)
	p = PassageTagLook(d, "Passage Text")
	def switch(evt=None):
		if evt: evt.Skip()
		generate_new_colour()
		p._create_bitmap()
		p.Refresh()
	
	p.Bind(wx.EVT_MOTION, switch)
	d.Sizer.Add(p)
#	for i in range(3):
#		d.Sizer.Add((0, 0))
#
#	for idx, item in enumerate(schemes):
#		d.Sizer.Add(PassageTagLook(d, "Passage %d" % idx, item))
#		if idx % 10 == 9:
#			d.Sizer.Add((0, 0))
#			d.Sizer.Add((0, 0))

	def show(event):
		btn = event.GetEventObject()
		pos = btn.ClientToScreen((btn.Size[0], 0))
		position = pos, (-btn.Size[0], btn.Size[0])
		l = LookPicker(d, "test", position)
		l.Popup()

	p.Bind(wx.EVT_LEFT_UP, show)
	d.ShowModal()

if __name__ == '__main__':
	run()

