"""\
Module to support internationalisation and localisation of the interface.
"""
#python \Python25\Tools\i18n\msgfmt.py -o locales\en\LC_MESSAGES\messages.mo locales\en.po
# python ~/Python-2.5.2/Tools/i18n/msgfmt.py -o locales/en/LC_MESSAGES/messages.mo locales/en.po

# python ~/Python-2.5.2/Tools/i18n/pygettext.py -p locales/ -k N_ `find . -name "*.py"`


import config
import gettext
from util.debug import dprint, WARNING
from util.configmgr import config_manager
from swlib.pysw import SW, change_locale
from swlib import pysw
import os
locale_settings = config_manager.add_section("Locale")
locale_settings.add_item("language", "en", item_type=str)
locale_settings.add_item("language_book_names", {"en": "bpbible"}, item_type="pickle")

localedir = "locales"
domain = "messages"             # the translation file is messages.mo

dummy_translator = False
def install_dummy_translator():
	import __builtin__
	__builtin__._ = lambda str: str
	global dummy_translator
	dummy_translator = True
	
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
		desc, locale, abbrev, conf = languages[langid]
		b = locale_settings["language_book_names"].get(langid)
		bookname_languages = dict(get_bookname_languages())
		if b not in bookname_languages:
			if b: print "Language not found", b
			lang = langid
			#b = langid
		else:
			desc, locale, abbrev = bookname_languages[b]
			lang = b

		change_locale(lang, abbrev, additional=conf)

def get_locale(langid):
	if langid in languages:
		desc, locale, abbrev, conf = languages[langid]
		return pysw.get_locale(locale, additional=conf)

def get_bookname_languages():
	langs = [x.c_str() for x in pysw.locale_mgr.getAvailableLocalesVector()]
	for item in langs:
		if item.endswith("abbrev"): continue
		if item in ("en_US", "abbr"): continue
		if "en_au" in item.lower() and config.is_release():
			continue
		
		i2 = item
		if item == "bpbible":
			i2 = "en"

		if i2 in languages:
			desc, locale, abbrev, conf = languages[i2]
			worked, locale, locale_encoding = pysw.get_locale(locale, additional=conf)
		else:
			abbrev = None
			for i in langs:
				if i == item + "-abbrev" or i == item + "_abbrev":
					abbrev = i
					break
			else:
				abbrev = item

			worked, locale, locale_encoding = pysw.get_locale(item)
			desc = locale.getDescription().decode(locale_encoding)
			if desc.endswith(" (Unicode)"): desc = desc[:-10]

		#if abbrev: 
		#	worked, abbrev_locale, abbrev_locale_encoding = pysw.get_locale(abbrev)
		#else: abbrev_locale = None

		yield (item, (desc, locale, abbrev))

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
	
def find_languages(is_release=False):
	languages = {}
	for item in os.listdir("locales"):
		if "en_au" in item.lower() and is_release:
			continue

		if os.path.isdir("locales/" + item) and item != "locales.d" and \
			os.path.exists("locales/%s/locale.conf" % item):
			conf = SW.Config("locales/%s/locale.conf" % item)
			language = conf.get("Language", "Description") or item
			locale = conf.get("SWORD", "locale") or "bpbible"
			abbrev_locale = conf.get("SWORD", "abbreviations") or locale
			locale_conf = SW.Locale("locales/%s/locale.conf" % item)
			
			
			languages[item] = language, locale, abbrev_locale, locale_conf
	
	return languages

languages = find_languages(config.is_release())
