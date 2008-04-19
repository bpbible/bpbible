import wx
import wx.html
from xrc.fontchoice_xrc import *
import guiconfig
from gui import htmlbase
from util.configmgr import config_manager

class HtmlWin(wx.html.HtmlWindow):
	def __init__(self):
		pre = wx.html.PreHtmlWindow()
		self.PostCreate(pre)
		self.Bind(wx.html.EVT_HTML_LINK_CLICKED, lambda x:x)
	

preview = """<body bgcolor="%s"><div><font color="%s"><p><h4>Hearing and Doing the Word</h4><br>
<a href = '#current' target='19'><a name='19'><small><sup>19</sup></small></a></a> <font color = 'green'> <small><a href="bible:1John 2:21">1John 2:21</a></small> Know this, my beloved brothers: let every person  <small><a href="bible:Eccl 5:1-2">Eccl 5:1-2</a></small> be quick to hear,  <small><a href="bible:Prov 10:19">Prov 10:19</a> <a href="bible:Prov 17:27">Prov 17:27</a></small> slow to speak,  <small><a href="bible:Prov 14:29">Prov 14:29</a></small> slow to anger;</font> 
<a href = "#20" name="20" target="20"><small><sup>20</sup></small></a> for the anger of man does not produce the righteousness that God requires.<a href="passagestudy.jsp?action=showNote&type=n&value=1&module=ESV&passage=James+1%%3A20"><small><sup>*n</sup></small></a></font></div></body>"""

class FontChoiceDialog(xrcFontChoiceDialog):
	def __init__(self, parent, font, size):
		super(FontChoiceDialog, self).__init__(parent)
		self.font_face.Bind(wx.EVT_CHOICE, lambda x:self.update_preview())
		self.font_size.Bind(wx.EVT_SPINCTRL, lambda x:self.update_preview())
		names = wx.FontEnumerator().GetFacenames()
		names.sort()
		self.font_face.Clear()
		[self.font_face.Append(x) for x in names]

		#if size is None:
		#	size = max(wx.NORMAL_FONT.PointSize, 10)
		#
		#if font is None:
		#	font = wx.Font(size, wx.SWISS, wx.NORMAL, wx.NORMAL, False);
		#
		#	font = font.FaceName


		if not self.font_face.SetStringSelection(font):
			self.font_face.SetSelection(0)

		self.font_size.SetValue(size)
		self.update_preview()
		

	def update_preview(self):
		self.preview.SetStandardFonts(self.font_size.Value, 
			self.font_face.StringSelection, "")
		
		
		self.preview.SetPage(preview % tuple(guiconfig.get_window_colours()))
	
	def ShowModal(self):
		ansa = super(FontChoiceDialog, self).ShowModal()
		if ansa == wx.ID_OK:
			config_manager["Html"]["base_text_size"] = self.font_size.Value
			config_manager["Html"]["font_name"] = self.font_face.StringSelection
	


if __name__ == '__main__':
	a=wx.App(0)
	FontChoiceDialog(None, "Arial", 10).ShowModal()

