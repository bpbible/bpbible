import wx
import sys
from util.debug import dprint, WARNING
from util import i18n

mylocale = None
language_workaround_upto = wx.LANGUAGE_USER_DEFINED
def initialize():
	li = wx.Locale.FindLanguageInfo(i18n.langid)
	if not li:
		dprint(WARNING, "Language not found for wx", i18n.langid)
		return
	
	# save this so it isn't deleted
	global mylocale
	
	# Make *sure* any existing locale is deleted before the new
	# one is created.  The old C++ object needs to be deleted
	# before the new one is created, and if we just assign a new
	# instance to the old Python variable, the old C++ locale will
	# not be destroyed soon enough, likely causing a crash.	
	if mylocale is not None:
		assert sys.getrefcount(mylocale) <= 2
		del mylocale

	hide_logging = wx.LogNull()
	
	# Set locale for wxWidgets
	mylocale = wx.Locale(li.Language)
	if not mylocale.IsOk():
		# currently wxMSW may refuse to set locale if it doesn't like it
		# here we make a new language which will use the right catalogs
		# NOTE: This will leave the OS locale set to english
		dprint(WARNING, "Couldn't set at all, smudging...")
		del mylocale
		global language_workaround_upto
		
		lang_info = wx.Locale.FindLanguageInfo("en")
		lang_info.CanonicalName = li.CanonicalName
		lang_info.Description = li.Description
		lang_info.Language = language_workaround_upto
		language_workaround_upto += 1
		wx.Locale.AddLanguage(lang_info)
		mylocale = wx.Locale(lang_info.Language)
		if not mylocale.IsOk():
			dprint(ERROR, "Couldn't set locale or even english!!!! Bad things may happen!!!")
		

	mylocale.AddCatalogLookupPathPrefix(i18n.localedir)
	if not mylocale.AddCatalog(i18n.domain):
		dprint(WARNING, "Couldn't add wx catalog", i18n.langid)
