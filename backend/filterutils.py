from swlib import pysw
from swlib.pysw import SW, BOTTOM
import sgmllib
import re
from util.debug import dprint, ERROR, WARNING
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


def return_success(func):
	def ret(*args, **kwargs):
		return SW.ReturnSuccess(*func(*args, **kwargs))
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
registered = False


class ParserBase(sgmllib.SGMLParser, object):
	def __init__(self):
		super(ParserBase, self).__init__()
		self.token = None
		self.buf = None
		self.success = SW.INHERITED
		self.u = None
		self.biblemgr = None
		
		
	
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

	def unknown_starttag(self, tag, attributes): 
		pass

	def unknown_endtag(self, tag): 
		pass
	
	def handle_starttag(self, tag, method, attributes):
		self.success = SW.SUCCEEDED
		method(attributes)

	
	def get_strongs_headword(self, value):
		if value in strongs_cache:
			return strongs_cache[value]
	
		match = strongs_re.match(value)
		if not match:
			dprint(WARNING, "Could not match lemma", value)
			return
	
		type, number = match.groups()
		if type not in "HG":
			dprint(WARNING, "Unknown lemma", value)
			return
		
		mod, modlang, last_item = dict(
			H=(strongshebrew, "Hebrew", last_hebrew),
			G=(strongsgreek, "Greek", last_greek)
		)[type]

		if not mod:
			dprint(WARNING, "Mod is None for type ", type)
			self.success = SW.INHERITED
			return

		k = mod.getKey()
		k.setText(number)
		mod.setKey(k)
		entry = mod.getRawEntry()
		text = mod.getKeyText()

		match = word_re.match(entry)
		if not match:
			dprint(WARNING, "Could not find strong's headword", 
				"mod:", modlang, "number:", number, "Entry:", entry)
			self.success = SW.INHERITED
			return

		if text == last_item:
			# TR has strong's numbers past the last one (I think for
			# morphlogy. If we hit the last one, do a quick check to see
			# whether it is likely to be past the end. If so, just give the
			# number.
			if last_item.strip("GH0") not in number:
				item = '<small><em>&lt;<a href="passagestudy.jsp?action=showStrongs&type=%s&value=%s">%s</a>&gt;</em></small>' % (modlang, number, number)
				strongs_cache[value] = item
				return item
				
				
		
		word = match.groups()[0]
		#self.buf += "&lt;%s&gt;" % word
		item = '<font size="-1"><glink href="passagestudy.jsp?action=showStrongs&type=%s&value=%s">&lt;%s&gt;</glink></font>' % (modlang, number, word)
		strongs_cache[value] = item

		return item
		
	def set_biblemgr(self, biblemgr):
		self.biblemgr = biblemgr

def clear_cache(biblemgr=None):
	global strongsgreek, strongshebrew, strongs_cache, last_greek, last_hebrew
	strongsgreek = None
	strongshebrew = None
	last_greek = None
	last_hebrew = None
	strongs_cache = {}
	
def setup(biblemgr):
	global strongsgreek, strongshebrew, last_greek, last_hebrew
	strongsgreek = biblemgr.get_module("StrongsGreek")
	strongshebrew = biblemgr.get_module("StrongsHebrew")
	if strongsgreek:
		strongsgreek.setPosition(BOTTOM)
		last_greek = strongsgreek.getKeyText()

	if strongshebrew:
		strongshebrew.setPosition(BOTTOM)
		last_hebrew = strongshebrew.getKeyText()
		

def register_biblemgr(biblemgr):
	global registered
	if registered:
		return
	
	biblemgr.on_before_reload += clear_cache
	biblemgr.on_after_reload += setup
	registered = True
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

		for item in refs[:ellipsis]:
			ref = pysw.VerseList(item, last_text).GetBestRange(True)
			last_text = ref
			buf.append('<a href="bible:%(ref)s">%(ref)s</a>'% locals())
		if(left_over):
			e = "<b><a href = \"bible:?values=%d" % left_over
			for idx, item in enumerate(refs[ellipsis:]):
				ref = pysw.VerseList(item, last_text).GetBestRange(True)
				last_text = ref
			
				e += "&val%d=%s" % (idx, SW.URL.encode(ref).c_str())
			e+= "\">...</a></b>"
		refs = []
		
	
	# DEFAULT BEHAVIOUR
	for item in refs:
		ref = pysw.VerseList(item, last_text).GetBestRange(True)
		last_text = ref
		buf.append('<a href="bible:%(ref)s">%(ref)s</a>'% locals())

	if ellipsis and left_over:
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
