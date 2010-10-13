import wx.wc
from backend.bibleinterface import biblemgr
from swlib.pysw import SW, VK, SW_URL_Encode, SW_URL_Decode
import os
import config
from util.debug import dprint, ERROR, MESSAGE, is_debugging
from display_options import all_options, get_js_option_value
from util.string_util import convert_rtf_to_html
from util.unicode import try_unicode, to_unicode
from util import languages, default_timer
import urlparse

counter = 0

class MasterProtocolHandler(wx.wc.ProtocolHandler):
	def _breakup_url(self, url):
		parsed_url = urlparse.urlsplit(url)
		if parsed_url.netloc:
			url_host = parsed_url.netloc
			page = parsed_url.path.lstrip('/')
		else:
			temp = parsed_url.path.lstrip('/')
			d = temp.split("/", 1)
			url_host = d[0]
			assert len(d) > 1, "No path for protocol handler."
			page = str(d[1])

		assert url_host == "content", \
			"only content is supported at the moment..."

		d = page.split("/", 1)
		if len(d) == 1:
			d.append('')

		protocol, path = d
		
		assert protocol in handlers, \
			"No handler for host type %s" % protocol

		return protocol, path

	def GetContentType(self, url):
		protocol, path = self._breakup_url(url)
		return unicode(handlers[protocol].get_content_type(path))

	def GetContent(self, url):
		dprint(MESSAGE, "GetContent called for url:", url)
		protocol, path = self._breakup_url(url)
		return unicode(handlers[protocol].get_document(path))

BASE_HTML = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" 
                      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="%(lang)s">
<head>
	%(head)s
</head>
<body %(bodyattrs)s>
	<div id="content" class="%(contentclass)s">
	<!-- <p> -->
	%(content)s
	<!-- </p> -->
	</div>
	%(timer)s
