import xml.etree.cElementTree as etree

# cElementTree uses elementtree, but the import is in C code.
# put it here explicitly for py2exe
import xml.etree.ElementTree

from cStringIO import StringIO
import re
from search import fields
from util.debug import dprint, WARNING
import string
from swlib.pysw import SW, TOP
from swlib import pysw


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
	FIELD_SEPARATOR = u"\uFDD1".encode("utf-8")
	DASH = u"\uFDD2".encode("utf-8")
	strongs_cache = {"": []}
	
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
				
	def write_field(self, node, si, type, text, parse_children=True):
		marker = type.MARKER
		si.write("%s%s%s" % (
			marker,
			text,
			marker))

		if parse_children:
			self._parse_children(node, si)

		si.write(marker)
	
	def write_osis_ref(self, ref, node, si, parse_children):
		items = []
		cnt = 0
		for item in ref.split(" "):
			if "-" in item:
				assert item.count("-") == 1, item
				start, end = item.split("-")

				if not pysw.LIB_1512_COMPAT:
					# NASTY HACK: VerseKey max argument can't handle anything
					# other than : for the chapter verse separator. It can handle
					# book:chapter:verse, though. So quickly change all . -> :
					end = end.replace(".", ":")

				vk = SW.VerseKey(start, end)
				while vk.Error() == '\x00':
					items.append(vk.getOSISRef())
					vk.increment(1)
			else:
				items.append(item)

		refs = u' '.join(items)
		refs = refs.encode("utf8").replace(".", self.FIELD_SEPARATOR)
		self.write_field(node, si, fields.RefField, refs,
			parse_children)

class ParseThML(ParseBase):
	strongs_re = re.compile(r"^([HG])(\d+)(!(.*))?")

	def parse(self, utf8string):
		self.first_lemma_warning = True
		tree = etree.fromstring("%s<doc>%s</doc>" % (thml_header, utf8string))
		self.keytext = ""
		si = StringIO()
		self._parse(tree, si)
		return si.getvalue()

	def handle_note(self, node, si):
		return

	def handle_br(self, node, si):
		si.write('\n')
	
	def handle_p(self, node, si):
		si.write('\n')
		self._parse_children(node, si)
		si.write('\n')
	
	handle_div = handle_p

	def handle_sync(self, node, si):
		type = node.attrib.get("type", "")
		val = node.attrib.get("value")
		
		if not val:
			dprint(WARNING, "Empty value", node.attrib)
			return
		
		# TODO: attach to text before
		if type == "morph":
			cls = node.attrib.get("class", "")
			item = ("%s%s%s" % (cls, 
				self.FIELD_SEPARATOR, val.replace("-", self.DASH)))
			
			self.write_field(node, si, fields.StrongsField, item,
				parse_children=False)
			
		elif type == "Strongs":
			# ###NOTE###: this code is adapted from code below. 
			# Do not modify one without the other
			#
			# calculating this is a little much to do every time, so cache it
			# this seems (for the KJV, at least) to work better on the whole 
			# lemma string, not on each part
			lemma = val
			if lemma not in self.strongs_cache:
				match = self.strongs_re.match(lemma)
				if not match:
					if self.first_lemma_warning:
						dprint(WARNING, "Could not match lemma", lemma)
						self.first_lemma_warning = False

					return

				# normalize it - letter then padding of 4 on number
				prefix, number, exclamation_mark, extra = match.groups("")
				number = int(number)
				p = "%s%04d%s" % (prefix, number, extra.upper())
				#self.strongs_cache[lemma] = p
				#items.append(self.strongs_cache[lemma])
			
				self.strongs_cache[lemma] = p

			# take a copy, for we change it later on
			item = self.strongs_cache[lemma]
			self.write_field(node, si, fields.StrongsField, item,
				parse_children=False)
		else:
			dprint(WARNING, "Unknown sync type", node.attrib)
		
	def handle_scripRef(self, node, si):
		ref = node.attrib.get("passage")
		if not ref:
			si2 = StringIO()
			self._parse_children(node, si2)
			ref = si2.getvalue()
			si.write(ref)
			
		refs = []
		list = pysw.i_vk.ParseVerseList(ref, self.keytext, True)
		for item in range(list.Count()):
			i = list.GetElement(item)
			k = SW.VerseKey_castTo(i)
			if k and k.isBoundSet():
				lb = k.LowerBound()
				ub = k.UpperBound()
				refs.append("%s-%s" % (lb.getOSISRef(), ub.getOSISRef()))
			else:
				SW.VerseKey.setText(pysw.i_vk, i.getText())
				refs.append(pysw.i_vk.getOSISRef())

		ref = ' '.join(refs)
		self.write_osis_ref(ref, node, si, parse_children=True)
		
	
	def handle_KeyedEntry(self, node, si):
		self.keytext = node.attrib["key"]
		self._parse_children(node, si)

	mapping = {
		'sync':			handle_sync,
		'note':			handle_note,
		'p':  			handle_p,
		'br': 			handle_br,
		'div':			handle_div,
		'scripRef':		handle_scripRef,
		'KeyedEntry':	handle_KeyedEntry,
	}


