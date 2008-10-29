import sys
import string
import wx
import os

from xrc.templatemanager_xrc import *
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate, Template
import config
import guiconfig
from wx import stc
from gui.movablelist import MovableListPanel
from gui import guiutil
#import wx.lib.mixins.listctrl  as  listmix
import cPickle as pickle

from util.debug import *

PREVIEW_VERSES = "Genesis 1:1-2"
default_templates = [
	Template(name="Default", 
		headings="<h5>$heading</h5>",
		header="",
		footer="$range ($description)",
		body="$versenumber $text "),

	Template(name="Verse per line with reference", 
		headings="<h5>$heading</h5>",
		header="",
		footer="",
		body="$reference $text<br>"),

	Template(name="Verse per Line with short reference", 
		headings="<h5>$heading</h5>",
		header="",
		footer="",
		body="<small>$bookabbrev $chapternumber:$versenumber</small> $text<br>"
	),

	Template(name="Verse with verse number per line", 
		headings="<h5>$heading</h5>",
		header="$range<br>",
		footer="",
		body="$versenumber $text<br>"),
		
	Template(name="Text with range at start", 
		headings="<h5>$heading</h5>",
		header="$range<br>",
		footer="",
		body="$text "),
		
	Template(name="Text with range at end", 
		headings="<h5>$heading</h5>",
		header="",
		footer="$range<br>",
		body="$versenumber $text<br>"),

]



class AutoCompleteList(wx.ListCtrl):#, listmix.ListCtrlAutoWidthMixin):
	def __init__(self, parent, style=0):
		super(AutoCompleteList, self).__init__(parent, style=style)
		self.selection = None
		self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.selected)
		self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.deselected)

	def selected(self, event):
		self.selection = event.GetItem()

	def deselected(self, event):
		self.selection = None

	def Populate(self, cols, items):
		# for normal, simple columns, you can add them like this:
		for idx, a in enumerate(cols):
			self.InsertColumn(idx, a)

		for idx, t in enumerate(items):
			#key, data = t
			index = self.InsertStringItem(sys.maxint, t[0])
			for ind, item in enumerate(t):
				self.SetStringItem(index, ind, item)
			#self.SetItemData(index, key)

		self.width = 0;
		for a in range(len(items[0])):
			self.SetColumnWidth(a, wx.LIST_AUTOSIZE)
			self.SetColumnWidth(a, self.GetColumnWidth(a)+5)
			self.width += self.GetColumnWidth(a)
		self.width += (self.Size[0] - self.ClientSize[0])			
		#self.SetColumnWidth(2, 100)

