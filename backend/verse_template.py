from string import Template as str_template
import re

class VerseTemplate(object):
	"""VerseTemplate is a class which defines templates for Bible Text""" 
	def __init__(self, body=u"$text", header=u"", footer=u"", 
	headings=u'<h6 class="heading" canonical="$canonical">$heading</h6>\n'):
		self.header = str_template(header)
		self.body = str_template(body)
		self.footer = str_template(footer)
		self.headings = str_template(headings)
	
	def finalize(self, text):
		return text

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

class SmartBody(object):
	whitespace = "(<INDENT-BLOCK-(START|END)[^>]*>)|(<br( [^>]*)?>)|(<p( [^>]*)?>)|(<!P>)"
	included_whitespace = "(%s)(%s|\s)*" % (whitespace, whitespace)
	vpl_text = '<br class="verse_per_line">'
	
	incl_whitespace_start = re.compile("^" + included_whitespace, re.IGNORECASE)
	incl_whitespace_end = re.compile(included_whitespace + "$", re.IGNORECASE)
	incl_whitespace_br_start = re.compile(
		"(?P<ws>%s)%s" % (included_whitespace, vpl_text),
		re.IGNORECASE
	)
	incl_whitespace_br_end = re.compile(
		"%s(?P<ws>%s)" % (vpl_text, included_whitespace),
		re.IGNORECASE
	)
	
	empty_versenumber = re.compile("<small><sup></sup></small></glink>\s?")
	
	def __init__(self, body, verse_per_line=True):
		self.body = body
		self.verse_per_line = verse_per_line
	
	def safe_substitute(self, dict):
		text = dict.pop("text")
		if dict["versenumber"] == 0 and not text or text == "<br />":
			return ""
		
		if dict["versenumber"] == 0:
			dict["versenumber"] = ""
			
		
		whitespace = []
		def collect(match):
			whitespace.append(match.group(0))
			return ""

		# float leading whitespace out to the front
		text = self.incl_whitespace_start.sub(collect, text)

		leading_whitespace = whitespace
		whitespace = []
		
		# float trailing whitespace to end
		text = self.incl_whitespace_end.sub(collect, text)
		
		dict["text"] = text

		ret = "%s%s%s%s\n" % (
			''.join(leading_whitespace),
			self.body.safe_substitute(dict),
			''.join(whitespace),
			self.vpl_text * self.verse_per_line,			
		)
		
		# remove empty verse number
		ret = self.empty_versenumber.sub("", ret)
		

		return ret
	
	def finalize(self, text):
		return self.incl_whitespace_br_start.sub(r"\g<ws>", 
			self.incl_whitespace_br_end.sub(r"\g<ws>", text)
		)
		

class SmartVerseTemplate(VerseTemplate):
	def __init__(self, *args, **kwargs):
		super(SmartVerseTemplate, self).__init__(*args, **kwargs)
		self.body = SmartBody(self.body)
		
	
	def finalize(self, text):
		return self.body.finalize(text)
