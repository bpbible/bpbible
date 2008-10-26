"""
Handle errors as gracefully as possible.

This module will pop up an error message notification to the user with the
exception text and traceback if anything goes wrong.

Important: this module should be kept error free :)
"""
import sys
import time
import traceback
import wx

import hashlib

import config
from util.configmgr import config_manager
from util.i18n import N_
import re

from xrc.error_dialog_xrc import xrcErrorDialog

errors = config_manager.add_section("Errors")
errors.add_item("errors_to_ignore", [], item_type="pickle")

COLLAPSED_TEXTS = N_("<< &Details"), N_("&Details >>")
PANE = 2
fixed_width_re = re.compile("``(((?!``)(..?))*)``", re.DOTALL)

class ErrorDialog(xrcErrorDialog):
	def __init__(self, parent):
		super(ErrorDialog, self).__init__(parent)
		self.exception_text.BackgroundColour = \
			self.traceback_text.BackgroundColour = \
				self.panel.BackgroundColour

		self.details_button.Bind(wx.EVT_BUTTON, self.collapse_toggle)
		sys.excepthook = self.handle_error
		self._log = None
		self.exc_text = ""
		
	
	def install(self):
		sys.excepthook = self.handle_error

	def uninstall(self):
		sys.excepthook = sys.__excepthook__
	

	def write_to_log(self, text):
		"""
		Attempt to write errors to a log.
		If the log can't be created, fail silently, and don't try again
		"""
		if self._log is None:
			try:
				# append to the old file
				self._log = open(config.error_log, "a")
			except EnvironmentError, e:
				self._log = e

		if not isinstance(self._log, EnvironmentError):
			self._log.write(time.strftime("%Y/%m/%d %H:%M:%S "))
			self._log.write(text)
		
	def handle_error(self, type, value, tb):
		traceback_text = u"%s%s\n" % (self.traceback_text.Value,
			''.join(traceback.format_exception(type, value, tb)))

		self.exc_text = "%s%s\n%s: %s\n" % (
			self.exc_text, _("An error has occurred."), type.__name__, value)


		self.write_to_log(traceback_text)

		# if this exception is turned off, return immediately
		exception_id = self.get_exception_id(type, value, tb)
		if exception_id in errors["errors_to_ignore"]:
			self.write_to_log(_("Above exception was ignored") + "\n")
			return
	
		self.collapsed = False
		self.collapse_toggle(None)
		self.MinSize = self.Size = 350, 125
		self.hide_error.SetValue(False)
		
		# take out the `` which marks fixed width text
		# and remember where it is
		items = []
		def collect_font(match):
			items.append((
				# offset is 4 per previous item, plus 2 for the current one
				match.start(1) - (len(items) * 4 + 2),
				match.end(1) - (len(items) * 4 + 2)
			))
			return match.group(1)


		exception_text = fixed_width_re.sub(collect_font, self.exc_text)
	
		# append, don't replace
		# otherwise two errors within two event loops will leave only the last
		# one...
		self.exception_text.ChangeValue(exception_text)
		self.traceback_text.ChangeValue(traceback_text)

		fixed_width = wx.TextAttr(
			font=wx.Font(
				self.exception_text.Font.PointSize,
				wx.FONTFAMILY_TELETYPE, 
				wx.FONTSTYLE_NORMAL, 
				wx.FONTWEIGHT_NORMAL
			)
		)

		for start, end in items:
			self.exception_text.SetStyle(start, end, fixed_width)
		
		# There can be an error in here if showing it modal twice under linux
		if not self.IsShown():
			self.ShowModal()
		else: 
			return

		# ignore this exception if the box is checked
		if self.hide_error.IsChecked():
			errors["errors_to_ignore"].append(exception_id)

		# now put it back to empty ready for next time
		self.traceback_text.ChangeValue('')
		self.exception_text.ChangeValue('')
		self.exc_text = ""

		

	def collapse_toggle(self, event):
		self.collapsed = not self.collapsed
		
		self.panel.Sizer.Show(PANE, not self.collapsed)
		existing_size = self.panel.Sizer.GetItem(PANE).Size[1]

		if self.collapsed:
			self.Size = -1, self.Size[1] - existing_size
		else:
			self.Size = -1, self.Size[1] + existing_size
			
		self.details_button.Label = _(COLLAPSED_TEXTS[self.collapsed])
		self.panel.Sizer.Layout()
	
	def get_exception_id(self, type, value, tb):
		"""Get a unique identifier for a traceback.

		This is currently:
		filename
		linenumber
		position in code
		md5 hash of code 
		exception type - not exception as a problem may have more than one 
		exception text
		"""
		import hashlib
		
		# go to the bottom level of the traceback
		while tb.tb_next:
			tb = tb.tb_next

		frame = tb.tb_frame
		code = frame.f_code
		return (code.co_filename, tb.tb_lineno, tb.tb_lasti, 
			hashlib.md5(code.co_code).hexdigest(), str(type))
	
		

if __name__ == '__main__':
	import wx
	app = wx.App(0)
	d = ErrorDialog(None)
	def raise_error(q, x, y, z, w):
		def raise_error2(x):
			def raise_error3(y):
				def raise_error4(z):
					def raise_error5(w):
						return x*y*z*w/q
					return raise_error5(w)
				return raise_error4(z)
			return raise_error3(y)
		return raise_error2(x)

	
	raise_error(0, 1, 2, 3, 4)