class ParseOSIS(ParseBase):
	headings_off = True
	def parse(self, utf8string):
		self.first_lemma_warning = True
		tree = etree.fromstring("<doc>%s</doc>" % utf8string)
		si = StringIO()
		self._parse(tree, si)
		return si.getvalue()
	
	def handle_KeyedEntry(self, node, si):
		self.write_field(node, si, fields.KeyField, node.attrib["key"],
#			# don't parse the children yet...
			parse_children=False)

		self._parse_children(node, si)
		
	def handle_title(self, node, si):
		# only put canonical headings (e.g. in Psalms)
		if node.attrib.get("canonical") != "true":
			return

		si.write("\n")
		self._parse_children(node, si)
		si.write("\n")
	
	def handle_lg(self, node, si):
		si.write("\n")
		self._parse_children(node, si)
		si.write("\n")	

	handle_p = handle_lg
	
	def handle_divineName(self, node, si):
		si2 = StringIO()
		self._parse_children(node, si2)
		text = si2.getvalue()
		try:
			si.write(text.decode("utf8").upper().encode("utf8"))
		except UnicodeDecodeError:
			si.write(text)
	
	def handle_note(self, node, si):
		for item in node:
			# only deal with references, don't leak note text
			if item.tag == "reference":
				self.handle_reference(item, si, parse_children=False)

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
	
	def handle_reference(self, node, si, parse_children=True):
		ref = node.attrib.get("osisRef")
		assert ref
		#refs = vk.ParseVerseList(ref, "", True)
		self.write_osis_ref(ref, node, si, parse_children)
		
	
	strongs_re = re.compile(r"^(?:strong|x-Strongs|Strong):([HG])(\d+)(!(.*))?")
	
	morph_cache = {"": []}
	MORPH_MAPPING = {
		"robinson": "robinson",
		"Robinson": "robinson",
		"x-Robinsons": "robinson",
		"x-Robison": "robinson",
		"strongMorph": "strongMorph",
		"x-StrongsMorph": "strongMorph",
		
	}
	


	def handle_w(self, node, si):
		l = node.attrib.get("lemma", "")
		
		# ###NOTE###: this code is duplicated above. 
		# Do not modify one without the other one

		# calculating this is a little much to do every time, so cache it
		# this seems (for the KJV, at least) to work better on the whole 
		# lemma string, not on each part
		if l not in self.strongs_cache:
			items = []
			for lemma in l.split():
				match = self.strongs_re.match(lemma)
				if not match:
					if self.first_lemma_warning:					
						dprint(WARNING, "Could not match lemma", lemma)
						self.first_lemma_warning = False
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
					self.FIELD_SEPARATOR, item.replace("-", self.DASH)))

			self.morph_cache[m] = m_items

		items.extend(self.morph_cache[m])

		#assert "POS" not in node.attrib, "What do I do with POS?"
		

		if not items:
			self._parse_children(node, si)
			return

		self.write_field(node, si, fields.StrongsField, ' '.join(items))

	mapping = dict(
		title=handle_title,
		divineName=handle_divineName,
		note=handle_note,
		l=handle_l,
		lg=handle_lg,
		p=handle_p,
		lb=handle_lb,
		milestone=handle_milestone,
		reference=handle_reference,
		w=handle_w,
	#	KeyedEntry=handle_KeyedEntry,
	)		

def init_fields():
	start_cnt = cnt = ord(u'\uFDD3')
	for field in fields.all_fields:
		chr = unichr(cnt)
		assert chr != '\uFDEF', "Hit top of range"
		field.MARKER = chr.encode("utf-8")
		cnt += 1

	return u"%c-%c" % (start_cnt, cnt-1)

special_chars = init_fields()

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
	if True:#not ParseOSIS.strongs_off:
		import backend.bibleinterface as b
		b.biblemgr.set_option("Strong's Numbers", "On")

	t = time.time()
	d=main(module="KJV")
	#print d[:5]
	print time.time() - t

