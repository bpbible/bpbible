import wx
import wx.combo
from util import osutils
from util.observerlist import ObserverList


class TreeCtrlComboPopup(wx.combo.ComboPopup):
	# overridden ComboPopup methods
	
	def Init(self):
		self.text = ""
		self.value = None
		self.curitem = None
		self.original = None

		
	def Create(self, parent):
		self.tree = wx.TreeCtrl(parent, style=wx.TR_HIDE_ROOT
								|wx.TR_HAS_BUTTONS
								|wx.TR_SINGLE
								|wx.TR_LINES_AT_ROOT
								|wx.SIMPLE_BORDER)
		root = self.tree.AddRoot("<hidden root>")
								
		self.tree.Bind(wx.EVT_MOTION, self.OnMotion)
		self.tree.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
		self.tree.Bind(wx.EVT_KEY_DOWN, self.on_key)
		self.GetCombo().Bind(wx.EVT_MOUSEWHEEL, self.mousewheel)
	
	def mousewheel(self, event):
		# assert event.WheelRotation
		
		if self.GetCombo().IsPopupShown():
			# if we are shown, scroll the tree.
			self.tree.ScrollLines(
				-event.WheelRotation/event.WheelDelta
				)
			return

		# otherwise go to next or previous item
		if event.WheelRotation > 0:
			self.go_up()
		elif event.WheelRotation < 0:
			self.go_down()

	def GetControl(self):
		return self.tree

	def GetStringValue(self):
		return self.text


	def OnPopup(self):
		value = self.get_value()
		if value:
			self.tree.EnsureVisible(value)
			self.tree.SelectItem(value)


	def SetStringValue(self, value):
		return

	def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
		return wx.Size(minWidth, min(200, maxHeight))
					   

	# helpers
	
	def AddItem(self, value, parent=None):
		if not parent:
			root = self.tree.GetRootItem()
			parent = root

		item = self.tree.AppendItem(parent, value)
		
		return item

	
	def OnMotion(self, evt):
		# have the selection follow the mouse, like in a real combobox
		item, flags = self.tree.HitTest(evt.GetPosition())
		if item and flags & wx.TREE_HITTEST_ONITEMLABEL:
			self.tree.SelectItem(item)
			self.curitem = item
		evt.Skip()


	def OnLeftDown(self, evt):
		# do the combobox selection
		item, flags = self.tree.HitTest(evt.GetPosition())
		if item and flags & wx.TREE_HITTEST_ONITEMLABEL:
			self.curitem = item
			self.set_value(item, selected_in_tree=True)
			self.Dismiss()

		evt.Skip()
	
	def OnComboKeyEvent(self, event):
		if event.KeyCode == wx.WXK_UP:
			self.go_up()
		elif event.KeyCode == wx.WXK_DOWN:
			self.go_down()
		elif not self.combo.readonly: 
			event.Skip()

		
	
	def on_key(self, event):
		if event.KeyCode in (wx.WXK_RETURN, wx.WXK_ESCAPE):
			
			if event.KeyCode == wx.WXK_RETURN:
				value = self.get_value()
				if value:
					self.combo.on_selected_in_tree(self.tree.GetItemText(value))
				
			self.Dismiss()
			return

		value = self.get_value()

		if not value or event.KeyCode not in (wx.WXK_UP, wx.WXK_DOWN,
			wx.WXK_LEFT, wx.WXK_RIGHT):
			event.Skip()
			return

		wx.CallAfter(self.handle_key, event.KeyCode)

	
	def handle_key(self, key_code):
		value = self.get_value()
	
		new_value = None

		expanded = self.tree.IsExpanded(value)
		has_children = self.tree.ItemHasChildren(value)
		
		if key_code == wx.WXK_UP:
			new_value = self.tree.GetPrevVisible(value)

		elif key_code == wx.WXK_DOWN:
			new_value = self.tree.GetNextVisible(value)
			

		elif key_code == wx.WXK_RIGHT:
			if has_children:
				if expanded:
					new_value = self.tree.GetNextVisible(value)
				else:
					self.tree.Expand(value)
					

		elif key_code == wx.WXK_LEFT:
			parent = self.tree.GetItemParent(value)
			root = self.tree.GetRootItem()
			
			if has_children and expanded:
				self.tree.Collapse(value)
			else:
				if root != parent:
					self.tree.Collapse(parent)
					new_value = parent
		
		if new_value:
			self.set_value(new_value)
		
	def set_value(self, value, selected_in_tree=False):
		self.value = value
		self.tree.SelectItem(self.value)
		#if not final:
		#	self.GetCombo().SetText(text)
		#else:
		text = self.combo.format_combo(value)
		self.text = text
		
		combo = self.GetCombo()
		combo.SetValueWithEvent(text, True)
		
		# it seems that readonly combo controls do not send an event. So we
		# send it ourselves.
		if combo.readonly:
			event = wx.CommandEvent(
				wx.wxEVT_COMMAND_TEXT_UPDATED, 
				combo.GetId()
			)

			event.SetString(text)
			combo.GetEventHandler().ProcessEvent(event)

		if selected_in_tree:
			combo.on_selected_in_tree(text)
		
		
	def get_value(self):
		# if we are not readonly, we may have to do some normalizing of user
		# input to get a tree item
		if not self.combo.readonly:
			self.value = self.combo.get_tree_item()

		return self.value
		
	def go_up(self):
		item = self.get_value()
		if not item:
			return

		prev = self.tree.GetPrevSibling(item)
		if prev:
			while self.tree.ItemHasChildren(prev):
				self.tree.Expand(prev)
				prev = self.tree.GetLastChild(prev)
		else:
			prev = self.tree.GetItemParent(item)
			if prev == self.tree.GetRootItem():
				return
	
		self.set_value(prev)
	
	def go_down(self):
		item = self.get_value()
		if not item:
			return

		# if we have children, expand them and go down
		if self.tree.ItemHasChildren(item):
			self.tree.Expand(item)
			item = self.tree.GetFirstChild(item)[0]
		
		# else if we have a sibling, go to it
		elif self.tree.GetNextSibling(item):
			item = self.tree.GetNextSibling(item)

		# else go up until we have a sibling and then select it
		else:
			root = self.tree.GetRootItem()
		
			while item != root and not self.tree.GetNextSibling(item):
				item = self.tree.GetItemParent(item)
			
			if item == root:
				return
			item = self.tree.GetNextSibling(item)
	
		self.set_value(item)
	
	def SetComboCtrl(self, combo):
		self.combo = combo
		combo.SetPopupControl(self)

