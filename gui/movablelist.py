import wx
from xrc.movablelist_xrc import *

class MovableListPanel(xrcMovableListPanel):
	def __init__(self, parent, gui_parent, copy_text=None):
		if copy_text is None:
			copy_text = _("Copy")

		self.parent = parent
	
		super(MovableListPanel, self).__init__(gui_parent)
		self.gui_templates.Bind(wx.EVT_LISTBOX, self.on_selection)

		self.move_up.Bind(wx.EVT_BUTTON, lambda x:self.move(-1))
		self.move_down.Bind(wx.EVT_BUTTON, lambda x:self.move(1))
		self.move_top.Bind(wx.EVT_BUTTON, lambda x:self.move_to(0))
		self.move_bottom.Bind(wx.EVT_BUTTON, 
			lambda x:self.move_to(len(self.templates)-1))
		

		self.gui_remove.Bind(wx.EVT_BUTTON, self.remove)
		self.gui_edit.Bind(wx.EVT_BUTTON, self.rename)
		self.gui_add.Bind(wx.EVT_BUTTON, self.copy)
		self.gui_add.Label = copy_text
		self.gui_remove.Bind(wx.EVT_UPDATE_UI, 
			lambda evt:evt.Enable(
				len(self.templates) > 1 and
				not self.template.readonly
			)
		)

		self.gui_edit.Bind(wx.EVT_UPDATE_UI, 
			lambda evt:evt.Enable(
				not self.template.readonly
			)
		)
			
	
	def init(self):
		self.fill_templates()

		self.gui_templates.SetSelection(0)
		self.change_template(0)
		
		
	def on_selection(self, event):
		self.change_template(self.gui_templates.GetSelection())
	

	def add_template(self, template):
		self.templates.append(template)
		
		self.fill_templates()

		ns = len(self.templates) - 1
		self.gui_templates.SetSelection(ns)
		self.change_template(ns)
		
		
	
	def delete_template(self, template):
		self.templates.remove(template)
		
		self.fill_templates()		

	def copy(self, event):
		selection = self.gui_templates.GetSelection()
		assert selection != -1
		
		name = self.parent.get_unique_name()
		if name:
			new_template = self.template.copy(name=name, 
											  readonly=False)

			self.add_template(new_template)

	def remove(self, event):
		if len(self.templates) == 1:
			return

		selection = self.gui_templates.GetSelection()
		assert selection != -1 and not self.template.readonly
		
		self.delete_template(self.template)
		if selection == len(self.templates):
			selection -= 1
			

		self.gui_templates.SetSelection(selection)

		
		self.change_template(selection)
	
	def move_to(self, item):
		selection = self.gui_templates.GetSelection()
		assert selection != -1

		t = self.templates
		t[selection], t[item] = t[item], t[selection]
		self.fill_templates()
		self.gui_templates.SetSelection(item)
	

	def move(self, direction):	
		selection = self.gui_templates.GetSelection()
		assert selection != -1
		
		item2 = selection + direction
		if item2 in (-1, len(self.templates)):
			# already top or bottom
			return
		
		self.move_to(item2)

	def fill_templates(self):
		self.gui_templates.Clear()
		for item in self.templates:
			self.gui_templates.Append(item.name)

	def change_template(self, selection):
		self.template = self.templates[selection]

		self.parent.on_template_change(selection)

	def rename(self, event):
		assert not self.template.readonly
		name = self.template.name
		name = self.parent.get_unique_name(name, self.template)
		if name:
			self.template.name = name
			self.fill_templates()

	@property
	def templates(self):
		return self.parent.templates
