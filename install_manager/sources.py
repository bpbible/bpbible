import wx
from xrc.installmgr_sources_xrc import xrcSourcesDialog
from gui.guiutil import bmp
from util.observerlist import ObserverList
from swlib.installsource import InstallSource

class StatusReporter(object):
	def preStatus(totalBytes, completedBytes, message):
		"""Messages before stages of a batch download"""

	def statusUpdate(dtTotal, dlNow):
		"""Frequently called throughout a download, to report status"""
	
class SourcesModel(object):	
	def __init__(self):
		self.sources = []
		self.current_source = None
		self.on_source_added = ObserverList()
		self.on_caption_changed = ObserverList()
		self.on_url_changed = ObserverList()
		self.on_change_item = ObserverList()
		self.on_source_deleted = ObserverList()

	def add_source(self, caption, url):
		install_source = InstallSource()
		install_source.url = url
		install_source.caption = caption
		self.sources.append(install_source)
		self.on_source_added(install_source)
		self.set_current_item(len(self.sources) - 1)

	def set_caption(self, caption):
		self.current_source.caption = caption
		self.on_caption_changed(self.current_source)
	
	def set_url(self, url):
		self.current_source.url = url
		self.on_url_changed(self.current_source)
		
	
	def set_current_item(self, idx):
		if idx == -1:
			self.current_source = None
		else:
			self.current_source = self.sources[idx]
		self.on_change_item(self.current_source, idx)
		
	
	def delete_item(self):
		idx = self.sources.index(self.current_source)
		del self.sources[idx]
		self.on_source_deleted(self.current_source, idx)
		idx = min(len(self.sources) - 1, idx)
		self.set_current_item(idx)
	
	def save(self):
		print [item.getConfEnt() for item in self.sources]
	
class SourcesDialog(xrcSourcesDialog):
	def __init__(self, parent):
		super(SourcesDialog, self).__init__(parent)
		self.sources = SourcesModel()

		self.toolbar = wx.ToolBar(self.toolbar_panel, 
			style=wx.TB_FLAT |
				  wx.TB_HORZ_TEXT |
				  wx.TB_NODIVIDER 
		)
		self.toolbar.SetToolBitmapSize((16, 16))
		
		
		self.gui_add = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Add", bmp("application_form_add.png", ),
			shortHelp="Add a new install source"
		)
		
		self.gui_remove = self.toolbar.AddLabelTool(wx.ID_ANY,  
			"Delete", bmp("application_form_delete.png", ),
			shortHelp="Remove this install source"
		)
		
		self.toolbar.Bind(wx.EVT_UPDATE_UI, lambda evt:
			evt.Enable(self.sources_list.GetSelection() != wx.NOT_FOUND),
			self.gui_remove
		)

		self.Bind(wx.EVT_CLOSE, lambda evt: (self.sources.save(), evt.Skip()))

		self.source_name.Bind(wx.EVT_TEXT, self.change_item_caption)

		self.source_location.Bind(wx.EVT_TEXT, 
			lambda evt: self.sources.set_url(self.source_location.Value))
		
		self.sources_list.Bind(wx.EVT_LISTBOX, self.change_item)

		self.toolbar.Bind(wx.EVT_TOOL, self.add_item, self.gui_add)
		self.toolbar.Bind(wx.EVT_TOOL, self.remove_item, self.gui_remove)
		

		self.toolbar.Realize()
		self.toolbar.MinSize = self.toolbar.Size
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(self.toolbar, 1, wx.GROW)
		self.toolbar_panel.SetSizer(sizer)
		self.SetSize((550, 320))
		self.update_ui()

		self.sources.on_change_item += self.on_change_item
		self.sources.on_source_added += self.on_add_item
		self.sources.on_source_deleted += self.on_delete_item

	def add_item(self, event=None):
		self.sources.add_source("CrossWire", "ftp.crosswire.org/pub/sword/raw")

	def remove_item(self, event=None):
		self.sources.delete_item()

	def change_item(self, event=None):
		self.sources.set_current_item(self.sources_list.Selection)

	def on_add_item(self, item):
		self.sources_list.Append(item.caption)
		self.update_ui()
	
	def on_delete_item(self, item, idx):
		self.sources_list.Delete(idx)
		self.update_ui()
	
	def on_change_item(self, item, idx):
		if item is not None:
			self.sources_list.SetSelection(idx)
			self.source_name.ChangeValue(item.caption)
			self.source_location.ChangeValue(item.url)
		else:
			self.source_name.ChangeValue("")
			self.source_location.ChangeValue("")
			
		self.update_ui()
	
	def change_item_caption(self, event=None):
		self.sources.set_caption(self.source_name.Value)
		self.on_change_item_caption(self.sources.current_source)
	
	def on_change_item_caption(self, item):
		self.sources_list.SetString(self.sources_list.Selection, item.caption)
	
	def update_ui(self):
		has_selection = self.sources_list.GetSelection() != wx.NOT_FOUND
		self.properties_panel.Enable(has_selection)

if __name__ == '__main__':
	a = wx.App(0)
	f = SourcesDialog(None)
	f.ShowModal()
