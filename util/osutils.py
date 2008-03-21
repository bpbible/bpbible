import sys
import wx


def is_gtk():
	return "wxGTK" in wx.PlatformInfo

def is_msw():
	return "wxMSW" in wx.PlatformInfo

def is_win2000():
	"""
	Return whether windows <= 2000

	On windows 2000, transparency is 1 bit, so it may need to be converted to one bit
	This function returns whether it needs to
	"""
	
	if sys.platform == "win32":
		major, minor, _, platform, _ = sys.getwindowsversion()
		# this function really returns whether it is <= 2000
		if platform != 2 or major < 5 or (major, minor) == (5, 0):
			return True
	
	return False

def is_py2exe():
	return hasattr(sys, "frozen")
