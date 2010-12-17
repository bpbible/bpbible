from string import Template as str_template
import re
from swlib.pysw import process_digits

class VerseTemplate(object):
	"""VerseTemplate is a class which defines templates for Bible Text""" 
	def __init__(self, body=u"$text", header=u"", footer=u"", 
	headings=u'$heading\n', preverse=""):
		self.header = str_template(header)
		self.body = str_template(body)
		self.footer = str_template(footer)
		self.headings = str_template(headings)
		self.preverse = str_template(preverse)
	
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
	# don't ever use capturing groups in here - they are slow
	whitespace = '<(?:(?:blockquote[^>]*>)|(?:/blockquote>)|(?:br ?[^>]*>)|(?:p ?[^>]*>)|(?:!P>)|(?:/div>))'
	### We just include the </div> in our whitespace; if we include the
	### opening div, then our verse numbers are moved into the indentedline,
	### which we don't want
	### |(<div class="indentedline"[^>]*>)|(</div>)'
	
	included_whitespace = "(?:%s)(?:%s|\s)*" % (whitespace, whitespace)
	vpl_text = '<br class="verse_per_line" />'
	
	incl_whitespace_start = re.compile("^" + included_whitespace, re.IGNORECASE)
	incl_whitespace_end = re.compile(included_whitespace + "$", re.IGNORECASE)
	a_tags = '<a name="[^"]*_(?:start|end)" osisRef="[^"]*"></a>'
	incl_whitespace_br_start = re.compile(
		u"(?P<ws>%s(?:%s)*)%s" % (included_whitespace, a_tags, vpl_text),
		re.IGNORECASE
	)
	incl_whitespace_br_end = re.compile(
		u"%s(?P<ws>(?:%s)*%s)" % (vpl_text, a_tags, included_whitespace),
		re.IGNORECASE
	)
	
	empty_versenumber = re.compile(u"<a class=\"(?:verse|chapter)number[^\"]*\"[^>]+></a>\s?")
	
	def __init__(self, body, verse_per_line=True):
		self.body = body
		self.verse_per_line = verse_per_line
	
	def safe_substitute(self, dict):
		text = dict.pop("text")
		verse_0 = dict["versenumber"] == process_digits("0", userOutput=True)
		if verse_0 and not text or text == "<br />":
			return u""
		
		if verse_0:
			dict["versenumber"] = u""

		if dict["versenumber"] == process_digits("1", userOutput=True):
			dict["versenumber"] = dict["chapternumber"]
			dict["numbertype"] = "chapternumber"
		else:
			dict["numbertype"] = "versenumber"
		
		whitespace = []
		def collect(match):
			whitespace.append(match.group(0))
			return u""

		# float leading whitespace out to the front
		text = self.incl_whitespace_start.sub(collect, text)

		leading_whitespace = whitespace
		whitespace = []
		
		# float trailing whitespace to end
		text = self.incl_whitespace_end.sub(collect, text)
		
		dict["text"] = text

		verse_per_line = self.verse_per_line
		if verse_0:
			verse_per_line = False

		ret = u"%s%s%s%s\n" % (
			u''.join(leading_whitespace),
			self.body.safe_substitute(dict),
			u''.join(whitespace),
			self.vpl_text * verse_per_line
		)
		
		# remove empty verse number
		ret = self.empty_versenumber.sub(u"", ret)
		

		return ret
	
	def finalize(self, text):
		return self.incl_whitespace_br_start.sub(ur"\g<ws>", 
			self.incl_whitespace_br_end.sub(ur"\g<ws>", text)
		)
	
	@property
	def template(self):
		return self.body.template
		
class SmartVerseTemplate(VerseTemplate):
	def __init__(self, *args, **kwargs):
		super(SmartVerseTemplate, self).__init__(*args, **kwargs)
		self.body = SmartBody(self.body)
		
	
	def finalize(self, text):
		return self.body.finalize(text)
