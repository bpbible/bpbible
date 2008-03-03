import wx
import wx.stc as stc
import wx.xrc as xrc
import xrc_stc

# XRCed interface module
import wx.tools.XRCed.xxx as xxx#import xxx

# XRCed interface class
class xxxSTCCtrl(xxx.xxxObject, object):
	allParams = ['pos', 'size', 'style', 'value']
	winStyles = []#['wxLED_ALIGN_LEFT', 'wxLED_ALIGN_RIGHT', 
				# 'wxLED_ALIGN_CENTER', 'wxLED_DRAW_FADED']


class xxxCPCtrl(xxx.xxxContainer, object):
	allParams = ['label', 'pos', 'size', 'style', 'value']
	winStyles = []#['wxLED_ALIGN_LEFT', 'wxLED_ALIGN_RIGHT', 
				# 'wxLED_ALIGN_CENTER', 'wxLED_DRAW_FADED']

import wx.tools.XRCed.xxx as xxx#import xxx
# Register XML handler
xxx.register(xrc_stc.STCXmlHandler)
xxx.register(xrc_stc.CPXmlHandler)


# Register XRCed interface class
xxx.custom('StyledTextCtrl', xxxSTCCtrl)
xxx.custom('CollapsiblePane', xxxCPCtrl)

