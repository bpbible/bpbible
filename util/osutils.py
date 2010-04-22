import os
import sys
import wx

def is_gtk():
	return "wxGTK" in wx.PlatformInfo

def is_msw():
	return "wxMSW" in wx.PlatformInfo

def is_mac():
	return "wxMac" in wx.PlatformInfo

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

def system_open_file(filepath):
	if is_mac():
		o = "open"
	elif is_gtk():
		o = "xdg-open"
	else:
		# the first argument if in quotes becomes the title of the
		# command prompt it will then launch - ugh
		# so put something in quotes at the start to pacify it
		o = 'start "title"'
	os.system('%s "%s"' % (o, filepath))

def get_user_data_dir():
	"""Gets the user data directory for BPBible for the current platform.

	This copies the wxWidgets wxStandardPaths::GetUserDataDir(),
	which we cannot easily use because it relies on the application being
	instantiated before it is used.
	"""
	appname = "bpbible"
	home_dir = os.path.expanduser('~')
	if is_msw():
		if "APPDATA" not in os.environ:
			import wx
			a = wx.App()
			wx.MessageBox(
				"APPDATA is not set. Quitting. \nENVIRON=%s" % os.environ,
				"Fatal Error")
			raise SystemExit("APPDATA is not set.\nENVIRON=%s" % os.environ)

		return os.path.join(os.environ["APPDATA"], appname)
	elif is_mac():
		return os.path.join(home_dir, "Library", "Application Support", appname)
	else:
		return os.path.join(home_dir, ".%s" % appname)
