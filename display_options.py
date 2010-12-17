import wx
from util.configmgr import config_manager
from util.observerlist import ObserverList
from util.i18n import N_
import guiconfig
from events import SETTINGS_CHANGED
from backend.filterutils import filter_settings, set_headwords_module_from_conf

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
options.add_item("show_timing", False, item_type=bool)
options.add_item("colour_speakers", "off", item_type=str)

class BooleanOptionMenuItem(object):
	def __init__(self, option_name, menu_text, hint="", force_complete_reload=False, options_section=options):
		self.option_name = option_name
		self.menu_text = menu_text
		self.hint = hint
		self.force_complete_reload = force_complete_reload
		self.options_section = options_section

	def add_to_menu(self, frame, menu):
		item = menu.AppendCheckItem(
			wx.ID_ANY, _(self.menu_text), help=_(self.hint)
		)

		if self.options_section[self.option_name]:
			item.Check()
		
		frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)

	def on_option_clicked(self, event):
		self.options_section[self.option_name] = event.Checked()
		display_option_changed(self.option_name, self.force_complete_reload)

class MultiOptionsMenuItem(object):
	def __init__(self, option_name, menu_text, _options, force_complete_reload=False, options_section=options, on_option_selected=None):
		self.option_name = option_name
		self.menu_text = menu_text
		self.options = _options
		self.options_map = {}
		self.force_complete_reload = force_complete_reload
		self.options_section = options_section
		self.on_option_selected = on_option_selected

	def add_to_menu(self, frame, menu):
		sub_menu = wx.Menu("")
		current_option = self.options_section[self.option_name]
	
		for option_value, menu_text in self.options:
			item = sub_menu.AppendRadioItem(wx.ID_ANY, _(menu_text))
			
			if option_value == current_option:
				item.Check()
			
			self.options_map[item.Id] = option_value
				
			frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)
		
		item = menu.AppendSubMenu(sub_menu, _(self.menu_text))

	def on_option_clicked(self, event):
		self.options_section[self.option_name] = self.options_map[event.Id]
		if self.on_option_selected is not None:
			self.on_option_selected()
		display_option_changed(self.option_name, self.force_complete_reload)

def on_headwords_module_changed():
	from backend.bibleinterface import biblemgr
	set_headwords_module_from_conf(biblemgr)

options_menu = [
	BooleanOptionMenuItem("columns", N_("Columns")),
	BooleanOptionMenuItem("verse_per_line", N_("One line per verse"), N_("Display each verse on its own line.")),
	BooleanOptionMenuItem("continuous_scrolling", N_("Continuous scrolling"), force_complete_reload=True),
	BooleanOptionMenuItem("headings", N_("Headings")),
	BooleanOptionMenuItem("cross_references", N_("Cross References")),
	BooleanOptionMenuItem("footnotes", N_("Footnotes")),
	BooleanOptionMenuItem("strongs_numbers", N_("Strongs Numbers")),
	BooleanOptionMenuItem("strongs_blocked", N_("Strongs Blocked")),
	BooleanOptionMenuItem("morphology", N_("Morphology")),
	BooleanOptionMenuItem("morph_segmentation", N_("Morph Segmentation")),
	MultiOptionsMenuItem("colour_speakers", N_("Colour code speakers"), [
		("woc_in_red", N_("Words of Christ in Red")),
		("coloured_quotes", N_("Colour code by speaker")),
		("off", N_("Off")),
	]),
	MultiOptionsMenuItem("headwords_module", N_("Strong's Headwords"), [
		("HeadwordsTransliterated", N_("Transliterated")),
		("HeadwordsOriginalLang", N_("Original Language")),
		("HeadwordsPronunciation", N_("Pronunciation")),
		("", N_("Strong's Numbers")),
	],
	options_section=filter_settings,
	force_complete_reload=True,
	on_option_selected=on_headwords_module_changed,
	),
]

debug_options_menu = [
	BooleanOptionMenuItem("raw", "Output Raw", force_complete_reload=True),
	BooleanOptionMenuItem("show_timing", "Display timing"),
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