class AutoCompleteTextBox(object):#(wx.TextCtrl):
	splitting = list(string.whitespace + string.punctuation)
	splitting.remove("$")
	splitting = "".join(splitting)

	def split(self, word):
		for item in self.splitting:
			word = word.replace(item, " ")

		# use $ to start a new split, but *don't* remove it
		r = []
		for item in word.split(" "):
			items = item.split("$")
			if items:
				r.append(items[0])
				for item2 in items[1:]:
					r.append("$"+item2)

		return r

	def __init__(self, textbox, update_func, items = {}):
		#super(AutoCompleteTextBox, self).__init__(parent)
		self.update_func = update_func
		self.textbox = textbox
		self.autocompleting=False
		self.dialog = None
		
		self.popup = wx.PopupWindow(guiconfig.mainfrm)
		self.list = AutoCompleteList(self.popup, 
			style=wx.LC_SINGLE_SEL | wx.LC_REPORT | 
				wx.LC_SORT_ASCENDING | wx.LC_NO_HEADER|wx.SUNKEN_BORDER)

		self.popup.Hide()
		self.textbox.Bind(stc.EVT_STC_MODIFIED, self.OnText)
		self.textbox.Bind(wx.EVT_KILL_FOCUS, self.KillFocus)
		self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.Select)
		
		


		self.textbox.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
		self.SetItems(items.copy())
	
	def KillFocus(self, event):
		if wx.Window.FindFocus() not in (self.list, self.popup, self.textbox):
			self.DismissPopup()
		event.Skip()

	
	def set_text(self, text):
		em = self.textbox.GetModEventMask()
		self.textbox.SetModEventMask(0)

		self.textbox.SetText(text)

		# turn events back on
		self.textbox.SetModEventMask(em)
	
	def OnText(self, event):
		event.Skip()
		self.update_func()
		mod = event.GetModificationType()
		if mod & stc.STC_MOD_INSERTTEXT: pass
		elif mod&stc.STC_MOD_DELETETEXT and self.autocompleting: pass
		else:
			event.Skip()
			return

		point = self.textbox.PointFromPosition(self.textbox.GetCurrentPos())
		point = self.textbox.ClientToScreen(point)		
		if wx.Platform == '__WXMSW__' and guiutil.hasNativePopupWindows:
			point = guiconfig.mainfrm.ScreenToClient(point)

		linetext, column = self.textbox.GetCurLine()

		if not linetext: return
		
		# these need to be offset by one. Presumably update of caret hasn't 
		# yet occurred
		lt = linetext[:column+1]

		#for item in splitting
		words = self.split(linetext[:column+1])

		if not words:
			return
		
		#if we have entered whitespace, kill thing
		if lt[-1] in self.splitting:
			if self.autocompleting: 
				self.DismissPopup()
			return
			
		word = words[-1]

		if word.strip(self.splitting)[0]=="$":
			#if not self.autocompleting:
			self.DisplayPopup(word.strip(self.splitting), point)
		elif self.autocompleting:
			self.DismissPopup()

	def DisplayPopup(self, word, point):
		if not self.autocompleting:
			x, y = point
			y += 6 + self.textbox.GetCharHeight()
			self.autocompleting = True
			self.popup.SetPosition((x,y))

			self.list.Size=(self.list.width,-1)
			ratio = (float(self.list.GetItemCount()) /
					float(self.list.GetCountPerPage()))
			
			self.list.Size = (-1, int(self.list.BestSize[1]*ratio))
			self.popup.Size=(self.list.width,self.list.Size[-1])
			self.popup.Show()

		sel = 0 #self.list.GetCount()
		length = len(self.terms.keys())
		for idx, a in enumerate(reversed(sorted(self.terms.keys()))):
			if a<word:
				sel = min(length - (idx), len(self.terms.keys()) - 1)
				break
		self.list.Select(sel)
		if self.dialog:
			self.dialog.SetEscapeId(wx.ID_NONE)
		
		

	def OnKeyPressed(self, event):
		keycode = event.GetKeyCode()
		if keycode == wx.WXK_TAB and not event.ControlDown():
			parent = self.textbox.Parent
			while parent:
				if not parent.Parent:
					break
				parent = parent.Parent
			#event = event.Clone()
			#event.SetEventObject(parent)
			#parent.GetEventHandler().ProcessEvent(event)
			direction = wx.NavigationKeyEvent.IsForward
			if event.ShiftDown():
				direction = wx.NavigationKeyEvent.IsBackward
			self.textbox.Navigate(direction)
			return
		if not self.autocompleting or not keycode in \
				(wx.WXK_UP, wx.WXK_DOWN, wx.WXK_ESCAPE, wx.WXK_RETURN,):

			if self.autocompleting and keycode in (wx.WXK_LEFT, wx.WXK_RIGHT):
				if keycode == wx.WXK_LEFT:
					text, col = self.textbox.GetCurLine()
					if col-1 < 0 or text[col-1] in self.splitting:
						self.DismissPopup()
				if keycode == wx.WXK_RIGHT:
					text, col = self.textbox.GetCurLine()
					if col >= len(text) or text[col] in self.splitting:
						self.DismissPopup()
				
			event.Skip()
				
			return
		if keycode == wx.WXK_ESCAPE:
			self.DismissPopup()
		if keycode == wx.WXK_UP:
			selection = self.list.GetFirstSelected()
			selection -= 1
			selection = max(0, selection)
			self.list.Select(selection)
		if keycode == wx.WXK_DOWN:
			selection = self.list.GetFirstSelected()
			selection += 1
			selection = min(len(self.terms) -1, selection)
			self.list.Select(selection)
		if keycode in (wx.WXK_RETURN, wx.WXK_TAB):
			if self.list.GetFirstSelected() == -1:
				event.Skip()
				return
			self.Select()

	
	def Select(self, event=None):
		item = self.list.GetItem(self.list.GetFirstSelected(), 0).GetText()
		pos = self.textbox.GetCurrentPos()
		line_text, column = self.textbox.GetCurLine()
		text = self.split(line_text[:column])[-1]
		#text = text.strip(self.splitting)
		rest = item[len(text):] + " "
		wx.CallAfter(self.InsertText, item, pos - len(text), pos)

		self.DismissPopup()
	
	def InsertText(self, text, text_pos_start, text_pos_end):
		#turn off all events
		em = self.textbox.GetModEventMask()
		self.textbox.SetModEventMask(0)

		#insert the text
		self.textbox.SetTargetStart(text_pos_start)
		self.textbox.SetTargetEnd(text_pos_end)
		self.textbox.ReplaceTarget(text)
		difference = text_pos_end - text_pos_start
		diff = len(text) - difference
		self.textbox.GotoPos(text_pos_end + diff)

		# turn events back on
		self.textbox.SetModEventMask(em)
		self.update_func()
		

	def DismissPopup(self):
		self.autocompleting=False
		self.popup.Hide()
		if self.dialog:
			self.dialog.SetEscapeId(wx.ID_CANCEL)
		

	def SetItems(self, items):
		for item in items.keys():
			items["$" + item] = items[item]
			del items[item]
		self.terms=items
		self.list.Populate(("Type", "Description") , list(items.iteritems()))
		return

