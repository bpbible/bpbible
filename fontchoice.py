import wx
import wx.html
from swlib.pysw import SW
from util.unicode import to_str, to_unicode
from backend.bibleinterface import biblemgr
from xrc.fontchoice_xrc import *
import guiconfig
from gui import htmlbase
from util.configmgr import config_manager
from module_tree import LanguageModuleTree
from displayframe import DisplayFrameXRC
from util import osutils

DefaultFont = object()

font_settings = config_manager.add_section("Font")
font_settings.add_item("language_fonts", {}, item_type="pickle")
font_settings.add_item("module_fonts", {}, item_type="pickle")
font_settings.add_item("default_fonts", None,#("Arial", 12, False),
		item_type="pickle")

def _default_font():
	if osutils.is_msw():
		# MSW has MS Shell Dlg 2, which can't be set to.
		# just use arial 12 pt
		return "Arial", 12, False

	return wx.NORMAL_FONT.FaceName, wx.NORMAL_FONT.PointSize, False

def get_font_params(data):
	if isinstance(data, basestring):
		return data, get_language_font_params(data)[1]
	
	if data is None:
		return None, font_settings["default_fonts"] or _default_font()

	return data.Lang(), get_module_font_params(data)[1]

def get_module_font_params(module):
	if module is None:
		return default_fonts()

	if module.Name() in font_settings["module_fonts"]:
		return False, font_settings["module_fonts"][module.Name()]
	else:
		return True, get_language_font_params(module.Lang())[1]

def get_language_font_params(language):
	if language in font_settings["language_fonts"]:
		return False, font_settings["language_fonts"][language]
	
	return True, default_fonts()[1]


def default_fonts():
	return not font_settings["default_fonts"], \
				font_settings["default_fonts"] or _default_font()

def get_default_font(module_or_language):
	if isinstance(module_or_language, SW.Module):
		return get_language_font_params(module_or_language.Lang())[1]
	
	if isinstance(module_or_language, basestring):
		return default_fonts()[1]
	
	return _default_font()
	
class FontChoiceDialog(xrcFontChoiceDialog):
	def __init__(self, parent):
		super(FontChoiceDialog, self).__init__(parent)
		self.font_face.Bind(wx.EVT_CHOICE, self.on_font_changed)
		self.font_size.Bind(wx.EVT_SPINCTRL, self.on_font_changed)
		self.gui_use_default_font.Bind(wx.EVT_CHECKBOX, 
			lambda evt: self.on_use_default_font(evt.Checked()))
		
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
			font, size, use_in_gui = get_default_font(self.tree_item)
			self.set_font_params(font, size)
			if self.tree_item == DefaultFont:
				font_settings["default_fonts"] = None
			else:
				if self.item_to_set in self.item_section:
					del self.item_section[self.item_to_set]
				
		
	def set_font_params(self, font, size):
		if not self.font_face.SetStringSelection(font):
			self.font_face.SetSelection(0)

		self.font_size.SetValue(size)
		self.update_preview()
		

	def on_font_changed(self, event):
		font, size = self.font_face.StringSelection, self.font_size.Value
		gui = self.gui_use_in_ui.Value
		self.gui_use_default_font.SetValue(False)
		self.item_section[self.item_to_set] = font, size, gui
		self.update_preview()

	def on_item_choice(self, data, parent_data, font_details_getter):
		default, (font, size, use_in_gui) = font_details_getter(data)
		self.set_font_params(font, size)
		self.tree_item = data
		
		self.on_use_default_font(default)
		
		self.gui_use_default_font.SetValue(default)
		self.gui_use_default_font.ContainingSizer.Show(0, True)#data!=DefaultFont)
		self.Layout()
		self.filterable_tree_holder.Parent.Layout()
		
		# refresh to ensure that the static text doesn't get painted anywhere
		# else
		self.Refresh()
	
	def on_module_choice(self, data, parent_data):
		self.mod = data
		self.preview.mod = data
		self.item_section = font_settings["module_fonts"]
		self.item_to_set = data.Name()
		
		self.on_item_choice(data, parent_data, get_module_font_params)

	def on_category_choice(self, data, parent_data):
		if data == DefaultFont:
			return self.on_default_choice(data, parent_data)
		
		# set the preview's mod to None, as we don't want any font based on
		# the module we happen to be preview with
		self.preview.mod = data
		
		self.mod = None
		books = [biblemgr.bible, biblemgr.commentary, 
			biblemgr.dictionary, biblemgr.genbook]
		
		# if there is a book which uses this language open, 
		# use this for the preview
		for book in books:
			if book.mod.Lang() == data:
				self.mod = book.mod
				break
		
		# otherwise just take the first one of the language		
		else:
			self.mod = self.tree.data[data][0]
		
		self.item_section = font_settings["language_fonts"]
		self.item_to_set = data
		
		self.on_item_choice(data, parent_data, get_language_font_params)
	
	def on_default_choice(self, data=DefaultFont, parent_data=None):
		self.item_section = font_settings
		self.item_to_set = "default_fonts"
		self.preview.mod = None
		self.mod = biblemgr.bible.mod
		
		
		self.on_item_choice(data, parent_data, 
			lambda data:default_fonts())
		
		
	

	def update_preview(self):
		#self.preview.font 
		# self.preview.SetStandardFonts(self.font_size.Value, 
		#	self.font_face.StringSelection, "")
		try:
			books = [biblemgr.bible, biblemgr.commentary, 
				biblemgr.dictionary, biblemgr.genbook]
			frames = guiconfig.mainfrm.frames

			for book, frame in zip(books, frames):
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

				ref = self.mod.getKeyText()
				self.preview.SetPage("%s (%s)<br>%s" % (
					to_unicode(ref, self.mod), self.mod.Name(), text
				))
				
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

