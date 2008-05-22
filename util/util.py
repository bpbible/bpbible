from string import Template as str_template
import re
import traceback
import sys
import htmlentitydefs

class VerseTemplate(object):
	"""VerseTemplate is a class which defines templates for Bible Text""" 
	def __init__(self, body="$text", header="", footer="", 
	headings="<p><h4>$heading</h4><br>\n"):
		self.header = str_template(header)
		self.body = str_template(body)
		self.footer = str_template(footer)
		self.headings = str_template(headings)

class Template(VerseTemplate):
	def __init__(self, name, readonly=True, *args, **kwargs):
		super(Template, self).__init__(*args, **kwargs)
		self.name = name
		self.readonly = readonly
		self.items = {}
		for item in "headings body footer header".split():
			self.items[item] = getattr(self, item).template
		self.args, self.kwargs = args, kwargs
	
	def copy(self, name=None, readonly=None):
		if name is None:
			name = self.name
		if readonly is None:
			readonly = self.readonly
		copy = Template(name, readonly, *self.args, **self.kwargs)
		return copy
	
	def __getitem__(self, item):
		return self.items[item]
	
	def __setitem__(self, item, value):
		self.items[item] = value
		getattr(self, item).template = value
	
	#def items(self):
	#	return self.items.copy()
	
	def keys(self):
		return self.items.keys()
	
	def __contains__(self, item):
		return item in self.keys()

class PushPopList(object):
	"""A push/pop list wrapper"""
	def __init__(self, init=None):
		if(init): 
			self.mylist = [init]
		else:
			self.mylist = []

	def push(self, value):
		self.mylist.append(value)
	
	def pop(self):
		try:
			return self.mylist.pop()
		except:
			print "Error popping list"
			raise

	def __call__(self):
		return self.GetMe()

	def GetMe(self):
		if(self.mylist): 
			return self.mylist[-1]
		return None

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

def replace_amp(groups):
	ent = groups.group('amps')
	if ent in htmlentitydefs.name2codepoint:
		return unichr(htmlentitydefs.name2codepoint[ent])

	if ent[0] == "#":
		try:
			return unichr(int(ent[1:]))
		except ValueError:
			from debug import dprint, WARNING
			dprint(WARNING, "Invalid int in html escape", groups.group(0))
		
	return ent

def amps_to_unicode(data):
	return re.sub("&(?P<amps>[^;]*);", replace_amp, data)
	

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

def noop(*args, **kwargs):
	"""Do nothing"""

def is_py2exe():
	return hasattr(sys, "frozen")	
