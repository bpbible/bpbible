import wx
#import PyAUI as aui


from wx import aui

#aui_hint = aui.AUI_MGR_RECTANGLE_HINT
aui_hint = aui.AUI_MGR_TRANSPARENT_HINT

mainfrm = None
app = None
icons = None


def get_tooltip_colours():
	colours = (wx.SYS_COLOUR_INFOBK, wx.SYS_COLOUR_INFOTEXT)
	return [wx.SystemSettings.GetColour(x).GetAsString(wx.C2S_HTML_SYNTAX) for x in colours]

