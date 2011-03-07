#!/usr/bin/env python
import os
import sys

if hasattr(sys, "frozen"):
	# py2exe may get paths wrong
	if os.path.dirname(sys.argv[0]):
		os.chdir(os.path.dirname(sys.argv[0]))

# allow user to drop customization scripts in custom
# these will be auto-run
# for example, for distributing small patches
if os.path.isdir("custom"):
	for file in os.listdir("custom"):
		if os.path.isfile("custom/%s" % file) and file.endswith(".py"):
			execfile("custom/%s" % file)


from util.debug import dprint, MESSAGE, WARNING, is_debugging
dprint(MESSAGE, "Importing wx")

import wx
from util import osutils
def find_xulrunner_path():
	if osutils.is_mac():
		path = os.getcwd() + "/../MacOS/"
		if os.path.exists(path):
			return path
		else:
			return os.getcwd() + "/dist/BPBible.app/Contents/MacOS/"

	if osutils.is_gtk():
		xulrunner_path = (osutils.find_file_in_path("xulrunner") or
			osutils.find_file_in_path("xulrunner-stub"))
		if xulrunner_path:
			return os.path.dirname(os.path.realpath(xulrunner_path))

	path = os.path.join(os.getcwd(), "xulrunner")
	if not os.path.isdir(path):
		# XXX: Perhaps we should make this error handling a little more friendly?
		sys.stderr.write("Unable to find XULRunner.\n")
		sys.exit(1)
	return path


xulrunner_path = find_xulrunner_path()
dprint(MESSAGE, "XULRunner path is", xulrunner_path)

if osutils.is_msw():
	os.environ['PATH'] = xulrunner_path + ';' + os.environ['PATH']

dprint(MESSAGE, "importing wx.wc")
import wx.wc

dprint(MESSAGE, "/importing wx")

# make sure contribs can be imported...
import contrib

import config, guiconfig
from util import confparser
from util.configmgr import config_manager

import util.i18n
import gui.i18n

class MyApp(wx.App):
	def Initialize(self):
		# for py2exe
		import mainframe
		
		was_restarted = self.restarting
		self.starting = self.restarting = False
		config_manager.load()
		util.i18n.initialize()
		gui.i18n.initialize()
		
		frame = self.res.LoadFrame(None,  "MainFrame" )
		if(frame == None):
			wx.MessageBox("Could not load MainFrame from auifrm.xrc", \
				"Fatal Error", style = wx.ICON_ERROR)
			return False


		frame.SetIcons(guiconfig.icons)

		self.SetTopWindow(frame)
		frame.Show(osutils.is_gtk())
		if was_restarted:
			frame.Raise()
		
	
	def OnInit(self):
		self.InitXULRunner()
		self.SetWebPreferences()
		self.FindXULRunnerVersion()
		self.ShowSplashScreen()
		
		self.starting = True
		self.restarting = False
		self.reload_restarting = False
	
		dprint(MESSAGE, "App Init")
		guiconfig.load_icons()
		

		from wx import xrc
		self.res = xrc.XmlResource(config.xrc_path+"auifrm.xrc" )
		return True

	def ShowSplashScreen(self):
		if not config.show_splashscreen():
			self.splash = None
			return

		picture = 'splashscreen.png'
		bitmap = wx.BitmapFromImage(
			wx.Image(config.graphics_path + picture)
		)
		self.splash = wx.SplashScreen(
			bitmap, 
			wx.SPLASH_CENTRE_ON_SCREEN|wx.SPLASH_NO_TIMEOUT,
			0,
			None,
			style=wx.FRAME_NO_TASKBAR|wx.BORDER_NONE
		)
		self.splash.Show()
		self.splash.Raise()

	def InitXULRunner(self):
		dprint(MESSAGE, "Initialising XULRunner engine")
		wx.wc.WebControl.AddPluginPath("Mozilla Firefox\\Plugins")
		wx.wc.WebControl.InitEngine(xulrunner_path)

		# NOTE: DO NOT move this import into the main import section.
		# Doing so causes InitEngine() above to fail when loading xul.dll.
		import gui.webconnect_protocol_handler
		wx.wc.RegisterProtocol("bpbible", gui.webconnect_protocol_handler.MasterProtocolHandler())
		dprint(MESSAGE, "XULRunner engine initialised")

	def SetWebPreferences(self):
		prefs = wx.wc.WebControl.preferences
		prefs['browser.dom.window.dump.enabled'] = True

	def FindXULRunnerVersion(self):
		"""Find the XULRunner version from the XULRunner platform.ini config file.

		This should be provided by XULRunner (and then wxWebConnect) through
		the nsIXULAppInfo API, but it seems this is only possible when xulrunner
		has been run from the command line and has an application.ini and
		XRE_Main() has been called.

		Since XRE_Main() is just looking up the value in the INI file,
		I figure it can't hurt too much to do the same here.
		"""
		xulrunner_ini_file = os.path.join(xulrunner_path, "platform.ini")
		config_parser = confparser.config()
		config_parser.read(xulrunner_ini_file)
		if config_parser.has_option("Build", "Milestone"):
			config.xulrunner_version = config_parser.get("Build", "Milestone")[0]
			dprint(MESSAGE,"XULRunner version is %s." % config.xulrunner_version)

def main():
	# convenience for when packaged (i.e. py2exe or py2app during dev on mac) 
	# - we can supply the name of a .py file and it will execfile it
	if len(sys.argv) > 1:
		if sys.argv[1].endswith(".py"):
			f = sys.argv.pop(1)
			return execfile(f, globals(), globals())

	inspection_imported = False
	try:
		from wx.lib.mixins.inspect import InspectionMixin
		inspection_imported = True
	except ImportError, e:
		try:
			from wx.lib.mixins.inspection import InspectionMixin
			inspection_imported = True
		except ImportError, e:
			pass
			
	if inspection_imported and is_debugging():
		class InspectableApp(MyApp, InspectionMixin):
			def OnInit(self):
				return_value = super(InspectableApp, self).OnInit()
				if not return_value:
					return False
				self.Init()
				return True

		app = InspectableApp(0)
	else:
		if is_debugging():
			dprint(WARNING, "Could not load inspection")

		app = MyApp(0)

	# Don't display warnings in distributed code unless it is in debugging mode.
	import warnings
	warnings.simplefilter("error" if is_debugging() else "ignore")
	
	dprint(MESSAGE, "App created")
	
	guiconfig.app = app
	while app.starting or app.restarting:
		if app.reload_restarting:
			import reload_util
			reload(reload_util)
			reload_util.reload_all()

		app.Initialize()
		app.MainLoop()

if __name__ == '__main__':
	main()

