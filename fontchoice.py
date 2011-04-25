import wx
from util.unicode import to_str, to_unicode
from backend.bibleinterface import biblemgr
from xrc.fontchoice_xrc import *
import guiconfig
import config
from module_tree import LanguageModuleTree
from displayframe import DisplayFrameXRC
from util import osutils
from gui import fonts
from gui.fonts import font_settings
from swlib import pysw

DefaultFont = object()

	
class FontChoiceDialog(xrcFontChoiceDialog):
	def __init__(self, parent):
		super(FontChoiceDialog, self).__init__(parent)
		self.font_face.Bind(wx.EVT_CHOICE, self.on_font_changed)
		self.font_size.Bind(wx.EVT_SPINCTRL, self.on_font_changed)
		self.gui_use_default_font.Bind(wx.EVT_CHECKBOX, 
			lambda evt: self.on_use_default_font(evt.Checked()))
		self.gui_use_in_ui.Bind(wx.EVT_CHECKBOX, self.on_font_changed)
			
		
		self.tree = FontTree(self.filterable_tree_holder)
		self.tree.on_module_choice += self.on_module_choice
		self.tree.on_category_choice += self.on_category_choice
		self.filterable_tree_holder.Sizer.Add(self.tree, 1, wx.GROW)
		self.filterable_tree_holder.Layout()
		names = wx.FontEnumerator().GetFacenames()
		names.sort()
		self.font_face.Clear()
		self.font_face.AppendItems(names)
		self.preview.handle_links = False

		#if size is None:
		#	size = max(wx.NORMAL_FONT.PointSize, 10)
		#
		#if font is None:
		#	font = wx.Font(size, wx.SWISS, wx.NORMAL, wx.NORMAL, False);
		#
		#	font = font.FaceName
		
		self.on_default_choice()
	
	def on_use_default_font(self, checked):
		if checked:
			if self.tree_item == DefaultFont:
				font_settings["default_fonts"] = None
			else:
				if self.item_to_set in self.item_section:
					del self.item_section[self.item_to_set]
			
			font, size, use_in_gui = fonts.get_default_font(self.tree_item)
			self.set_font_params(font, size, use_in_gui)

	def set_font_params(self, font, size, use_in_gui):
		if not self.font_face.SetStringSelection(font):
			self.font_face.SetSelection(0)

		self.font_size.SetValue(size)
		self.gui_use_in_ui.SetValue(use_in_gui)
		self.update_preview()
		

	def on_font_changed(self, event):
		font, size = self.font_face.StringSelection, self.font_size.Value
		gui = self.gui_use_in_ui.Value
		self.gui_use_default_font.SetValue(False)
		self.item_section[self.item_to_set] = font, size, gui
		self.update_preview()

	def on_item_choice(self, data, font_details_getter):
		self.preview.mod = self.mod
		self.font_details_getter = font_details_getter
		default, (font, size, use_in_gui) = font_details_getter(data)
		self.set_font_params(font, size, use_in_gui)
		self.tree_item = data
		
		self.on_use_default_font(default)
		
		self.gui_use_default_font.SetValue(default)
		self.gui_use_default_font.ContainingSizer.Show(0, True)#data!=DefaultFont)
		self.Layout()
		self.filterable_tree_holder.Parent.Layout()
		
		# refresh to ensure that the static text doesn't get painted anywhere
		# else
		self.Refresh()
	
	def on_module_choice(self, data):
		self.mod = data
		self.item_section = font_settings["module_fonts"]
		self.item_to_set = data.Name()
		
		self.on_item_choice(data, fonts.get_module_font_params)

	def on_category_choice(self, data):
		if data == DefaultFont:
			return self.on_default_choice(data)
		
		# set the preview's mod to None, as we don't want any font based on
		# the module we happen to be preview with
		
		self.mod = None
		books = [biblemgr.bible, biblemgr.commentary, 
			biblemgr.dictionary, biblemgr.genbook]
		
		# if there is a book which uses this language open, 
		# use this for the preview
		for book in books:
			if book.mod and book.mod.Lang() == data:
				self.mod = book.mod
				break
		
		# otherwise just take the first one of the language		
		else:
			# greek and hebrew are always there, so they can be empty
			if self.tree.data[data]:
				self.mod = self.tree.data[data][0]
			else:
				self.mod = None
		
		self.item_section = font_settings["language_fonts"]
		self.item_to_set = data
		
		self.on_item_choice(data, fonts.get_language_font_params)
	
	def on_default_choice(self, data=DefaultFont):
		self.item_section = font_settings
		self.item_to_set = "default_fonts"
		self.mod = biblemgr.bible.mod
		
		
		self.on_item_choice(data, lambda data:fonts.default_fonts())
		
		
	

	def update_preview(self):
		if self.mod is None:
			self.preview.SetPage(config.MODULE_MISSING_STRING())
			return

		try:
			for frame in guiconfig.mainfrm.frames:
				book = frame.book
				if self.mod.Name() not in book.GetModuleList():
					continue

				# if we are already set to that book, use it
				### should we get a better key here?
				if self.mod == frame.mod or True:
					if isinstance(frame.reference, basestring):
						ref = frame.reference
					else:
						ref = frame.reference.text
						
				self.mod.KeyText(to_str(ref, self.mod))
				
				text = self.mod.RenderText()
				# if there is no text here, look back and forth for text
				if not text:
					old = self.mod.getSkipConsecutiveLinks()
					self.mod.setSkipConsecutiveLinks(True)
					
					for direction in 1, -1:
						self.mod.increment(direction)
						text = self.mod.RenderText()
						if text:
							break
					
					self.mod.setSkipConsecutiveLinks(old)

				ref = to_unicode(self.mod.getKeyText(), self.mod)
				ref = frame.format_ref(self.mod, ref)
				#if book in (biblemgr.bible, biblemgr.commentary):
				#	ref = pysw.internal_to_user(ref)
				#else:
				#	ref = to_unicode(ref, self.mod)
				preview_text = u'%s (%s)<br>%s' % (
					ref, self.mod.Name().decode("utf8"), text.decode("utf8")
				)
				preview_text = u'<span style="font-family: %s; font-size: %spt;">%s</span>' % \
						(self.font_face.StringSelection, self.font_size.Value, preview_text)
				item_to_focus_on = wx.Window.FindFocus()
				self.preview.SetPage(preview_text)
				self.preview.ForceKillFocus()
				item_to_focus_on.SetFocus()
				
		finally:
			pass
			#preview % tuple(guiconfig.get_window_colours()))
	
	def ShowModal(self):
		old_fonts = (
			font_settings["default_fonts"], 
			font_settings["language_fonts"].copy(),
			font_settings["module_fonts"].copy(),
		)

		ansa = super(FontChoiceDialog, self).ShowModal()

		if ansa != wx.ID_OK:
			(font_settings["default_fonts"], 
			 font_settings["language_fonts"],			
			 font_settings["module_fonts"]) = old_fonts
		
		return ansa

class FontTree(LanguageModuleTree):
	def add_first_level_groups(self):
		self.model.add_child("Default Font", data=DefaultFont)
		super(FontTree, self).add_first_level_groups()
		self.data[DefaultFont] = []

if __name__ == '__main__':
	a=wx.App(0)
	FontChoiceDialog(None).ShowModal()

