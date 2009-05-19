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
			try:
				if self.IsFrozen():	
					self.Thaw()
				# even with checking it is frozen, it will sometimes throw an
				# assertion on 
			except AssertionError, e:
				debug.dprint(debug.WARNING, "Ignoring assertion with thaw", e)
	
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
		debug.dprint(debug.WARNING, "Couldn't find screen for point", point)
		return wx.Rect()
	
	display = wx.Display(screen)
	return display.GetClientArea()


# try to stop the interactive interpreter grinding our _ builtin into the dirt
def fix_underscore_in_builtin():
	import wx.py.dispatcher as d
	# it helpfully sends out this signal when a statement has just been
	# executed
	d.connect(handle, signal='Interpreter.push', weak=False)

def handle(signal, sender, command, source, more, **kwargs):
	import __builtin__
	from types import MethodType
	
	import util.i18n
	
	# if the _ isn't correct, move builtin _ into the local _ 
	if not isinstance(_, MethodType) or _.im_self is not util.i18n.mytranslation:
		sender.locals['_'] = __builtin__._
	
		# now trample over the last-result _ with the i18n _
		util.i18n.mytranslation.install(unicode=True)

# install our fixer
fix_underscore_in_builtin()

class PopupWindow(wx.MiniFrame):
	def __init__(self, parent, style=wx.NO_BORDER|wx.FRAME_FLOAT_ON_PARENT):
		super(PopupWindow, self).__init__(parent, style=style)
#
#	def Dismiss(self):
#		print "Dismissing"
#		if self.child.HasCapture():
#			self.child.ReleaseMouse()
#		self.child.Unbind(wx.EVT_LEFT_DOWN)
#		self.child.Unbind(wx.EVT_KILL_FOCUS)
#		self.Unbind(wx.EVT_IDLE)
#		self.Hide()
#		#self.old_focus.SetFocus()


class PopupTransientWindow(PopupWindow):
	def Position(self, ptOrigin, size):
		size = wx.Point(*size)
		ptOrigin = wx.Point(*ptOrigin)
		sizeScreen = wx.GetDisplaySize()
		sizeSelf = self.Size
		
		# is there enough space to put the popup below the window (where we put it
		# by default)?
		y = ptOrigin.y + size.y
		if ( y + sizeSelf.y > sizeScreen.y ):
		    # check if there is enough space above
		    if ( ptOrigin.y > sizeSelf.y ):
		        # do position the control above the window
		        y -= size.y + sizeSelf.y;
		    #else: not enough space below nor above, leave below
		
		# now check left/right too
		x = ptOrigin.x;
		        
		if ( wx.GetApp().GetLayoutDirection() == wx.Layout_RightToLeft ):
		    # shift the window to the left instead of the right.
		    x -= size.x;
		    x -= sizeSelf.x;        # also shift it by window width.
		else:
		    x += size.x;
		
		
		if ( x + sizeSelf.x > sizeScreen.x ):
		    # check if there is enough space to the left
		    if ( ptOrigin.x > sizeSelf.x ):
		        # do position the control to the left
		        x -= size.x + sizeSelf.x;
		    #else: not enough space there neither, leave in default position
		
		#BM: do we need this flag below? it isn't defined
		self.Move((x, y))#, wx.SIZE_NO_ADJUSTMENTS); 

	#	print "positioning at", pos1, pos2
	#	self.SetPosition(pos1)
	
	def Popup(self):
		self.old_focus = wx.Window.FindFocus()
		print "Showing"
		self.child = self.Children[0]
		self.child.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
		self.child.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

		self.Bind(wx.EVT_IDLE, self.OnIdle)

		self.child.CaptureMouse()
		self.Show()
	
	def OnIdle(self, event):
		event.Skip()
		if self.IsShown():
			pos = self.child.ScreenToClient(wx.GetMousePosition())
			rect = wx.RectS(self.child.Size)
			if rect.Contains(pos):
				if self.child.HasCapture():	
					print "Releasing"
					self.child.ReleaseMouse()
			else:
				if not self.child.HasCapture():
					print "Capturing"
					self.child.CaptureMouse()
		
	def OnKillFocus(self, event):
		event.GetWindow()
		while win:
			if win == self:
				return
			win = win.Parent
		self.Dismiss()

	def Dismiss(self):
		print "Dismissing"
		if self.child.HasCapture():
			self.child.ReleaseMouse()
		self.child.Unbind(wx.EVT_LEFT_DOWN)
		self.child.Unbind(wx.EVT_KILL_FOCUS)
		self.Unbind(wx.EVT_IDLE)
		self.Hide()
		#self.old_focus.SetFocus()

	def OnLeftDown(self, event):
		print "Left down"
		if self.ProcessLeftDown(event):
			return
		
		win = event.GetEventObject()
		if win.Rect.Contains(event.Position):
			event.Skip()
		else:
			# do the coords translation now as after DismissAndNotify()
			# m_popup may be destroyed
			event2 = wx.MouseEvent()
			event2.__dict__ = event.__dict__.copy()
			                                                                
			event2.m_x, event2.m_y = self.ClientToScreen((event2.m_x, event2.m_y))
			                                                                
			# clicking outside a popup dismisses it
			self.Dismiss()
			                                                                
			# dismissing a tooltip shouldn't waste a click, i.e. you
			# should be able to dismiss it and press the button with the
			# same click, so repost this event to the window beneath us
			winUnder = wx.FindWindowAtPoint(event2.GetPosition())
			if ( winUnder ):
			    # translate the event coords to the ones of the window
			    # which is going to get the event
			    event2.m_x, event2.m_y = winUnder.ScreenToClient((event2.m_x, event2.m_y))
			                                                                
			    event2.SetEventObject(winUnder);
			    wx.PostEvent(winUnder, event2);
	
	def ProcessLeftDown(self, event):
		self.Dismiss()	
		return False


if osutils.is_mac():
	# mac doesn't implement these
	wx.PopupTransientWindow = PopupTransientWindow
	wx.PopupWindow = PopupWindow

	hasNativePopupWindows = False
else:
	hasNativePopupWindows = True

def add_close_window_esc_accelerator(frame, handler):

	def escape_handler(event):
		if event.KeyCode == wx.WXK_ESCAPE and not event.GetModifiers():
			event.Skip()
			handler()
	
	bind_event_to_all_children(frame, wx.EVT_KEY_UP, escape_handler,
			lambda child: child is not wx.Choice)
	
def bind_event_to_all_children(parent, event, handler,
		child_filter=(lambda child: True)):
	if not child_filter(parent):
		return

	parent.Bind(event, handler)
	for child in parent.Children:
		bind_event_to_all_children(child, event, handler, child_filter)
