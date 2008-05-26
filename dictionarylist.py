import bisect

import wx
#import wx.lib.buttons as buttons
import wx.calendar

from backend.bibleinterface import biblemgr
from util.observerlist import ObserverList
from gui.virtuallist import VirtualListBox
from gui.guiutil import bmp
from util import osutils

_disabled = False#True

class DateConverter(object):
	def __init__(self, object):
		self.object = object
	
	def __len__(self):
		return len(self.object)
	
	def __getitem__(self, item):
		return mmdd_to_date(self.object[item]) or self.object[item]

class Upper(object):
	def __init__(self, object):
		self.object = object
	
	def __len__(self):
		return len(self.object)
	
	def __getitem__(self, item):
		return self.object[item].upper()
	

class DictionaryList(VirtualListBox):
	def __init__(self, parent, book):
		super(DictionaryList, self).__init__(parent)
		self.book = None

	def set_book(self, book):
		self.book = book
		b = wx.BusyInfo("Getting dictionary topic list...")
		if not _disabled:
			self.topics = book.GetTopics()
			# TODO: this is broken if we don't have a proper module and get
			# returned a list...
			self._upper_topics = Upper(self.topics)
			
			if book.has_feature("DailyDevotion"):
				self.topics = DateConverter(self.topics)
			
		else:
			self.topics = ["DISABLED"]
			self._upper_topics = self.topics

		self.set_data(self.topics)

	def choose_item(self, text):
		# get what sword thinks the key should be
		text = self.book.snap_text(text)

		# then look it up in the list
		idx = bisect.bisect_left(self._upper_topics, unicode(text))

		idx = min(len(self.topics)-1, idx)
		if idx >= 0:
			self.EnsureVisible(idx)
			self.Select(idx)

# we want users to be able to view the 29 february even when not in a leap
# year
leap_year_default_date = wx.DateTime()
leap_year_default_date.ParseDate("1 Jan 2008")

def date_to_mmdd(date, return_formatted=True):
	# tack the following bits on the end to see if they help give us dates
	# the second is February -> February 1
	# the third is 29 February -> 29 February 2008
	additions = ["", " 1", " 2008"]
	dt = wx.DateTime()

	# turn off logging to avoid debug messages
	ol = wx.Log.GetLogLevel()
	wx.Log.SetLogLevel(0)
	try:
		for addition in additions:
			ansa = dt.ParseDate(date + addition)
			if ansa != -1:
				if return_formatted:
					return dt.Format("%m.%d")
				return dt
		
	finally:
		# now turn it on again	
		wx.Log.SetLogLevel(ol)
		
	return None

	
def mmdd_to_date(date):
	dt = wx.DateTime()
	ansa = dt.ParseFormat(date, "%m.%d", leap_year_default_date)
	if ansa == -1:
		return None

	return dt.Format("%B ") + str(dt.Day)

