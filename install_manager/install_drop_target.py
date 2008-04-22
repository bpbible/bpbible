import wx
from moduleinfo import ModuleInfo
from install_manager.install_module import ModuleInstallDialog
from install_manager import zipinstaller

class ModuleDropTarget(wx.FileDropTarget):
	def __init__(self, window):
		wx.FileDropTarget.__init__(self)
		self.window = window

	def OnDropFiles(self, x, y, filenames):
		if [file for file in filenames if not file.endswith(".zip")]:
			return False

		zipfiles = [
			zipinstaller.ZipInstaller(filename) for filename in	filenames
		]
		
		ModuleInstallDialog(self.window, zipfiles).ShowModal()
