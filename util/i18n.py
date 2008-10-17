"""\
Module to support internationalisation and localisation of the interface.
"""
#python \Python25\Tools\i18n\msgfmt.py -o locales\en\LC_MESSAGES\messages.mo locales\en.po
# python ~/Python-2.5.2/Tools/i18n/msgfmt.py -o locales/en/LC_MESSAGES/messages.mo locales/en.po

# python ~/Python-2.5.2/Tools/i18n/pygettext.py -p locales/ -k N_ `find . -name "*.py"`


import gettext
import wx
from util.debug import dprint, WARNING
from util.configmgr import config_manager
locale_settings = config_manager.add_section("Locale")
locale_settings.add_item("language", "en", item_type=str)
	

localedir = "locales"
domain = "messages"             # the translation file is messages.mo

def initialize():
	global langid
	langid = locale_settings["language"]
	
	# Set up Python's gettext
	mytranslation = gettext.translation(domain, localedir,
		[langid], fallback=True)
	
	if type(mytranslation) == gettext.NullTranslations:
		dprint(WARNING, "Language not found for python", langid)
	
	mytranslation.install()

def N_(text):
	"""Mark text as i18n'able, but don't translate it yet"""
	return text

languages = dict(
	en=N_("English"),
	es=N_("Spanish"),
	en_AU=N_("BM test"),
)
	
