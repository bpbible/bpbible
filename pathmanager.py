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
		#self.path = path
	
	def copy(self, name, readonly=False):
		return PathItem(name)

class PathManager(wx.Dialog):
	def __init__(self, parent):
		super(PathManager, self).__init__(parent, title="Path manager")
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.panel = MovableListPanel(parent=self, gui_parent=self,
			copy_text="New")
		
		sizer.Add(self.panel, 1, wx.GROW)
		b = wx.Button(self, id=wx.ID_OK)
		#panel2 = wx.Panel(self)
		s = wx.StdDialogButtonSizer()
		s.AddButton(b)
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

		dlg = wx.DirDialog(self, "Choose a directory:",
						  style=wx.DD_DEFAULT_STYLE, defaultPath=name)#|wx.DD_DIR_MUST_EXIST)

		# If the user selects OK, then we process the dialog's data.
		# This is done by getting the path data from the dialog - BEFORE
		# we destroy it. 
		ansa = dlg.ShowModal() 
		if ansa == wx.ID_OK:
			path = dlg.Path
			return path#and not self.path_exists(:
			#self.log.WriteText('You selected: %s\n' % dlg.GetPath())

	def on_template_change(self, selection): pass

	def ShowModal(self):
		ansa = super(PathManager, self).ShowModal()
		wx.SafeYield()
		if ansa == wx.ID_OK:
			self.save()
	
	def save(self):
		busy = wx.BusyInfo("Reading modules...")
		biblemgr.set_new_paths([str(a.name) for a in self.templates])

if __name__ == '__main__':
	app = wx.App(0)
	PathManager(None).ShowModal()
	wx.MessageBox(str([a.c_str() for a in biblemgr.mgr.getModules()]))
	wx.MessageBox(biblemgr.bible.GetReference("Gen 3:1-5"))
	
