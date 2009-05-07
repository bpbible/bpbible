import re
import traceback
import htmlentitydefs

greek = u'\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff'
hebrew = u'\u0590-\u05ff\ufb1d-\ufb4f'

def insert_language_font(text, language_letters, font, size,
	replacement=r'<fontarea basefont="%(font)s" basesize="%(size)s">\1</fontarea>'):
	return re.sub("(([%s]\s*)+)" % language_letters, 
		replacement % {"font": font, "size": size}, text)

def ReplaceUnicode(data):
	""" This replaces common unicode characters with ASCII equivalents """
	#replace common values
	replacements = {
		8221: "\"", #right quote
		8220: "\"", #left quote
		8212: "--", #em dash
		8217: "'",  #right single quote
		8216: "'",  #left single quote	
	}

	#TODO &#184; Paragraph marker (see KJV)

	for item, replacement in replacements.items():
		data = data.replace("&#%d;" % item, replacement)

		# hmm. Using unicode replace on non-ascii str's text doesn't work
		data = data.replace(unichr(item), replacement)

	return data

def htmlify_unicode(data):
	# I'd like to use the following:
	# return data.encode("ascii", "xmlcharrefreplace")
	# however, this doesn't work always with str's with bad encoding
	letters = []
	for item in data:
		item_int = ord(item)
		if item_int > 127:
			letters.append("&#%s;" % item_int)
		else:
			letters.append(item)
	
	return ''.join(letters)

def KillTags(data):
	""" This removes HTML style tags from in text, while not getting rid of
	content.

	Example: Testing <b>This</b> thing. -> Testing This thing"""
	return re.sub('<[^>]+>', "", data)

def remove_amps(data):
	return re.sub("&[^;]*;", "", data)

do_replace_specials = False
def replace_amp(groups):
	ent = groups.group('amps')
	if not do_replace_specials and ent in ["lt", "gt", "amp"]:
		return groups.group()

	if ent in htmlentitydefs.name2codepoint:
		return unichr(htmlentitydefs.name2codepoint[ent])
	
	if ent == "apos":
		return "'"

	if ent[0] == "#":
		try:
			if ent[1] == "x":
				return unichr(int(ent[1:], 16))

			return unichr(int(ent[1:]))
		except ValueError:
			from debug import dprint, WARNING
			dprint(WARNING, "Invalid int in html escape", groups.group(0))
		
	return ent

def amps_to_unicode(data, replace_specials=True):
	global do_replace_specials
	do_replace_specials = replace_specials
	return re.sub("&(?P<amps>[\w#]*);", replace_amp, data)
	

def RemoveWhitespace(data):
	""" This removes extra whitespace, while not getting rid of content.

	Example: Testing       This thing. -> Testing This thing"""
	return re.sub('\s+', " ", data)

def nl2br(data):
	"""Turns all newlines into htmlstyle linebreaks"""
	return data.replace("\n", "<br />")

def br2nl(data):
	return re.sub("<br[^>]*>", "\n", data)
	
def interact(interaction_locals):
	import code
	code.InteractiveConsole(locals=interaction_locals).interact()

def pluralize(word, count):
	if count == 1:
		return "1 %s" % word
	
	return "%d %ss" % (count, word)

def get_traceback():
	traceback.print_list(traceback.extract_stack())
