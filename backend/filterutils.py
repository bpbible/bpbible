from swlib import pysw
from swlib.pysw import SW
import sgmllib
import config
import re
from util.debug import *
import traceback
from util.configmgr import config_manager

default_ellipsis_level = 2
filter_settings = config_manager.add_section("Filter")
filter_settings.add_item("use_osis_parser", True, item_type=bool)
filter_settings.add_item("use_thml_parser", True, item_type=bool)
filter_settings.add_item("expand_thml_refs", True, item_type=bool)
filter_settings.add_item("footnote_ellipsis_level", default_ellipsis_level, 
	item_type=int)
filter_settings.add_item("strongs_headwords", True, item_type=bool)
filter_settings.add_item("strongs_colour", "#0000ff")


def me(func):
	def ret(*args, **kwargs):
		#me = 
		return SW.ReturnSuccess(*func(*args, **kwargs))
#		me.success, me.buf = func(*args, **kwargs)
		return me
	ret.__name__ = func.__name__
	return ret

def report_errors(func):
	def ret(*args, **kwargs):
		try: 
			return func(*args, **kwargs)
		except Exception, e:
			try:
				dprint(ERROR, "Exception occurred:\n"+ traceback.format_exc())
			except Exception, traceback_exc:
				dprint(ERROR, "Exception occurred", e)
				dprint(ERROR, "Could not print traceback", traceback_exc)

			return "", SW.FAILED
				
	ret.__name__ = func.__name__		
	return ret


def get_user_data_desc(filter):
	def UserData(func):
		def ret(self, buf, token, userdata):
			u = filter.getData(userdata)
			retval = func(self, buf, token, u)
			#filter.updateData(userdata, u)
			return retval
		ret.__name__ = func.__name__
		return ret
	
	return UserData

strongs_re = re.compile(r"([HG])(\d+)")
#get ophelimos from 
#  5624  ophelimos  o-fel'-ee-mos\n\n\n from a form of 3786; helpful or 
#serviceable, i.e.\n advantageous:--profit(-able).\n see GREEK for 3786
word_re = re.compile(r" \d+ +([^ ]+)")


strongsgreek = strongshebrew = None
strongs_cache = {}


class ParserBase(sgmllib.SGMLParser, object):
	def __init__(self):
		super(ParserBase, self).__init__()
	
	def init(self, token, userdata, buf = ""):
		self.token = token
		self.buf = buf
		self.success = SW.INHERITED
		self.u = userdata
		self.reset()

	def report_unbalanced(self, tag):
		method = getattr(self, "end_%s" % tag, None)
		if method is None:
			self.unknown_endtag(tag)
		else: 
			self.success = SW.SUCCEEDED
			return method()

	def unknown_starttag(self, tag, attributes): pass
	def unknown_endtag(self, tag): pass
	
	def handle_starttag(self, tag, method, attributes):
		self.success = SW.SUCCEEDED
		method(attributes)

	
	def clear_cache(self, biblemgr=None):
		global strongsgreek, strongshebrew, strongs_cache
		strongsgreek = None
		strongshebrew = None
		strongs_cache = {}
	
	def setup(self, biblemgr=None):
		global strongsgreek, strongshebrew
		strongsgreek = self.biblemgr.GetModule("StrongsGreek")
		strongshebrew = self.biblemgr.GetModule("StrongsHebrew")
	
	def get_strongs_headword(self, value):
		if value in strongs_cache:
			return strongs_cache[value]
	
		match = strongs_re.match(value)
		if not match:
			dprint(WARNING, "Could not match lemma", value)
			return
	
		type, number = match.groups()
		if type not in "HG":
			dprint(WARNING, "Unknown lemma", lemma, "Lemmas:", lemmas)
			return
		
		mod = dict(H=strongshebrew, G=strongsgreek)[type]
		modlang = dict(H="Hebrew", G="Greek")[type]

		if not mod:
			dprint(WARNING, "Mod is None for type ",type)
			self.success = SW.INHERITED
			return

		k = mod.getKey()
		k.setText(number)
		mod.setKey(k)
		entry = mod.getRawEntry()
		match = word_re.match(entry)
		if not match:
			dprint(WARNING, "Could not find strong's headword", 
				"mod:", modname, "number:", number, "Entry:", entry)
			self.success = SW.INHERITED
			return

		word = match.groups()[0]
		#self.buf += "&lt;%s&gt;" % word
		item = '<font size="-1"><glink href="passagestudy.jsp?action=showStrongs&type=%s&value=%s">&lt;%s&gt;</glink></font>' % (modlang, number, word)
		strongs_cache[value] = item
		return item
		
	def set_biblemgr(self, biblemgr):
		self.biblemgr = biblemgr
		self.biblemgr.on_before_reload += self.clear_cache
		self.biblemgr.on_after_reload += self.setup
		#self.setup()

		

OSISUserData = get_user_data_desc(SW.PyOSISHTMLHREF)
ThMLUserData = get_user_data_desc(SW.PyThMLHTMLHREF)

def ellipsize(refs, last_text="", ellipsis=None):
	if ellipsis is None:
		ellipsis = filter_settings["footnote_ellipsis_level"]
	
	intable = 0
	
	buf = []
	e = ""

	# ELLIPSIS BEHAVIOUR
	if(ellipsis):
	
		left_over = max(0, len(refs)-ellipsis)
		if left_over == 1:
			ellipsis += 1
			left_over = 0

		for a in refs[:ellipsis]:
			ref = pysw.VerseList(a, last_text).GetBestRange(True)
			last_text = ref
			buf.append('<a href="bible:%(ref)s">%(ref)s</a>'% locals())
		if(left_over):
			e = "<b><a href = \"bible:?values=%d" % left_over
			for id, a in enumerate(refs[ellipsis:]):
				ref = pysw.VerseList(a, last_text).GetBestRange(True)
				last_text = ref
			
				e += "&val%d=%s" % (id, SW.URL.encode(ref).c_str())
			e+= "\">...</a></b>"
		refs = []
		
	
	# DEFAULT BEHAVIOUR
	for a in refs:
		ref = pysw.VerseList(a, last_text).GetBestRange(True)
		last_text = ref
		buf.append('<a href="bible:%(ref)s">%(ref)s</a>'% locals())

	if(left_over): 
		buf.append(e)


	#TABLE BEHAVIOUR
	if intable:
		rows = 2
		cols = max(1, len(buf)/rows)
		buf2 = "<table>"
		for id, a in enumerate(buf):
			if(id%cols==0):
				buf2 += "<tr>"				
		
			buf2 += "<td>" + a + "</td>"
			
			if(id%cols==rows - 1):
				buf2 += "</tr>"				
			
		buf2 += "</table>"

		i = buf2
	else:
		i = " ".join(buf)

	return " <small>%s</small> " % i
