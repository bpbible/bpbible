import wx
from moduleinfo import ModuleInfo
from install_manager.install_module import ModuleInstallDialog
from install_manager import zipinstaller

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

				modules.append(zipinstaller.ZipInstaller(filename))
			
			except zipinstaller.InvalidModuleException:
				bad_files.append(filename)

			except zipinstaller.BadMetadata, e:
				wx.MessageBox(e, "Error")
				return
		
		if bad_files:
			if len(bad_files) > 1:
				message = 'The following files do not appear to be installable books:\n'
			else:
				message = 'The following file does not appear to be an installable book:\n'
			message += "\n".join(bad_files)
			wx.MessageBox(message, "Error")

		else:
			ModuleInstallDialog(self.window, modules).ShowModal()
				
	
