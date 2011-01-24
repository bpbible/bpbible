import wx
from swlib.pysw import SW
from util.configmgr import config_manager
from util import osutils
from util.observerlist import ObserverList
from backend.bibleinterface import biblemgr


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

def get_module_gui_font(module, default_to_None=False):
	default, (face, size, use_in_gui) = get_module_font_params(module)
	if use_in_gui:
		font = wx.FFont(size, wx.FONTFAMILY_ROMAN, face=face)
	else:
		if default_to_None:
			font = None
		else:
			font = wx.NORMAL_FONT
	
	return font#use_in_gui, font

fonts_changed = ObserverList()

font_css = ""
css_loaded = False

def fonts_have_changed():
	global css_loaded
	css_loaded = False

fonts_changed += fonts_have_changed

def get_css():
	global font_css, css_loaded

	if not css_loaded:
		css_loaded = True
		# We add the rule for [module] to revert to the default font for any
		# module that does not have a custom font.
		font_css = get_css_rule("html, [module]", default_fonts()[1])
		for lang_code, font in font_settings["language_fonts"].iteritems():
			font_css += get_css_rule('[lang="%s"]' % lang_code, font)

		for module, font in font_settings["module_fonts"].iteritems():
			font_css += get_css_rule('[module="%s"]' % module, font)

	return font_css

def get_css_rule(selector, font):
	return "%s { font-family: %s; font-size: %spt; }\n" % (selector, font[0], font[1])
