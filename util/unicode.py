import swlib.swordlib as SW
from debug import dprint, WARNING

def to_unicode(text, mod=None):
	encoding = "utf8"
	if mod and ord(mod.Encoding()) == SW.ENC_LATIN1:
		encoding = "cp1252"
	
	return text.decode(encoding, "replace")

def to_str(text, mod=None):
	encoding = "utf8"
	if mod and ord(mod.Encoding()) == SW.ENC_LATIN1:
		encoding = "cp1252"
	
	return text.encode(encoding, "replace")

def get_module_encoding(module):
	encoding = "UTF-8"
	if module.getConfigEntry("Encoding") == "Latin-1":
		encoding = "cp1252"
	
	return encoding

def to_unicode_2(text, module):
	if not text:
		return
		
	return text.decode(get_module_encoding(module))