class TemplatePanel(xrcTemplatePanel):
	def __init__(self, parent, values={}, headings=False):
		super(TemplatePanel, self).__init__(parent)
		fields = "header body footer"

		if headings:
			fields += " headings"


		self.fields = []

		template_options = biblemgr.bible.get_template_options()

		for field in fields.split():
			item = getattr(self, field)
			#setattr(self, field, item)
			#item.Bind(stc.EVT_STC_CHANGE, self.Update)
			item.field = field
			if field in values:
				item.set_text(values[field])

			item.autocomplete = AutoCompleteTextBox(item, self.Update,
				template_options[field])

			dialog = guiutil.toplevel_parent(self)
			if isinstance(dialog, wx.Dialog):
				item.autocomplete.dialog = dialog
			

			self.fields.append(item)

		if not headings:
			s = self.headings.ContainingSizer
			s.Clear(True)
			cs = s.ContainingWindow.Sizer
			cs.Remove(s)
			cs.Layout()
			
template_file = config.data_path + "templates.conf"

class TemplateManager(xrcTemplateManager):
	def __init__(self, parent):
		super(TemplateManager, self).__init__(parent)
		self.template_panel = TemplatePanel(self.tp_holder)
		self.movable_list = MovableListPanel(self, self.movable_list_holder)

		self.tp_holder.Sizer.Add(self.template_panel, 1, wx.GROW|wx.ALL,
			border=5)
		self.movable_list_holder.Sizer.Add(self.movable_list, 1, 
			wx.GROW|wx.ALL,	border=5)
			
		self.tp_holder.Fit()
		self.movable_list_holder.Fit()
		self.Fit()
		self.MinSize = self.Size
		

		for a in [wx.EVT_KILL_FOCUS,]:#, stc.EVT_STC_MODIFIED]:
			for item in self.template_panel.fields:
				item.Bind(a, self.change_field)
		
		
		self.movable_list.gui_templates.Bind(wx.EVT_LISTBOX_DCLICK, 
			lambda x:self.EndModal(wx.ID_OK))
			
		self.read_templates()
		self.movable_list.init()
		
	
	def template_exists(self, name, excluded=None):
		for item in self.templates:
			if item is not excluded and item.name == name:
				return True
		return False
	
	def save(self):
		if not os.path.exists(config.data_path):
			os.makedirs(config.data_path)
	
		f = open(template_file, "wb")
		pickle.dump(self.templates, f)
		
		
	
	def change_field(self, event):
		event.Skip()
		if self.movable_list.template.readonly: return
		assert not self.movable_list.template.readonly
	
		#for item in self.fields:
		item = event.EventObject

		self.movable_list.template[item.field] = item.Text
		self.update_preview()
			
	@property
	def template(self):
		"""Delegate this to the movable list"""
		return self.movable_list.template

	def get_template(self, name):
		for item in self.templates:
			if item.name == name:
				return item
		#assert False, "Template '%s' not found" % name
			
	def get_unique_name(self, name="", template=None, overwrite=False):
		while True:
			te = wx.TextEntryDialog(self, "New name for template...", 
				"Rename", defaultValue=name)
			if te.ShowModal() == wx.ID_OK:
				name = te.GetValue()
				if overwrite and self.template_exists(name):
					if self.get_template(name).readonly:
						wx.MessageBox(_("Template '%s' is read only. Try a "
						"different name.") % name, _("Error"), 
							wx.OK|wx.ICON_ERROR)
					else:
						ansa = wx.MessageBox(
						_("Template '%s' already exists. Overwrite?") % name,
						_("Overwrite?") , wx.YES_NO|wx.ICON_QUESTION)
						if ansa == wx.YES:
							return name
				elif self.template_exists(name, template):
					wx.MessageBox(
					_("Template name is already in use. Try a different name."),
					_("Error"), wx.OK|wx.ICON_ERROR)		
												
				else: 
					return name
					
			else:
				return
			
	
	
	def read_templates(self):
		try:
			f = open(template_file, "rb")
			self.templates = pickle.load(f)
		except Exception, e:
			dprint(WARNING, "Template loading exception", e)
			#try:
			#	import traceback
			#	traceback.print_exc()
			#except:
			#	pass
			self.templates = default_templates[:]
	

	
	def on_template_change(self, selection):
		enabled = not self.movable_list.template.readonly
		
		for item in self.template_panel.fields:
			item.set_text(self.movable_list.template[item.field])

			# make it a disabled field if necessary
			item.SetReadOnly(not enabled)

			# give it the right colour
			if enabled:
				colour, text_colour = guiconfig.get_window_colours()
			
			
			else:
				colour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
				text_colour = wx.SystemSettings.GetColour(
								wx.SYS_COLOUR_GRAYTEXT
							)

			for s in stc.STC_STYLE_DEFAULT, 0:
				item.StyleSetBackground(s, colour)
				item.StyleSetForeground(s, text_colour)

			item.SetCaretForeground(text_colour)

		self.update_preview()
			
	
	
	def update_preview(self):
		biblemgr.bible.templatelist.append(self.movable_list.template)
		data = biblemgr.bible.GetReference(PREVIEW_VERSES)
		biblemgr.bible.templatelist.pop()

		if data is None:
			data = config.MODULE_MISSING_STRING
		
		self.gui_preview.book = biblemgr.bible
		self.gui_preview.SetPage(data)
		
	

	def ShowModal(self):
		try:
			return super(TemplateManager, self).ShowModal()
		finally:
			self.save()
	
	def return_template(self, template_name):
		if not self.template_exists(template_name):
			return None
		#name = self.get_unique_name(name, self.movable_list.template)
	
		return self.get_template(template_number)
	
	def save_template(self, template):
		name = self.get_unique_name(template.name, overwrite=True)
		if not name:
			return False

		template.name = name
		
		if self.template_exists(name):
			for id, item in enumerate(self.templates):
				if item.name == name:
					# if we are readonly, we should have been stopped earlier
					assert not item.readonly

					self.templates[id] = template
		else:
			self.movable_list.add_template(template)

		return True
			#self.templates.append(template)

		#self.fill_templates()
	
	def change_template(self, selection):
		self.movable_list.change_template(selection)
	
if __name__ == '__main__':
	app=wx.App(0)
	guiconfig.mainfrm = wx.Frame(None)
	guiconfig.mainfrm.lost_focus = True
	tm = TemplateManager(guiconfig.mainfrm)
	tm.ShowModal()


