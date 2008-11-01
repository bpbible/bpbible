import wx
from xrc.htmlide_xrc import xrcHtmlIde
import guiconfig

class HtmlIde(xrcHtmlIde):
	def __init__(self, parent):
		super(HtmlIde, self).__init__(parent)
		self.gui_go.Bind(wx.EVT_BUTTON, self.on_set_html)
		
	def on_set_html(self, event):
		self.html_window.mod = None
		self.html_window.SetPage(self.html_src.Value)

if __name__ == '__main__':
	a = wx.App(0)
	f = HtmlIde(None)
	f.Show()
	a.MainLoop()
