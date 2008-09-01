from string import Template as str_template

class VerseTemplate(object):
	"""VerseTemplate is a class which defines templates for Bible Text""" 
	def __init__(self, body=u"$text", header=u"", footer=u"", 
	headings=u"<p><h4>$heading</h4><br>\n"):
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
