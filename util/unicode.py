import swlib.swordlib as SW
from debug import dprint, WARNING
from util import get_traceback

def to_unicode(text, mod=None):
	if mod is None:
		#dprint(WARNING, "mod is None in to_unicode")
		#get_traceback()
		encoding = "utf8"
	else:
		encoding = "cp1252"
	
		if ord(mod.Encoding()) == SW.ENC_UTF8:
			encoding = "utf8"
	
	return text.decode(encoding, "replace")

def to_str(text, mod=None):
	if mod is None:
		encoding = "utf8"
	else:
		encoding = "cp1252"
	
		if ord(mod.Encoding()) == SW.ENC_UTF8:
			encoding = "utf8"

	
	return text.encode(encoding, "replace")

def get_module_encoding(module):
	encoding = "cp1252"
	
	if ord(module.Encoding()) == SW.ENC_UTF8:
		encoding = "utf8"

	return encoding

def to_unicode_2(text, module):
	if not text:
		return
		
	return text.decode(get_module_encoding(module))
