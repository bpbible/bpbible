import bisect

import wx

from backend.bibleinterface import biblemgr
from util.observerlist import ObserverList
from gui.virtuallist import VirtualListBox

_disabled = False#True

class DictionaryList(VirtualListBox):
	def __init__(self, parent, book):
		super(DictionaryList, self).__init__(parent)

		self.set_book(book)

	def set_book(self, book):
		self.book = book
		def set_book():
			b = wx.BusyInfo("Getting dictionary topic list...")
			if not _disabled:
				self.topics = book.GetTopics()
			else:
				self.topics = ["DISABLED"]
			self._topics = [s.upper() for s in self.topics]

			self.set_data(self.topics)


		wx.CallAfter(set_book)

	def choose_item(self, text):
		text = self.book.snap_text(text)
		# get what sword thinks the key should be
		idx = bisect.bisect_left(self._topics, text)

		idx = min(len(self.topics)-1, idx)
		self.EnsureVisible(idx)
		self.Select(idx)

class DictionarySelector(wx.Panel):
	def __init__(self, parent, book):
		super(DictionarySelector, self).__init__(parent)
		self.list = DictionaryList(self, book)
		self.text_entry = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.text_entry, 0, wx.GROW)
		sizer.Add(self.list, 1, wx.GROW)
		self.text_entry.Bind(wx.EVT_TEXT, self.on_text)
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		width = 200

		self.SetSizerAndFit(sizer)
		self.item_changed = ObserverList()


	def on_text(self, event):
		self.list.Unbind(wx.EVT_LIST_ITEM_SELECTED)
		self.list.choose_item(self.text_entry.GetValue())
		self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_list)
		self.item_changed()


	def on_list(self, event):
		self.choose_item(event.GetText())
		self.item_changed()


	def choose_item(self, text):
		was_same = str(self.text_entry.GetValue()) == str(text)

		self.text_entry.SetValue(text)
		if was_same:
			# if we try to change the text to the same thing, it doesn't fire
			# event. So call this anyway
			wx.CallAfter(self.on_text, None)



	def GetValue(self):
		return self.text_entry.GetValue()

	SetValue = choose_item

	def set_book(self, book):
		self.list.set_book(book)

if __name__ == '__main__':
	a=wx.App(0)
	d=wx.Dialog(None, style=wx.RESIZE_BORDER|wx.DEFAULT_DIALOG_STYLE)
	l=DictionarySelector(d, biblemgr.dictionary)
	#button = wx.Button(d, pos=(300, 100), label="TEST")
	#button.Bind(wx.EVT_BUTTON, lambda x:l.choose_item("METAL"))
	sizer = wx.BoxSizer(wx.HORIZONTAL)
	sizer.Add(l, 1, wx.GROW)
	d.SetSizer(sizer)

	d.ShowModal()

