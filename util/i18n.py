"""\
Module to support internationalisation and localisation of the interface.
"""
#python \Python25\Tools\i18n\msgfmt.py -o locales\en\LC_MESSAGES\messages.mo locales\en.po
# python ~/Python-2.5.2/Tools/i18n/msgfmt.py -o locales/en/LC_MESSAGES/messages.mo locales/en.po

# python ~/Python-2.5.2/Tools/i18n/pygettext.py -p locales/ -k N_ `find . -name "*.py"`


import gettext
from util.debug import dprint, WARNING
from util.configmgr import config_manager
from swlib.pysw import SW, change_locale
import os
locale_settings = config_manager.add_section("Locale")
locale_settings.add_item("language", "en", item_type=str)

localedir = "locales"
domain = "messages"             # the translation file is messages.mo

def initialize():
	global langid, mytranslation, ngettext
	langid = locale_settings["language"]
	if langid not in languages:
		dprint(WARNING, "Didn't have language", langid)
		langid = "en"
	
	# Set up Python's gettext
	mytranslation = gettext.translation(domain, localedir,
		[langid], fallback=True)
	
	if type(mytranslation) == gettext.NullTranslations:
		dprint(WARNING, "Language not found for python", langid)
	
	mytranslation.install(unicode=True)
	ngettext = mytranslation.ngettext

	if langid in languages:
		desc, locale, abbrev = languages[langid]
		l = SW.Locale("locales/%s/locale.conf" % langid)
		change_locale(locale, abbrev, additional=l)

def N_(text):
	"""Mark text as i18n'able, but don't translate it yet"""
	return text

#languages = dict(
#	en=N_("English"),
#	es=N_("Spanish"),
#	en_AU=N_("BM test"),
#	vi=N_("Vietnamese"),
##	as=N_("Assammese"),	
#)
	
def find_languages():
	languages = {}
	for item in os.listdir("locales"):
		if os.path.isdir("locales/" + item) and item != "locales.d" and \
			os.path.exists("locales/%s/locale.conf" % item):
			conf = SW.Config("locales/%s/locale.conf" % item)
			language = conf.get("Language", "Description") or item
			locale = conf.get("SWORD", "locale") or "bpbible"
			abbrev_locale = conf.get("SWORD", "abbreviations") or locale
			
			languages[item] = language, locale, abbrev_locale
	
	return languages

languages = find_languages()
