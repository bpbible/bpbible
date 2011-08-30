import wx
from util.configmgr import config_manager
from util.observerlist import ObserverList
from util.i18n import N_
import guiconfig
import events
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

sword_options_map = dict(
	strongs_numbers="Strong's Numbers",
	morphology="Morphological Tags",
	morph_segmentation="Morpheme Segmentation",
)

all_reload_options = (
	DO_NOT_RELOAD,
	RELOAD_BIBLE_FRAMES,
	RELOAD_ALL_FRAMES
) = range(3)

class BooleanOptionMenuItem(object):
	def __init__(self, option_name, menu_text, hint="", reload_options=DO_NOT_RELOAD, options_section=options):
		self.option_name = option_name
		self.menu_text = menu_text
		self.hint = hint
		self.reload_options = reload_options
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
		display_option_changed(self.option_name, self.reload_options)

class MultiOptionsMenuItem(object):
	def __init__(self, option_name, menu_text, _options, reload_options=DO_NOT_RELOAD, options_section=options, on_option_selected=None):
		self.option_name = option_name
		self.menu_text = menu_text
		self.options = _options
		self.options_map = {}
		self.reload_options = reload_options
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
		display_option_changed(self.option_name, self.reload_options)

def on_headwords_module_changed():
	from backend.bibleinterface import biblemgr
	set_headwords_module_from_conf(biblemgr)

options_menu = [
	BooleanOptionMenuItem("columns", N_("Columns")),
	BooleanOptionMenuItem("verse_per_line", N_("One line per verse"), N_("Display each verse on its own line.")),
	BooleanOptionMenuItem("continuous_scrolling", N_("Continuous scrolling"), reload_options=RELOAD_ALL_FRAMES),
	BooleanOptionMenuItem("headings", N_("Headings")),
	BooleanOptionMenuItem("cross_references", N_("Cross References")),
	BooleanOptionMenuItem("footnotes", N_("Footnotes")),
	BooleanOptionMenuItem("strongs_numbers", N_("Strongs Numbers"), reload_options=RELOAD_BIBLE_FRAMES),
	BooleanOptionMenuItem("strongs_blocked", N_("Strongs Underneath")),
	BooleanOptionMenuItem("morphology", N_("Morphology"), reload_options=RELOAD_BIBLE_FRAMES),
	BooleanOptionMenuItem("morph_segmentation", N_("Morph Segmentation"), reload_options=RELOAD_BIBLE_FRAMES),
	MultiOptionsMenuItem("colour_speakers", N_("Colour code speakers"), [
		("woc_in_red", N_("Words of Christ in Red")),
		("coloured_quotes", N_("Colour code by speaker")),
		("off", N_("Off")),
	]),
	MultiOptionsMenuItem("headwords_module", N_("Strongs Headwords"), [
		("HeadwordsTransliterated", N_("Transliterated")),
		("HeadwordsOriginalLang", N_("Original Language")),
		("HeadwordsPronunciation", N_("Pronunciation")),
		("", N_("Strongs Numbers")),
	],
	options_section=filter_settings,
	reload_options=RELOAD_BIBLE_FRAMES,
	on_option_selected=on_headwords_module_changed,
	),
]

debug_options_menu = [
	BooleanOptionMenuItem("raw", "Output Raw", reload_options=RELOAD_ALL_FRAMES),
	BooleanOptionMenuItem("show_timing", "Display timing"),
]

display_option_changed_observers = ObserverList()

def display_option_changed(option_name, reload_options):
	from backend.bibleinterface import biblemgr
	if option_name in sword_options_map:
		biblemgr.set_option(sword_options_map[option_name], options[option_name])

	if reload_options == DO_NOT_RELOAD:
		display_option_changed_observers(option_name)
	elif reload_options == RELOAD_BIBLE_FRAMES:
		guiconfig.mainfrm.UpdateBibleUI(settings_changed=True, source=events.SETTINGS_CHANGED)
	elif reload_options == RELOAD_ALL_FRAMES:
		guiconfig.mainfrm.refresh_all_pages()

def all_options():
	return options.items.keys()

def get_js_option_value(option, quote_string=False):
	type = options.item_types[option]
	if type not in (str, bool):
		raise TypeError("Only bool and str supported at the moment (option: %s)" % option)
	if type == bool:
		return "true" if options[option] else "false"
	else:
		option_value = options[option].encode("utf8")
		if quote_string:
			option_value = "'%s'" % option_value
		return option_value
