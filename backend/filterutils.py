from swlib import pysw
from swlib.pysw import SW, BOTTOM
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
filter_settings.add_item("headwords_module", "HeadwordsTransliterated", item_type=str)
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

strongs_re = re.compile(r"([HG])(\d+)(!\w)?")
#get ophelimos from 
#  5624  ophelimos  o-fel'-ee-mos\n\n\n from a form of 3786; helpful or 
#serviceable, i.e.\n advantageous:--profit(-able).\n see GREEK for 3786

#TODO?: G5516 chi xi stigma H1021 Beyth hak-Kerem
#     : G5607, G03588 - multiple words
word_re = re.compile(r" \d+ +([^ ]+)")


# make reloading not clear out some of our variables
try:
	headwords_module
except: 
	headwords_module = None
	strongsgreek = strongshebrew = None

	registered = False

tag = SW.XMLTag()

strongs_cache = {}
strongs_cacher = None
class ParserBase(object):
	def __init__(self):
		super(ParserBase, self).__init__()
		self.token = None
		self.buf = None
		self.success = SW.INHERITED
		self.u = None
		self.biblemgr = None
	
	def process(self, token, userdata, buf=""):
		self.token = token
		self.buf = buf
		self.success = SW.INHERITED
		self.u = userdata
	
		tag.setText("<%s>" % token)		
		which_one = "start_%s"
		if tag.isEndTag():
			which_one = "end_%s"
		method = getattr(self, which_one % tag.getName(), None)
		if method is not None:
			self.success = SW.SUCCEEDED		
			method(tag)

	def get_strongs_headword_from_headword_module(self, value):
		global strongs_cacher
		
		new_strongs_cacher = headwords_module
		
		if strongs_cacher != new_strongs_cacher:
			strongs_cache.clear()
		
		strongs_cacher = new_strongs_cacher

		
		if value in strongs_cache:
			return strongs_cache[value]
		
		#if not headwords_module:
		#	dprint(WARNING, "Mod is None")
		#	#self.success = SW.INHERITED
		#	#return
		
		match = strongs_re.match(value)
		if not match:
			dprint(WARNING, "Could not match lemma", value)
			return
	
		type, number, extra = match.groups()
		if type not in "HG":
			dprint(WARNING, "Unknown lemma", value)
			return

		orig_value = value
		
		num = int(number)
		# normalize
		value = "%s%04d" % (type, int(number))
		display_number = "%s%d" % (type, int(number))
		
		
		mod, modlang, last_item = dict(
			H=(strongshebrew, "Hebrew", last_hebrew),
			G=(strongsgreek, "Greek", last_greek)
		)[type]
		
		if extra:
			number += extra
			display_number += extra
			value_with_extra = value + extra
		
		else:
			value_with_extra = value
		
		if headwords_module:
			headwords_module.setKey(SW.Key(value_with_extra))

			# this MUST be in html/thml...
			word = headwords_module.getRawEntry()
		
			if headwords_module.getKeyText() not in (
				# if we can't find the value with the extra bit, ignore this
				value, value_with_extra
			):
				# don't report hebrew 00, as this is used throughout the KJV OT		
				if value != 'H0000':
					dprint(WARNING, "Could not find strong's headword", value)

				word = display_number

				#self.success = SW.INHERITED
				#return
		else:
			word = display_number

		#TODO handle extra...
		item = '<a class="strongs_headword" href="strongs://%s/%s">%s</a>' % (modlang, number, word)
		strongs_cache[value] = item
		
		
		return item
	
	get_strongs_headword = get_strongs_headword_from_headword_module

	def set_biblemgr(self, biblemgr):
		self.biblemgr = biblemgr

def clear_cache(biblemgr=None):
	global strongsgreek, strongshebrew, strongs_cache, last_greek, last_hebrew
	global strongs_cacher, headwords_module
	strongsgreek = None
	strongshebrew = None
	last_greek = None
	last_hebrew = None
	strongs_cache = {}
	strongs_cacher = None
	headwords_module = None
	
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
	
	# if this is our first try, we won't have loaded the config file
	# but we do this again later
	# if we are refreshing biblemgr, then we should load from config
	set_headwords_module_from_conf(biblemgr)


def set_headwords_module_from_conf(biblemgr):
	preferred = filter_settings["headwords_module"]
	
	if biblemgr.headwords_modules:
		modules = [(name, mod) for name, mod 
			in biblemgr.headwords_modules.items()
			if preferred == name]

		if modules:
			set_headwords_module(modules[0])
			return
		
	if biblemgr.headwords_modules and preferred:
		set_headwords_module(biblemgr.headwords_modules.items()[0])
	else:
		print "Setting to None"
		set_headwords_module(("", None))


def set_headwords_module(name_mod):
	global headwords_module
	name, mod = name_mod
	headwords_module = mod
	filter_settings["headwords_module"] = name 
		

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

def ellipsize(version, refs, last_text="", ellipsis=None, type="crossReference"):
	if ellipsis is None:
		ellipsis = filter_settings["footnote_ellipsis_level"]
	
	buf = []
	e = ""

	# ELLIPSIS BEHAVIOUR
	if(ellipsis):
	
		left_over = max(0, len(refs)-ellipsis)
		if left_over == 1:
			ellipsis += 1
			left_over = 0

		for item in refs[:ellipsis]:
			internal_ref = pysw.VerseList(item, last_text).GetBestRange(True)
			internal_ref = SW.URL.encode(internal_ref).c_str()
			ref = pysw.VerseList(item, last_text).GetBestRange(True,
				userOutput=True)
			last_text = ref
			buf.append('<a href="newbible://content/passagestudy.jsp?action=showRef&type=scripRef&module=%(version)s&value=%(internal_ref)s">%(ref)s</a>'% locals())
		if(left_over):
			parameters = "action=showMultiRef&values=%d" % left_over
			for idx, item in enumerate(refs[ellipsis:]):
				ref = pysw.VerseList(item, last_text).GetBestRange(True)
				last_text = ref
			
				parameters += "&val%d=%s" % (idx, ref)

			e = '<b><a href="newbible://content/passagestudy.jsp?%s">...</a></b>' % SW.URL.encode(parameters).c_str()
		refs = []
		
	
	# DEFAULT BEHAVIOUR
	for item in refs:
		ref = pysw.VerseList(item, last_text).GetBestRange(True,
			userOutput=True)
		internal_ref = pysw.VerseList(item, last_text).GetBestRange(True)
		
		last_text = ref
		buf.append('<a href="bible:%(internal_ref)s">%(ref)s</a>'% locals())

	if ellipsis and left_over:
		buf.append(e)

	i = " ".join(buf)

	return ' <span class="crossreference">%s</span> ' % i.encode("utf8")
