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
from util.i18n import _

from xrc.error_dialog_xrc import xrcErrorDialog

errors = config_manager.add_section("Errors")
errors.add_item("errors_to_ignore", [], item_type="pickle")

COLLAPSED_TEXTS = _("<< &Details"), _("&Details >>")
PANE = 2

class ErrorDialog(xrcErrorDialog):
	def __init__(self, parent):
		super(ErrorDialog, self).__init__(parent)
		self.exception_text.BackgroundColour = \
			self.traceback_text.BackgroundColour = \
				self.panel.BackgroundColour

		self.details_button.Bind(wx.EVT_BUTTON, self.collapse_toggle)
		sys.excepthook = self.handle_error
		self._log = None
		
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
		traceback_text = _("%s%s\n") % (self.traceback_text.Value,
			''.join(traceback.format_exception(type, value, tb)))

		exception_text = _("%sAn error has occurred.\n%s: %s\n") % (
			self.exception_text.Value, type.__name__, value)

		self.write_to_log(traceback_text)

		# if this exception is turned off, return immediately
		exception_id = self.get_exception_id(type, value, tb)
		if exception_id in errors["errors_to_ignore"]:
			self.write_to_log(_("Above exception was ignored\n"))
			return
	
		self.collapsed = False
		self.collapse_toggle(None)
		self.MinSize = self.Size = 350, 125
		self.hide_error.SetValue(False)
		
		# append, don't replace
		# otherwise two errors within two event loops will leave only the last
		# one...
		self.exception_text.ChangeValue(exception_text)
		self.traceback_text.ChangeValue(traceback_text)
		
		self.ShowModal()

		# ignore this exception if the box is checked
		if self.hide_error.IsChecked():
			errors["errors_to_ignore"].append(exception_id)

		# now put it back to empty ready for next time
		self.traceback_text.ChangeValue('')
		self.exception_text.ChangeValue('')
		

	def collapse_toggle(self, event):
		self.collapsed = not self.collapsed
		
		self.panel.Sizer.Show(PANE, not self.collapsed)
		existing_size = self.panel.Sizer.GetItem(PANE).Size[1]

		if self.collapsed:
			self.Size = -1, self.Size[1] - existing_size
		else:
			self.Size = -1, self.Size[1] + existing_size
			
		self.details_button.Label = COLLAPSED_TEXTS[self.collapsed]
	
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
