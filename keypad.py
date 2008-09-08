"""
A virtual keypad to be used for typing in words for searching
"""

import wx
import unicodedata
from util.observerlist import ObserverList

class KeyPad(wx.PopupTransientWindow):
	COLUMNS = 16
	def __init__(self, parent, keys, position):
		super(KeyPad, self).__init__(parent, style=wx.NO_BORDER)
		panel = wx.Panel(self, style=wx.RAISED_BORDER)
		sizer = wx.GridSizer(len(keys)/self.COLUMNS, self.COLUMNS, 1, 1)
		for key in sorted(keys):
			button = wx.Button(panel, label=key, style=wx.BU_EXACTFIT)
			button.SetToolTipString(
				unicodedata.name(key, "<Unknown letter (%r)>" % key))
			sizer.Add(button, 0, wx.GROW)

		panel.SetSizer (sizer)
		o = wx.BoxSizer(wx.HORIZONTAL)
		o.Add(panel, 1, wx.GROW)
		self.SetSizer(o)
		self.Bind(wx.EVT_BUTTON, self.on_button)
		self.Fit()
		self.Layout()
		self.key_pressed = ObserverList()
		self.Position(*position)
		
	
	def on_button(self, event):
		self.key_pressed(event.EventObject.Label)

if __name__ == '__main__':
	app = wx.App(0)
	import search.search as s
	import config
	n=s.ReadIndex("NASLex")
	
	f = wx.Frame(None)
	b = wx.Button(f, wx.ID_ANY, "Press me")
	text = u'\u1f04\u03b3\u03b1\u03bc\u03bf\u03c2'	
	text = n.statistics["letters"]

	def print_(value):
		print value

	def show_popup(evt):
		kp = KeyPad(f, text, (wx.GetMousePosition(), (0, 0)))
		kp.Popup()
		kp.key_pressed += print_

	b.Bind(wx.EVT_BUTTON, show_popup)
	f.Show()
	app.MainLoop()
