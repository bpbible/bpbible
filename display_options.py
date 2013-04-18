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
options.add_item("strongs_position", "underneath", item_type=str)
options.add_item("highlight_strongs", True, item_type=bool)
options.add_item("morphology", True, item_type=bool)
options.add_item("morph_segmentation", False, item_type=bool)
options.add_item("raw", False, item_type=bool)
options.add_item("show_timing", False, item_type=bool)
options.add_item("colour_speakers", "off", item_type=str)
options.add_item("reference_bar", False, item_type=bool)

sword_options_map = dict(
	strongs_numbers="Strong's Numbers",
	morphology="Morphological Tags",
	morph_segmentation="Morpheme Segmentation",
)

sword_options_with_fixed_values = dict(
	Headings=True,
	Footnotes=True,
)

all_reload_options = (
	DO_NOT_RELOAD,
	RELOAD_BIBLE_FRAMES,
	RELOAD_ALL_FRAMES
) = range(3)

class Separator(object):
	def add_to_menu(self, frame, menu):
		menu.AppendSeparator()

class BooleanOptionMenuItem(object):
	def __init__(self, option_name, menu_text, hint="", reload_options=DO_NOT_RELOAD, options_section=options):
		self.option_name = option_name
		self.menu_text = menu_text
		self.hint = hint
		self.reload_options = reload_options
		self.options_section = options_section

	def add_to_menu(self, frame, menu):
		item = menu.AppendCheckItem(
			wx.ID_ANY, _(self.menu_text), help=_(self.hint or self.menu_text)
		)

		if self.options_section[self.option_name]:
			item.Check()
		
		frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)

	def on_option_clicked(self, event):
		self.options_section[self.option_name] = event.Checked()
		display_option_changed(self.option_name, self.reload_options, self.options_section)

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
	
		for v in self.options:
			if len(v) == 3:
				option_value, menu_text, hint = v
			else:
				option_value, menu_text = v
				hint = ""

			item = sub_menu.AppendRadioItem(wx.ID_ANY, _(menu_text), _(hint))
			
			if option_value == current_option:
				item.Check()
			
			self.options_map[item.Id] = option_value
				
			frame.Bind(wx.EVT_MENU, self.on_option_clicked, item)
		
		item = menu.AppendSubMenu(sub_menu, _(self.menu_text))

	def on_option_clicked(self, event):
		self.options_section[self.option_name] = self.options_map[event.Id]
		if self.on_option_selected is not None:
			self.on_option_selected()
		display_option_changed(self.option_name, self.reload_options, self.options_section)

def on_headwords_module_changed():
	from backend.bibleinterface import biblemgr
	set_headwords_module_from_conf(biblemgr)

options_menu = [
	BooleanOptionMenuItem("verse_per_line", N_("One line per verse"), N_("Display each verse on its own line.")),
	BooleanOptionMenuItem("continuous_scrolling", N_("Continuous scrolling"), N_("Show more than one chapter at once."), reload_options=RELOAD_ALL_FRAMES),
	BooleanOptionMenuItem("columns", N_("Columns"), N_("Display the chapter in more than one column.")),
	BooleanOptionMenuItem("reference_bar", N_("Reference bar")),
	Separator(),
	BooleanOptionMenuItem("headings", N_("Headings"), N_("Show headings in the text.")),
	BooleanOptionMenuItem("footnotes", N_("Footnotes"), N_("Show footnotes in the text")),
	BooleanOptionMenuItem("cross_references", N_("Cross References"), N_("Show cross references in the text.")),
	MultiOptionsMenuItem("colour_speakers", N_("Colour code speakers"), [
		("woc_in_red", N_("Words of Christ in Red")),
		("coloured_quotes", N_("Colour code by speaker (ESV only)")),
		("off", N_("Off")),
	]),
	Separator(),
	BooleanOptionMenuItem("strongs_numbers", N_("Strongs Numbers"), reload_options=RELOAD_BIBLE_FRAMES),
	MultiOptionsMenuItem("strongs_position", N_("Strongs Positioning"), [
		("underneath", N_("Underneath text"), N_("Show the Original Language Word underneath the word.")),
		("inline", N_("Inline with text"), N_("Show the Original Language Word next to the word.")),
		("hover", N_("Show on hover"), N_("Show the Original Language Word when the cursor is over the word.")),
		("click", N_("Show on click"), N_("Show the Original Language Word when the word is selected.")),
	]),
	MultiOptionsMenuItem("headwords_module", N_("Strongs Headwords"), [
		("HeadwordsTransliterated", N_("Transliterated")),
		("HeadwordsOriginalLang", N_("Original Language")),
		("HeadwordsPronunciation", N_("Pronunciation")),
		("", N_("Strongs Numbers")),
	], options_section=filter_settings,
		reload_options=RELOAD_BIBLE_FRAMES,
		on_option_selected=on_headwords_module_changed,
	),
	BooleanOptionMenuItem("highlight_strongs", N_("Highlight Matching Strongs")),
	BooleanOptionMenuItem("morphology", N_("Morphology"), reload_options=RELOAD_BIBLE_FRAMES),
	BooleanOptionMenuItem("morph_segmentation", N_("Morph Segmentation"), reload_options=RELOAD_BIBLE_FRAMES),
]

debug_options_menu = [
	BooleanOptionMenuItem("raw", N_("Output Raw"), reload_options=RELOAD_ALL_FRAMES),
	BooleanOptionMenuItem("show_timing", N_("Display timing")),
]

display_option_changed_observers = ObserverList()

def display_option_changed(option_name, reload_options, options_section):
	from backend.bibleinterface import biblemgr
	if option_name in sword_options_map:
		biblemgr.set_option(sword_options_map[option_name], options_section[option_name])

	display_option_changed_observers(option_name, options_section)
	if reload_options == RELOAD_BIBLE_FRAMES:
		guiconfig.mainfrm.UpdateBibleUI(settings_changed=True, source=events.SETTINGS_CHANGED)
	elif reload_options == RELOAD_ALL_FRAMES:
		guiconfig.mainfrm.refresh_all_pages()

def all_options():
	return options.items.keys()

def get_js_option_value(option, options_section=options, quote_string=False):
	type = options_section.item_types[option]
	if type not in (str, bool):
		raise TypeError("Only bool and str supported at the moment (option: %s)" % option)
	if type == bool:
		return "true" if options_section[option] else "false"
	else:
		option_value = options_section[option].encode("utf8")
		if quote_string:
			option_value = "'%s'" % option_value
		return option_value
