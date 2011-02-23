import wx
from backend.bibleinterface import biblemgr
from moduleinfo import ModuleInfo
from install_manager.install_module import ModuleInstallDialog
from install_manager import zipinstaller
import traceback
from util.unicode import to_unicode, to_str

class ModuleDropTarget(wx.FileDropTarget):
	def __init__(self, window):
		wx.FileDropTarget.__init__(self)
		self.window = window

	def OnDropFiles(self, x, y, filenames):
		# use call after, otherwise we cannot go click on our explorer window
		# until message box is dismissed
		wx.CallAfter(self.handle_dropped_files, filenames)
	
	def handle_dropped_files(self, filenames):
		bad_files = []
		modules = []
		for filename in filenames:
			try:
				if not filename.endswith(".zip"):
					raise zipinstaller.InvalidModuleException(filename)

				modules.append(zipinstaller.find_zip_installer(filename))

			except zipinstaller.InvalidModuleException:
				bad_files.append(filename)

			except zipinstaller.BadMetadata, e:
				wx.MessageBox(e, _("Error"))
				return
			
			except Exception, e:
				wx.MessageBox(
					_("An error occurred while trying to read books. "
					"Please report this issue:\n"
					" 1. Press Ctrl-C to copy the error text\n"
					" 2. In the BPBible menu, select Help > Report a problem.\n"
					" 3. In the website that opens, click New Issue, and fill"
					" in the details\n"
					"The error given was:")  + "\n" + traceback.format_exc(), 
					_("Error reading books"))
				return
				
		
		if bad_files:
			if len(bad_files) > 1:
				message = _('The following files do not appear to be installable books:')
			else:
				message = _('The following file does not appear to be an installable book:')
			message += "\n"
			message += "\n".join(bad_files)
			wx.MessageBox(message, _("Error"))

		else:
			try:
				dlg = ModuleInstallDialog(self.window, modules)
				ansa = dlg.ShowModal()
				if ansa == wx.ID_OK:
					self.install_modules(modules, dlg.dest_dir)

				dlg.Destroy()
			except Exception, e:
				wx.MessageBox(
					_("An error occurred while installing modules.\n"
					"Please make sure that the directory exists, and that you "
					"have permission to write to the directory.\n"
					"The error given was:") + "\n" + traceback.format_exc(), 
					"Error installing modules")
				
	def install_modules(self, modules, dest_dir):
		def callback(progress, text):
			continuing, skip = p.Update(progress, text)
			wx.GetApp().Yield()
	
		for module in modules:
			p = wx.ProgressDialog(
				_("Extracting %s") % to_unicode(module.Description(), module),
				_("Preparing"), style=wx.PD_APP_MODAL)

			# make it nice and long so that the status text will fit in
			p.Size = (640, -1)

			p.Show()

			try:
				module.extract_zipfile(dest_dir, callback)
				
			finally:
				p.Hide()
				p.Destroy()			
		
		biblemgr.set_new_paths(path_changed=to_str(dest_dir))
