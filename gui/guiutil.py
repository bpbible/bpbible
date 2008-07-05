import wx
import guiconfig
import config
from util import osutils
from util import debug

def toplevel_parent(item):
	parent = item.Parent
	while parent:
		if parent.TopLevel:
			return parent

		parent = parent.Parent

def get_mouse_pos(window, scrolled=False):
	xc, yc = wx.GetMousePosition()
	x, y =  window.ScreenToClient((xc, yc))
	if scrolled:
		x, y =  window.CalcUnscrolledPosition(x, y)
	return x, y

class FreezeUI(object):
	"""Same purpose as wx.WindowUpdateUILocker"""
	def __init__(self, window):
		self.window = window
		self.window.Freeze()
	
	def __del__(self):
		if self.window.IsFrozen():	
			self.window.Thaw()

def frozen(function):
	def frozen_internal(self, *args, **kwargs):
		self.Freeze()
		try:
			function(self, *args, **kwargs)
		finally:
			if self.IsFrozen():	
				self.Thaw()
	
	frozen_internal.__name__ = function.__name__
	return frozen_internal

def copy(text):
	guiconfig.mainfrm.copy(text)

def image_on_background(bmp, background_colour):
	# I'm not sure this works...
	new_bmp = wx.EmptyBitmap(*bmp.Size)
	dc = wx.MemoryDC()
	dc.SelectObject(new_bmp)
	dc.Brush = wx.Brush(background_colour)
	dc.Pen = wx.TRANSPARENT_PEN
	dc.DrawRectangle(0, 0, *bmp.Size)
	dc.DrawBitmap(bmp, 0, 0, True)
	del dc
	return new_bmp
	

def dispatch_keypress(actions, event):
	"""Dispatch a keypress based on an events table.

	actions is to be a sequence of keypress: callable
	where keypress is either a key code or a key code, modifiers tuple
	event is the key event"""
	for item, func in actions.items():
		if not isinstance(item, tuple):
			item = item, wx.MOD_NONE
		
		if item == (event.KeyCode, event.Modifiers):
			func()
			break

	else:
		event.Skip()

def image(f):
	# load and process image
	image = wx.Image(config.graphics_path + f)
	return image

def bmp(f, force_mask=False):
	# load and process image
	image = wx.Image(config.graphics_path + f)
	if osutils.is_win2000() or force_mask:
		image.ConvertAlphaToMask()

	return wx.BitmapFromImage(image)

def call_after_x(loops, func, *args, **kwargs):
	assert callable(func)
	if loops == 0:
		func(*args, **kwargs)
	else:
		args = (wx.CallAfter,) * (loops - 1) + (func,) + args 
		wx.CallAfter(*args, **kwargs)

def is_xp_styled():
	"""Return whether user has xp styles on""" 
	return True
	# if we have ctypes in our py2exe build, we should enable this function
	#try:
	#	import ctypes
	#	return ctypes.windll.uxtheme.IsAppThemed()
	#except Exception, e:
	#	dprint(WARNING, "Error trying to see if it is styled", e) 
	#	return False

def open_web_browser(href):
	# I would use webbrowser, but it doesn't seem to work very well
	#import webbrowser
	#
	## Python 2.5+
	#if hasattr(webbrowser, "open_new_tab"):
	#	webbrowser.open_new_tab(href)
	## Python <= 2.4
	#else:
	#	webbrowser.open_new(href)
	wx.LaunchDefaultBrowser(href)

def get_screen_rect(point):
	"""Get the size of the screen the given window is on"""
	screen = wx.Display.GetFromPoint(point)
	if screen == wx.NOT_FOUND:
		debug.dprint(debug.WARNING, "Couldn't find screen for window", window)
		return wx.Rect()
	
	display = wx.Display(screen)
	return display.GetClientArea()
