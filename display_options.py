import wx
from util.configmgr import config_manager
from util.observerlist import ObserverList
import guiconfig
from events import SETTINGS_CHANGED

options = config_manager.add_section("Options")
options.add_item("columns", False, item_type=bool)
options.add_item("verse_per_line", False, item_type=bool)
options.add_item("continuous_scrolling", True, item_type=bool)
options.add_item("headings", True, item_type=bool)
options.add_item("cross_references", True, item_type=bool)
options.add_item("footnotes", True, item_type=bool)
options.add_item("strongs_numbers", True, item_type=bool)
options.add_item("strongs_blocked", True, item_type=bool)
options.add_item("morphology", True, item_type=bool)
options.add_item("morph_segmentation", False, item_type=bool)
options.add_item("raw", False, item_type=bool)
options.add_item("colour_speakers", "off", item_type=str)

class BooleanOptionMenuItem(object):
	def __init__(self, option_name, menu_text, hint="", force_complete_reload=False):
		self.option_name = option_name
		self.menu_text = menu_text
		self.hint = hint
		self.force_complete_reload = force_complete_reload

	def add_to_menu(self, frame, menu):
		item = menu.AppendCheckItem(
			wx.ID_ANY, self.menu_text, help=self.hint
		)

		if options[self.option_name]:
			item.Check()
		
		frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)

	def on_option_clicked(self, event):
		options[self.option_name] = event.Checked()
		display_option_changed(self.option_name, self.force_complete_reload)

class MultiOptionsMenuItem(object):
	def __init__(self, option_name, menu_text, options, force_complete_reload=False):
		self.option_name = option_name
		self.menu_text = menu_text
		self.options = options
		self.options_map = {}
		self.force_complete_reload = force_complete_reload

	def add_to_menu(self, frame, menu):
		sub_menu = wx.Menu("")
		current_option = options[self.option_name]
	
		for option_value, menu_text in self.options:
			item = sub_menu.AppendRadioItem(wx.ID_ANY, menu_text)
			
			if option_value == current_option:
				item.Check()
			
			self.options_map[item.Id] = option_value
				
			frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)
		
		item = menu.AppendSubMenu(sub_menu, self.menu_text)
			
		#frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)

	def on_option_clicked(self, event):
		options[self.option_name] = self.options_map[event.Id]
		display_option_changed(self.option_name, self.force_complete_reload)

options_menu = [
	BooleanOptionMenuItem("columns", "Columns"),
	BooleanOptionMenuItem("verse_per_line", "One line per verse", "Display each verse on its own line."),
	BooleanOptionMenuItem("continuous_scrolling", "Continuous scrolling", force_complete_reload=True),
	BooleanOptionMenuItem("headings", "Headings"),
	BooleanOptionMenuItem("cross_references", "Cross References"),
	BooleanOptionMenuItem("footnotes", "Footnotes"),
	BooleanOptionMenuItem("strongs_numbers", "Strongs Numbers"),
	BooleanOptionMenuItem("strongs_blocked", "Strongs Blocked"),
	BooleanOptionMenuItem("morphology", "Morphology"),
	BooleanOptionMenuItem("morph_segmentation", "Morph Segmentation"),
	MultiOptionsMenuItem("colour_speakers", "Colour code speakers", [
		("woc_in_red", "Words of Christ in Red"),
		("coloured_quotes", "Colour code by speaker"),
		("off", "Off"),
	]),
]

debug_options_menu = [
	# XXX: This should force the entire page to reload.
	BooleanOptionMenuItem("raw", "Output Raw", force_complete_reload=True),
]

display_option_changed_observers = ObserverList()

def display_option_changed(option_name, force_complete_reload):
	if force_complete_reload:
		guiconfig.mainfrm.UpdateBibleUI(settings_changed=True, source=SETTINGS_CHANGED)
	else:
		display_option_changed_observers(option_name)

def all_options():
	return options.items.keys()

def get_js_option_value(option):
	type = options.item_types[option]
	if type not in (str, bool):
		raise TypeError("Only bool and str supported at the moment (option: %s)" % option)
	if type == bool:
		return "true" if options[option] else "false"
	else:
		return "'%s'" % options[option].encode("utf8")
