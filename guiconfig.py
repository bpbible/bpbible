import wx
import config
from util import osutils
from util.debug import dprint, MESSAGE

class DummyMainfrm(object):
	def hide_tooltips(*args, **kwargs):
		pass
	
	lost_focus = True

mainfrm = DummyMainfrm()
app = None
icons = None

use_versetree = not osutils.is_mac()
use_one_toolbar = osutils.is_mac()
def get_colour_set(colour_set):
	def get_tooltip_colours(html_style=True):
		colours = [wx.SystemSettings.GetColour(x) for x in colour_set]
		if html_style:
			colours = [x.GetAsString(wx.C2S_HTML_SYNTAX) for x in colours]

		return colours
	
	return get_tooltip_colours

get_tooltip_colours = get_colour_set(
	(wx.SYS_COLOUR_INFOBK, wx.SYS_COLOUR_INFOTEXT)
)

get_window_colours = get_colour_set(
	(wx.SYS_COLOUR_WINDOW, wx.SYS_COLOUR_WINDOWTEXT)
)
		

def load_icons():
	global icons
	wx.InitAllImageHandlers()

	icons = wx.IconBundle()
	for item in "16 32 48 64 128".split():
		path = config.graphics_path
		icon = wx.Image("%(path)sbible-%(item)sx%(item)s.png" % locals())
		if icon.IsOk():
			# on windows 2000, transparency is 1 bit, so convert it 
			# to one bit
			if osutils.is_win2000():
				icon.ConvertAlphaToMask()

			bmp = wx.BitmapFromImage(icon)
			icons.AddIcon(wx.IconFromBitmap(bmp))

	dprint(MESSAGE, "Loaded icon")
