__all__ = [
	'copyverses_xrc.py',
	'xrc_stc.py',
]
import wx.xrc
from wx import xrc
import os
import xrc_stc

def Load(self, resourcepath):
	self.AddHandler(xrc_stc.STCXmlHandler())
	self.AddHandler(xrc_stc.CPXmlHandler())
	

	if os.path.exists(resourcepath):
		self.original_Load(resourcepath)
	else:
		self.original_Load("xrc/"+resourcepath)
	
wx.xrc.XmlResource.original_Load = wx.xrc.XmlResource.Load
wx.xrc.XmlResource.Load = Load
def XRCCTRL(item, name):
	id = xrc.XRCID(name)
	ctrl = item.FindWindowById(id)
	if ctrl: return ctrl
	if not hasattr(item, "GetToolBar"):
		return ctrl
		
	toolbar = item.GetToolBar()
	if toolbar:
		ctrl = toolbar.FindWindowById(id)
		return ctrl
	
	#if not hasattr(item, "GetMenuBar"):
		return ctrl
		
	#menubar = item.GetMenuBar()
	#if menubar:
	#	ctrl = menubar.FindItem(id)
		
	#return ctrl

wx.xrc.XRCCTRL=XRCCTRL


