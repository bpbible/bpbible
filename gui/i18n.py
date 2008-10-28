import wx
import sys
from util.debug import dprint, WARNING
from util import i18n

mylocale = None
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

	# Set locale for wxWidgets
	mylocale = wx.Locale(li.Language)
	mylocale.AddCatalogLookupPathPrefix(i18n.localedir)
	if not mylocale.AddCatalog(i18n.domain):
		dprint(WARNING, "Couldn't add wx catalog", i18n.langid)
