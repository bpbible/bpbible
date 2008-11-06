import wx
from util.debug import dprint, WARNING

class Separator:
	pass

class MenuItem(object):
	def __init__(self, text, action, doc=None, enabled=lambda:True,
			update_text=lambda:None, update_ui=None, accelerator=None,
			id=wx.ID_ANY, font=None):
		self.text = text
		self.action = action
		#self.window = window

		if doc is None:
			self.doc = action.__doc__
			if self.doc is None:
				dprint(WARNING, "No description for menu item", text)
				self.doc = ""
		else:
			self.doc = doc
		
		self.enabled = enabled
		self.update_text = update_text
		self.update_ui = update_ui
		self.accelerator = accelerator
		self.id = id
		self.font = font
	
	def create_item(self, window, menu, pos=None, is_popup=False):
		if pos is None:
			pos = menu.GetMenuItemCount()

		text = self.text
		if self.accelerator and not is_popup:
			text += "\t%s"%self.accelerator
		item = menu.Append(self.id, text, self.doc)
		if self.font is not None:
			item.SetFont(self.font)

		if self.action:
			window.Bind(wx.EVT_MENU, lambda evt:self.action(), item)

		window.Bind(wx.EVT_UPDATE_UI, self.on_update_ui, item)

		return item
		
	
	def on_update_ui(self, event):
		if self.update_ui:
			return self.update_ui(event)
			
		event.Enable(self.enabled())
		text = self.update_text()
		if text is not None:
			event.SetText(text)
