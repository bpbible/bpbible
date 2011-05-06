import bisect

import wx
#import wx.lib.buttons as buttons
import wx.calendar

from backend.bibleinterface import biblemgr
from backend.dictionary import ListDataWrapper
from util.observerlist import ObserverList
from gui.virtuallist import VirtualListBox
from gui.guiutil import bmp
from util import osutils
from util.unicode import to_str

from gui import fonts
import guiconfig

_disabled = False#True

class Upper(object):
	def __init__(self, object):
		self.object = object
	
	def __len__(self):
		return len(self.object)
	
	def __getitem__(self, item):
		return self.object[item].upper()
	

def is_date_conversion_supported():
	# vietnamese under windows doesn't complete the loop
	return wx.DateTime.Now().ParseFormat(wx.DateTime.Now().Format("%B %d"), "%B %d") != -1
	
class DictionaryList(VirtualListBox):
	def __init__(self, parent, book):
		super(DictionaryList, self).__init__(parent)
		self.book = None

	def set_book(self, book):
		self.book = book
		b = wx.BusyInfo("Getting dictionary topic list...")
		if not _disabled:
			# TODO: this is broken if we don't have a proper module and get
			# returned a list...
			
			self.topics = book.GetTopics(user_output=True)
			self._upper_topics = Upper(self.topics)
			
		else:
			self.topics = ["DISABLED"]
			self._upper_topics = self.topics

		self.set_data(self.topics)

	def choose_item(self, text, update_text_entry_value=False):
		idx = self.topics.mod.getEntryForKey(
			to_str(text, self.topics.mod)
		)

		idx = min(len(self.topics)-1, idx)
		if idx >= 0:
			self.EnsureVisible(idx)
			self.Select(idx)
		return idx

# we want users to be able to view the 29 february even when not in a leap
# year
leap_year_default_date = wx.DateTime()
leap_year_default_date.ParseDate("1 Jan 2008")

def date_to_mmdd(date, return_formatted=True):
	dt = wx.DateTime()
	
	if not return_formatted and not is_date_conversion_supported():
		try:
			month, day = map(int, date.split(".", 1))
		except ValueError:
			pass
		else:
			dt.Set(day, month-1, 2008)
			return dt
			

	# tack the following bits on the end to see if they help give us dates
	# the second is February -> February 1
	# the third is 29 February -> 29 February 2008
	additions = ["", " 1", " 2008"]

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

	
#def mmdd_to_date(date):
#	if not is_date_conversion_supported():
#		return None
#
#	dt = wx.DateTime()
#	ansa = dt.ParseFormat(date, "%m.%d", leap_year_default_date)
#	if ansa == -1:
#		return None
#
#	return dt.Format("%B ") + str(dt.Day)

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
			if is_date_conversion_supported():
				self.Parent.choose_item(dt.Format("%B ") + str(dt.Day))
			else:
				self.Parent.choose_item(dt.Format("%m.%d"))

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

		win.Size = panel.GetSize() - (0, size_combo)
		
		# Show the popup right below or above the button
		# depending on available screen space...
		btn = event.GetEventObject()
		pos = btn.ClientToScreen((btn.Size[0], 0))
		win.Position(pos, (-btn.Size[0], btn.Size[1]))

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
		self.timer = wx.Timer(self)
		self.item_to_focus_on = None
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.text_entry, 0, wx.GROW)
		sizer.Add(self.list, 1, wx.GROW)
		self.text_entry.text.Bind(wx.EVT_TEXT, self.on_text)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
		width = 200

		self.SetSizerAndFit(sizer)
		self.item_changed_observers = ObserverList()
		fonts.fonts_changed += self.set_font
		guiconfig.mainfrm.on_close += lambda:\
			fonts.fonts_changed.remove(self.set_font)
	
	def set_font(self):
		if self.list.book.mod is None:
			return

		font = fonts.get_module_gui_font(self.list.book.mod)

		self.list.Font = font
		self.text_entry.text.Font = font
		self.Layout()
		
	def on_text(self, event):
		self.item_to_focus_on = self.text_entry
		self.change_selected_text(is_user_typing=True)

	def change_selected_text(self, is_user_typing=False, update_text_entry_value=False):
		# unbind the selected event so that we don't go into an infinite loop
		# TODO: check whether this is really necessary
		self.list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
		idx = self.list.choose_item(self.GetValue().upper(), update_text_entry_value=update_text_entry_value)
		if idx >= 0 and update_text_entry_value:
			self.text_entry.set_value(self.list.GetItemText(idx))
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		if is_user_typing:
			self.timer.Start(200, oneShot=True)
		else:
			self.item_changed()

	def on_timer(self, event):
		self.item_changed()

	def on_list(self, event):
		self.item_to_focus_on = self.list
		text = self.list.GetItemText(event.m_itemIndex)
		self.choose_item(text)

	def choose_item(self, text, update_text_entry_value=False):
		# change the value (doesn't fire an event)
		self.text_entry.set_value(text)

		# scroll to the correct entry, and fire off an item_changed
		wx.CallAfter(lambda: self.change_selected_text(update_text_entry_value=update_text_entry_value))

	def item_changed(self):
		self.item_changed_observers()
		if self.item_to_focus_on:
			self.item_to_focus_on.SetFocus()
			self.item_to_focus_on = None



	def GetValue(self):
		return self.text_entry.get_value()

	def set_book(self, book):
		was_devotion = self.text_entry.is_calendar
		self.text_entry.show_calendar(book.has_feature("DailyDevotion"))
		self.list.set_book(book)

		self.set_font()
	

		# if we are changing to a devotion, and weren't a devotion,
		# set it to today
		if book.has_feature("DailyDevotion") and not was_devotion:
			dt = wx.DateTime.Today()
			if is_date_conversion_supported():
				self.choose_item(dt.Format("%B ") + str(dt.Day))
			else:
				self.choose_item(dt.Format("%m.%d"))
				
		else:
			self.choose_item(self.text_entry.text.Value)
			

if __name__ == '__main__':
	a=wx.App(0)
	d=wx.Dialog(None, style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
	biblemgr.dictionary.SetModule("BibleCompanion")
	l=DictionarySelector(d, biblemgr.dictionary)
	#button = wx.Button(d, pos=(300, 100), label="TEST")
	#button.Bind(wx.EVT_BUTTON, lambda x:l.choose_item("METAL"))
	sizer = wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(l, 1, wx.GROW)
	d.SetSizer(sizer)

	d.ShowModal()