</body></html>'''

class ProtocolHandler(object):
	def get_content_type(self, path):
		return 'text/html'
	
	def get_document(self, path):
		return "No content specified"
	
	def _get_html(self, module, content, bodyattrs="", timer="", 
		stylesheets=[], scripts=[], contentclass=""):
		resources = []
		skin_prefixs = ["css", "css"]
		script_prefixs = ["js", "js"]

		### Should we keep using the file:/// protocol?
		### For the XUL port we intended to switch to using the chrome:/// protocol.
		prefixs = ["file:///" + os.getcwd() + "/"]
		for skin_prefix, script_prefix, prefix \
				in zip(skin_prefixs, script_prefixs, prefixs):
			for item in stylesheets:
				if "://" in item:
					resources.append('<link rel="stylesheet" type="text/css" href="%s"/ >' % (item))
				else:
					resources.append('<link rel="stylesheet" type="text/css" href="%s/%s/%s"/ >' % (prefix, skin_prefix, item))
			for item in scripts:
				resources.append('<script type="text/javascript" src="%s/%s/%s"></script>' % (prefix, script_prefix, item))

		text = BASE_HTML % dict(
			lang=module.Lang(),
			head='\n'.join(resources),
			bodyattrs=bodyattrs, 
			content=content, 
			timer=timer,
			contentclass=contentclass)
		
		try:
			global counter
			counter += 1
			filename = "generated_html/tmp%d.html" % counter
			open(filename, "w").write(text.encode("utf8"))
		except Exception, e:
			print "Error writing tmp.html", e
		return text


class NullProtocolHandler(ProtocolHandler):
	def get_document(self, path):
		return "<html><body>Content not loaded</body></html>"

class PageProtocolHandler(ProtocolHandler):
	bible_stylesheets = ("bpbible_html.css", "bpbible_chapter_view.css", 
						"bpbible://content/quotes_skin/")
	def _get_document_parts(self, path):
		ref = SW_URL_Decode(path)
		assert ref, "No reference"

		module_name, ref = ref.split("/", 1)
		ref = ref.decode("utf8")
		return self._get_document_parts_for_ref(module_name, ref)

	def _get_document_parts_for_ref(self, module_name, ref, do_current_ref=True):
		import time
		t = default_timer()

		stylesheets = list(self.bible_stylesheets)
		scripts = ["jquery-1.3.2.js", "highlight.js", "bpbible_html.js",
				  "hyphenate.js", "columns.js"]

		book = biblemgr.get_module_book_wrapper(module_name)
		assert book, "Module wrapper not found for book " + module_name
		module = book.mod
		if book.chapter_view:
			scripts.append("bpbible_html_chapter_view.js")
			#stylesheets.append("bpbible_chapter_view.css")
			#stylesheets.append("bpbible://content/quotes_skin/")
		else:
			scripts.append("bpbible_html_page_view.js")
			stylesheets.append("bpbible_page_view.css")			
	
		if is_debugging():
			stylesheets.append("bpbible_html_debug.css")

		if book.is_verse_keyed:
			if book.chapter_view:
				if do_current_ref:
					c = book.GetChapter(ref, ref, config.current_verse_template)
				else:
					c = book.GetChapter(ref)

				ref_id = VK(ref).get_book_chapter()
				
			else:
				c = book.GetReference(ref, headings=True)
				ref_id = ref


		elif book.is_dictionary:
			c = book.GetReference(ref)
			ref_id = ref

		elif book.is_genbook:
			c = book.GetReference(ref)
			ref_id = ref
		else:
			dprint(ERROR, "Book `%s' not found." % module_name)
			c = ''
		c = c.replace("<!P>", "</p><p>")

		clas = ""
		if not c:
			clas = " nocontent"

		c = '<div class="segment%s" ref_id="%s">%s</div>' % (clas, SW_URL_Encode(ref_id), c)

		return dict(
			module=module, content=c,
			bodyattrs=self._get_body_attrs(module),
			stylesheets=stylesheets,
			scripts=scripts,
			timer="<div class='timer'>Time taken: %.3f (ref_id %s)</div>" % (default_timer() - t, ref_id))

	def _get_body_attrs(self, module):
		options = []
		for option in all_options():
			options.append((option, get_js_option_value(option)))

		options.append(("module", module.Name()))
		dir = {
			SW.DIRECTION_BIDI: "bidi",
			SW.DIRECTION_LTR:  "ltr",
			SW.DIRECTION_RTL:  "rtl",
		}.get(ord(module.Direction()))

		if not dir: 
			print "Unknown text direction"
			dir = "ltr"

		options.append(("dir", dir))
		return ' '.join('%s="%s"' % option for option in options)
	
	
	def get_document(self, path):
		#print "Getting document", path
		d = self._get_document_parts(path)
		d["content"] = '<div class="page_segment" id="original_segment">%s</div>' % d["content"]
		d["contentclass"] = "chapterview"
		return self._get_html(**d)

class PageFragmentHandler(PageProtocolHandler):
	def get_document(self, path):
		#print "GET DOCUMENT"
		ref = SW_URL_Decode(path)
		#print "GET FRAGMENT", ref
		#assert ref.count("/") == 2, "Should be two slashes in a fragment url"

		#print "REF was", ref
		module_name, rest = ref.split("/", 1)
		ref, direction = rest.rsplit("/", 1)
		assert direction in ("next", "previous")
		#print module_name, ref, direction

		dir = {"next": 1, "previous": -1}[direction]
		book = biblemgr.get_module_book_wrapper(module_name)
		mod = book.mod		
		no_more = False
		if book.is_verse_keyed:
			vk = VK(ref, headings=not book.chapter_view)
			if book.chapter_view:
				vk.chapter += dir
				if vk.Error():
					print "No more in that direction", dir
					no_more = True
				else:
				
					# go back just a little, so that when we go forward on the module
					# we won't overshoot... (at least, that is our plan - we hope it
					# won't be baffled...)
					vk.Verse(vk.Verse() - dir)
					if vk.Error():
						print "VK had an error taking away a verse", dir
	
			if not no_more:
				old_mod_skiplinks = mod.getSkipConsecutiveLinks()
				mod.setSkipConsecutiveLinks(True)
				try:
					vk.Persist(1)
					mod.setKey(vk)
					#print repr(mod.Error())
					mod.increment(dir)

					if mod.Error() != '\x00':
						print "Mod had an error"
						no_more = True
					else:
						if book.chapter_view:
							new_ref = vk.get_book_chapter()
						else:
							new_ref = vk.text
				finally:
					mod.setKey(SW.Key())
					mod.setSkipConsecutiveLinks(old_mod_skiplinks)
		
		elif book.is_dictionary:
			# XXX: Would using an index rather than a reference (as the XUL code did) be more efficient?
			book.snap_text(ref)
			book.mod.increment(dir)
			if mod.Error() == '\x00' and book.mod.getKey().getText():
				new_ref = book.mod.getKey().getText().decode("utf8")
			else:
				no_more = True
			
		elif book.is_genbook:
			ref = "/" + ref
			tk = book.GetKey()
			tk.Persist(1)
			assert tk.thisown
			newtk = book.GetKey()
			newtk.thisown = True
			mod.setKey(tk)
			print "Getting next for", ref
			tk.setText(ref)
			print tk.getText()
			if mod.Error() != '\x00':
				print "Error on initial set?"
			mod.increment(dir)
			if mod.Error() == '\x00' and tk.getText():
				new_ref = to_unicode(tk.getText(), mod)[1:] # trim off the leading /
			else:
				no_more = True
			
			mod.setKey(newtk)
		else:
			print "Book type not handled", module_name
		
		if no_more:
			return '''
			<div class="page_segment" empty="true">
				<div class='no_more_text end-%(end)s'>
					You are at the %(end)s of this book
				</div>
			</div>''' % dict(end={
				-1: "start",
				 1: "end",
			}[dir])
		
		return '<div class="page_segment">%(content)s%(timer)s</div>' % self._get_document_parts_for_ref(module_name, new_ref, do_current_ref=False)
	
class ModuleInformationHandler(ProtocolHandler):
	def get_document(self, path):
		module_name = SW_URL_Decode(path)

		book = biblemgr.get_module_book_wrapper(module_name)
		if not book:
			dprint(ERROR, "Book `%s' not found." % module_name)
			return "Error: Book `%s' not found." % module_name

		module = book.mod
		
		rows = []
		t = u"<table class='module_information'>%s</table>"
		for key, value in (
			("Name", module.Name()), 
			("Description", module.Description()),
			("Language", languages.get_language_description(module.Lang())),
			("License", module.getConfigEntry("DistributionLicense")),
			("About", module.getConfigEntry("About")), 
		):
			rows.append('''
			<tr>
				<th class="module_information_key">%s</th>
				<td class="module_information_value">%s</td>
			</tr>''' % (
				key, convert_rtf_to_html(try_unicode(value, module))
			))

		t %= ''.join(rows)

		return self._get_html(module, t, stylesheets=["book_information_window.css"])
	
class QuotesHandler(ProtocolHandler):
	def get_content_type(self, path):
		return 'text/css'
	
	def get_document(self, path):
		import quotes
		style, mapping = quotes.get_quotes()
		return style

class TooltipConfigHandler(PageProtocolHandler):
	registered = {}
	upto = 0

	@classmethod
	def register(cls, config):
		cls.upto += 1
		k = str(cls.upto)
		cls.registered[k] = config
		return "bpbible://content/tooltip/%s" % k

	def get_document(self, path):
		config = self.registered.pop(path)
		return self._get_html(config.get_module(), config.get_text(),
				stylesheets=self.bible_stylesheets,
				bodyattrs=self._get_body_attrs(config.get_module()))

handlers = {
	"page": PageProtocolHandler(), 
	'pagefrag': PageFragmentHandler(),
	'': NullProtocolHandler(),
	'moduleinformation': ModuleInformationHandler(),
	'quotes_skin': QuotesHandler(),
	'tooltip': TooltipConfigHandler(),
	# wxWebConnect always wants to get a favicon for a domain.
	# This handler prevents exceptions when the favicon is requested.
	'favicon.ico': ProtocolHandler(),
}

