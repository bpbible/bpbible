import os
from gui.movablelist import MovableListPanel
import wx
from backend.bibleinterface import biblemgr

# prior to wx 2.8.3, this is not there
if not hasattr(wx, "DD_DIR_MUST_EXIST"):
	wx.DD_DIR_MUST_EXIST = 0x0200

class PathItem(object):
	def __init__(self, path):
		self.name = path
		self.readonly = False
	
	def copy(self, name, readonly=False):
		return PathItem(name)

class PathManagerPanel(wx.Panel):
	def __init__(self, parent):
		super(PathManagerPanel, self).__init__(parent)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.panel = MovableListPanel(parent=self, gui_parent=self,
			copy_text=_("New"))
		
		sizer.Add(self.panel, 1, wx.GROW)
		s = wx.StdDialogButtonSizer()
		s.AddButton(wx.Button(self, id=wx.ID_OK))
		s.AddButton(wx.Button(self, id=wx.ID_CANCEL))
		
		s.Realize()
		sizer.Add(s, 0, wx.GROW)
		
		self.Sizer = sizer


		self.templates = self.read_templates()
		
		self.panel.init()
	
	def read_templates(self):
		return [PathItem(x) for x in biblemgr.load_paths()]
	
	def normalize_path(self, path):
		dir = os.getcwd()
		return os.path.normpath(path)
	
	def get_unique_name(self, name="", template=None, overwrite=False):
		if not name:
			name=os.getcwd()

		dlg = wx.DirDialog(self, _("Choose a directory:"),
						  style=wx.DD_DEFAULT_STYLE, defaultPath=name)

		# If the user selects OK, then we process the dialog's data.
		# This is done by getting the path data from the dialog - BEFORE
		# we destroy it. 
		ansa = dlg.ShowModal() 
		if ansa == wx.ID_OK:
			path = dlg.Path
			return path

	def on_template_change(self, selection): pass

	def save(self):
		busy = wx.BusyInfo(_("Reading books..."))
		biblemgr.set_new_paths([str(a.name) for a in self.templates])

class PathManager(wx.Dialog):
	def __init__(self, parent):
		super(PathManager, self).__init__(parent, title=_("Path manager"))
		s = wx.BoxSizer(wx.HORIZONTAL)
		self.pmp = PathManagerPanel(self)	
		s.Add(self.pmp, 1, wx.GROW)
		self.SetSizer(s)

	def ShowModal(self):
		ansa = super(PathManager, self).ShowModal()
		wx.SafeYield()
		if ansa == wx.ID_OK:
			self.pmp.save()

	
if __name__ == '__main__':
	app = wx.App(0)
	PathManager(None).ShowModal()
	
	
	wx.MessageBox(str([a.c_str() for a in biblemgr.modules]))
	wx.MessageBox(biblemgr.bible.GetReference("Gen 3:1-5"))
	
