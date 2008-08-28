import xml.dom.minidom as m
import xml.etree.cElementTree as etree
from cStringIO import StringIO
import re
from util.debug import dprint, WARNING
import string
from swlib.pysw import SW


import htmlentitydefs
thml_header = """<!DOCTYPE thml-entities [
	%s
]>"""

entity = '<!ENTITY %s "%s">'
entities = []
for (name, codepoint) in htmlentitydefs.name2codepoint.iteritems():
	entities.append(entity % (name, "&#%d;" % codepoint))

thml_header %= '\n'.join(entities)

class ParseBase(object):
	def _parse(self, node, si):
		if node.tag in self.mapping:
			self.mapping[node.tag](self, node, si)

		else:
			self._parse_children(node, si)

	def _parse_children(self, node, si):
		if node.text:
			si.write(node.text.encode("utf8"))

		for item in node:
			self._parse(item, si)
			if item.tail:
				si.write(item.tail.encode("utf8"))
				

class ParseThML(ParseBase):
	def parse(self, utf8string):
		tree = etree.fromstring("%s<doc>%s</doc>" % (thml_header, utf8string))
		si = StringIO()
		self._parse(tree, si)
		return si.getvalue()
	
	mapping = {}

class ParseOSIS(ParseBase):
	headings_off = True
	def parse(self, utf8string):
		tree = etree.fromstring("<doc>%s</doc>" % utf8string)
		si = StringIO()
		self._parse(tree, si)
		return si.getvalue()
	
	def handle_title(self, node, si):
		if self.headings_off:
			return

		si.write("\n")
		self._parse_children(node, si)
		si.write("\n")
	
	handle_lg = handle_title
	handle_p = handle_title
	
	def handle_divineName(self, node, si):
		si2 = StringIO()
		self._parse_children(node, si2)
		text = si2.getvalue()
		try:
			si.write(text.decode("utf8").upper().encode("utf8"))
		except UnicodeDecodeError:
			si.write(text)
	
	def handle_note(self, node, si):
		return
	
	def handle_l(self, node, si):
		if "eID" in node.attrib:
			si.write('\n')

		self._parse_children(node, si)
		if "eID" not in node.attrib:
			si.write('\n')
	
	def handle_lb(self, node, si):
		si.write('\n')
		self._parse_children(node, si)
	
	def handle_milestone(self, node, si):
		### does this make sense?          V ###
		if node.attrib.get("type", "line") != "line":
			si.write('\n')
			self._parse_children(node, si)
			
	
	strongs_re = re.compile(r"^(?:strong|x-Strongs|Strong):([HG])(\d+)(!(.*))?")
	strongs_off = False

	STRONGS_MARKER = u"\uFDD1".encode("utf-8")
	FIELD_SEPARATOR = u"\uFDD2".encode("utf-8")
	strongs_cache = {"": []}
	morph_cache = {"": []}
	MORPH_MAPPING = {
		"robinson": "robinson",
		"Robinson": "robinson",
		"x-Robinsons": "robinson",
		"x-Robison": "robinson",
		"strongMorph": "strongMorph",
	}
	


	def handle_w(self, node, si):
		l = node.attrib.get("lemma", "")

		# calculating this is a little much to do every time, so cache it
		# this seems (for the KJV, at least) to work better on the whole 
		# lemma string, not on each part
		if l not in self.strongs_cache:
			items = []
			for lemma in l.split():
				match = self.strongs_re.match(lemma)
				if not match:
					dprint(WARNING, "Could not match lemma", lemma)
					continue

				# normalize it - letter then padding of 4 on number
				prefix, number, exclamation_mark, extra = match.groups("")
				number = int(number)
				p = "%s%04d%s" % (prefix, number, extra.upper())
				#self.strongs_cache[lemma] = p
				#items.append(self.strongs_cache[lemma])
				items.append(p)
			self.strongs_cache[l] = items

		# take a copy, for we change it later on
		items = self.strongs_cache[l][:]

		m = node.attrib.get("morph", "")
		if m not in self.morph_cache:
			m_items = []
			for item in m.split():
				i = item.split(":", 1)
				if len(i) == 1:
					dprint(WARNING, "No class found for morph", node.attrib)
					continue
				
				type, item = i


				if type not in self.MORPH_MAPPING:
					dprint(WARNING, "Unknown morph class", node.attrib)
					continue

				m_items.append("%s%s%s" % (self.MORPH_MAPPING[type], 
					self.FIELD_SEPARATOR, item))

			self.morph_cache[m] = m_items

		items.extend(self.morph_cache[m])

		#assert "POS" not in node.attrib, "What do I do with POS?"
		

		if not items:
			self._parse_children(node, si)
			return

		si.write("%s%s%s" % (self.STRONGS_MARKER,
			' '.join(items),
			self.STRONGS_MARKER))

		self._parse_children(node, si)
		si.write(self.STRONGS_MARKER)

	mapping = dict(
		title=handle_title,
		divineName=handle_divineName,
		note=handle_note,
		l=handle_l,
		lg=handle_lg,
		p=handle_p,
		lb=handle_lb,
		milestone=handle_milestone,
	)		

	if not strongs_off:
		mapping["w"] = handle_w
	

def method1(mod):
	return mod.StripText() #mod.getRawEntry()

def method3(mod):
	return mod.StripText(mod.getRawEntry())

def method4(mod):
	items.append(mod.getRawEntry())

def method5(mod):
	return ParseOSIS().parse(mod.getRawEntry())

def method5b(mod):
	entry = mod.getRawEntry()
	try:
		return ParseThML().parse(entry)
	except etree.XMLParserError:
		print mod.getKeyText()
		return mod.StripText(entry)
	
def method6(mod):
	t1 = re.sub(r"\s+", " ", method5(mod)).strip()
	t2 = re.sub(r"\s+", " ", method1(mod)).strip()
	assert t1 == t2, (t1, t2)

def after4():
	return parse('\n'.join(items))

def after4b():
	return ParseOSIS().parse('%'.join(items)).split("%")

def after4c():
	import time
	t = time.time()
	text, num = re.subn("(<\s*See [^>\]]*[>\]])|(\x15)", "", '\n'.join(items))
	print time.time() - t
	return ParseThML().parse(text)

items = []
def main(method=method4, after=after4b, module=None):
	# clear its cache...
	ParseOSIS.strongs_cache = {"": []}
	ParseOSIS.morph_cache = {"": []}


	import backend.bibleinterface as b
	bible = b.biblemgr.bible
	if module is not None:
		bible.SetModule(module)
	items[:] = []

	ret = []
	
	for item in yield_verses(bible.mod):
		ret.append(method(bible.mod))
	
	return after() or ret

def yield_verses(mod):
	from swlib.pysw import VK, TOP
	vk = VK()
	vk.Headings(1)
	vk.setPosition(TOP)
	#vk.setText("Matthew 1:1")
	vk.Persist(1)
	vk.thisown = False
	
	mod.setKey(vk)

	books = ("Genesis", "Matthew")#"Exodus")
	while not vk.Error():
	#while vk.Testament() in '\x00\x01':
	#while vk.Testament() == '\x00' or vk.Book() == '\x00' or \
	#	vk.getBookName() in books:
		yield 
		vk.increment(1)

if __name__ == '__main__':
	import time
	if not ParseOSIS.strongs_off:
		import backend.bibleinterface as b
		b.biblemgr.set_option("Strong's Numbers", "On")

	t = time.time()
	d=main(module="KJV")
	#print d[:5]
	print time.time() - t