class TextEntry(wx.Panel):
	def __init__(self, parent):
		super(TextEntry, self).__init__(parent)
		self.text = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		
		
		self.calendar_pic = bmp("calendar_view_day.png")

		self.calendar = wx.BitmapButton(
			self, 
			bitmap=self.calendar_pic
		)
		#self.calendar.SetBezelWidth(1)
		w, h = self.text.Size[1], self.text.Size[1]
		self.calendar.SetSize((w, h))
		self.calendar.MinSize = self.calendar.Size
		self.calendar.Bind(wx.EVT_BUTTON, self.show_popup)
		
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(self.text, 1, wx.GROW)
		self.calendar_sizer_item = sizer.Add(self.calendar, 0, 
			flag=
				wx.FIXED_MINSIZE |
				wx.ALIGN_CENTER  |
				wx.SHAPED
		)
		
		self.SetSizer(sizer)
		self.show_calendar(False)
		
	
	def show_popup(self, event):
		def on_cal_changed(event):
			dt = event.GetDate()
			self.Parent.choose_item(dt.Format("%B ") + str(dt.Day))

		def on_cal(event):
			win.Destroy()
		
		win = wx.PopupTransientWindow(self,
								 wx.NO_BORDER)

		now_date = date_to_mmdd(self.text.Value, return_formatted=False)

		if now_date is None:
			now_date = wx.DateTime_Now()		
		
		style = 0

		if osutils.is_msw():
			style = wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION
		
		panel = wx.Panel(win)
		
		cal = wx.calendar.CalendarCtrl(panel, -1, now_date, pos=(1,1),
			style=wx.RAISED_BORDER|style
		)

		panel.ClientSize = cal.Size + (1,1)
		cal.Bind(wx.calendar.EVT_CALENDAR_SEL_CHANGED, on_cal_changed)
		cal.Bind(wx.calendar.EVT_CALENDAR, on_cal)
		size_combo = 0
		
		if not style & wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION:
			# hide the spin control
			for child in panel.Children:
				if isinstance(child, wx.SpinCtrl):
					child.Hide()

					# we will shorten ourselves by this amount
					size_combo = child.Size[1] + 6
			
			# make combo fill up rest of space
			for child in panel.Children:
				if isinstance(child, wx.ComboBox):
					child.Size = cal.Size[0], -1

		# Show the popup right below or above the button
		# depending on available screen space...
		btn = event.GetEventObject()
		pos = btn.ClientToScreen((0, btn.Size[1]))
		win.Size = panel.GetSize() - (0, size_combo)
		win.Position(pos, (0, 0))#win.Size[1]))

		win.Popup()
		
	

	
	def show_calendar(self, visible=True):
		self.is_calendar = visible
		self.Sizer.Show(self.calendar, visible)
		self.Sizer.Layout()
	
	def get_value(self):
		if not self.is_calendar:
			return self.text.GetValue()

		else:
			value = self.text.GetValue()
			mm_dd = date_to_mmdd(value)
			if not mm_dd:
				return value
			return mm_dd
	
	def set_value(self, text):
		self.text.ChangeValue(text)			

		
class DictionarySelector(wx.Panel):
	def __init__(self, parent, book):
		super(DictionarySelector, self).__init__(parent)
		self.text_entry = TextEntry(self)
		self.list = DictionaryList(self, book)
		self.set_book(book)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.text_entry, 0, wx.GROW)
		sizer.Add(self.list, 1, wx.GROW)
		self.text_entry.text.Bind(wx.EVT_TEXT, self.on_text)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		width = 200

		self.SetSizerAndFit(sizer)
		self.item_changed = ObserverList()

	def on_text(self, event):
		# unbind the selected event so that we don't go into an infinite loop
		# TODO: check whether this is really necessary
		self.list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
		self.list.choose_item(self.GetValue().upper())
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		self.item_changed()

	def on_list(self, event):
		text = self.list.GetItemText(event.m_itemIndex)
		self.choose_item(text)

	def choose_item(self, text):
		# change the value (doesn't fire an event)
		self.text_entry.set_value(text)

		# scroll to the correct entry, and fire off an item_changed
		wx.CallAfter(self.on_text, None)



	def GetValue(self):
		return self.text_entry.get_value()

	SetValue = choose_item

	def set_book(self, book):
		was_devotion = self.text_entry.is_calendar
		self.text_entry.show_calendar(book.has_feature("DailyDevotion"))
		self.list.set_book(book)

		# if we are changing to a devotion, and weren't a devotion,
		# set it to today
		if book.has_feature("DailyDevotion") and not was_devotion:
			dt = wx.DateTime.Today()
			self.choose_item(dt.Format("%B ") + str(dt.Day))
		else:
			self.choose_item(self.text_entry.text.Value)
			

if __name__ == '__main__':
	a=wx.App(0)
	d=wx.Dialog(None, style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
	biblemgr.dictionary.SetModule("ot1nt2")
	l=DictionarySelector(d, biblemgr.dictionary)
	#button = wx.Button(d, pos=(300, 100), label="TEST")
	#button.Bind(wx.EVT_BUTTON, lambda x:l.choose_item("METAL"))
	sizer = wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(l, 1, wx.GROW)
	d.SetSizer(sizer)

	d.ShowModal()