class TreeCombo(wx.combo.ComboCtrl):
	def __init__(self, parent, style=wx.CB_READONLY):
		super(TreeCombo, self).__init__(parent, style=style)

		self.readonly = style & wx.CB_READONLY
		self.on_selected_in_tree = ObserverList()
		
		self.popup = TreeCtrlComboPopup()
		self.popup.SetComboCtrl(self)
		if not osutils.is_msw():
			self.Bind(wx.EVT_KEY_UP, self.on_char)

	def on_char(self, event):
		if event.KeyCode != wx.WXK_RETURN:
			event.Skip()
			return
		
		event = wx.CommandEvent(wx.wxEVT_COMMAND_TEXT_ENTER, 
								self.GetId())
		#event.SetString(text)
		self.GetEventHandler().ProcessEvent(event)
		
		
		#self.BibleRefEnter()
			
		
		
		
	
	def AddItem(self, item, parent=None):
		return self.popup.AddItem(item, parent)
	
	def set_value(self, item):
		self.popup.set_value(item)
	
	def format_combo(self, item):
		return self.tree.GetItemText(item)
		
	
	@property
	def tree(self):
		return self.popup.tree
	
class LazyTreeCombo(TreeCombo):
	def __init__(self, parent, style):
		super(LazyTreeCombo, self).__init__(parent, style=style)
		self.root = self.tree.GetRootItem()
		self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.Expand)
		self.Bind(wx.EVT_TEXT, self.OnChoice)

	def AddItems(self, item):
		data, hasExpanded = self.tree.GetPyData(item)
		if hasExpanded: return
		self.tree.SetPyData(item, (data, True))
		for child in data:
			node = self.tree.AppendItem(item, unicode(child))
			# set data to key, hasexpanded
			self.tree.SetPyData(node, (child, False))
			if(self.has_children(node)):
				self.tree.SetItemHasChildren(node)

	def Expand(self, event):
		item = event.GetItem()
		self.AddItems(item)
		
	def OnChoice(self, event=None):
		item = self.popup.value
		if not item: return


		event = wx.CommandEvent(
			wx.wxEVT_COMMAND_COMBOBOX_SELECTED, 
			self.GetId()
		)

		event.SetString(self.tree.GetItemText(item))
		self.GetEventHandler().ProcessEvent(event)

		
		#self.frame.SetReference(self.tree.GetPyData(item)[0])
		

	def set_value(self, item):
		super(LazyTreeCombo, self).set_value(item)
		self.OnChoice()
	
	def get_data(self, item):
		return self.tree.GetPyData(item)[0]
		






if __name__ == '__main__':
	app = wx.App(0)
	d = wx.Dialog(None)
	popup = TreeCombo(d)
	for i in range(5):
		item = popup.AddItem('Item %d' % (i+1))
		for j in range(5):
			item2 = popup.AddItem('Subitem %d-%d' % (i+1, j+1), parent=item)
			for k in range(5):
				popup.AddItem('Subsubitem %d-%d-%d' % (i+1, j+1, k+1), parent=item2)
			
	
	popup.set_value(popup.tree.GetFirstChild(popup.tree.GetRootItem())[0])
	
	d.ShowModal()
