import wx
from util.debug import dprint, WARNING

class MultiChoiceDialog(wx.MultiChoiceDialog):
	def __init__(self, *args, **kwargs):
		super(MultiChoiceDialog, self).__init__(*args, **kwargs)
		for item in self.Children:
			if isinstance(item, wx.CheckListBox):
				self.Bind(wx.EVT_KEY_UP,  self.on_char)
				item.Bind(wx.EVT_KEY_UP,  self.on_char)
				
				break
		else:
			dprint(WARNING, "ListBox not found in MultiChoiceDialog")
			item = None
		
		self.list_box = item
	
	def ShowModal(self):
		if self.list_box:
			# Usual MultiChoiceDialog doesn't resize properly.
			# Set the list box to grab all available space
			sizer = self.list_box.ContainingSizer
			sizer_item = sizer.GetItem(self.list_box)
			sizer_item.Proportion = 1
		

		return super(MultiChoiceDialog, self).ShowModal()
	
	def on_char(self, event):
		if event.KeyCode == ord("A") and event.ControlDown():
			self.select_all(True)

		elif event.KeyCode == ord("B") and event.ControlDown():
			self.select_all(False)

		else:
			event.Skip()
	
	def select_all(self, to):
		if not self.list_box: 
			return

		for item in range(self.list_box.Count):
			self.list_box.Check(item, to)
		
