import wx
from swlib.pysw import SW
from util.configmgr import config_manager
from util import osutils


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
