import wx
#import PyAUI as aui


from wx import aui

#aui_hint = aui.AUI_MGR_RECTANGLE_HINT
aui_hint = aui.AUI_MGR_TRANSPARENT_HINT

mainfrm = None
app = None
icons = None

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
