from backend.bibleinterface import biblemgr
from backend.book import get_module_css_text_direction
from swlib.pysw import SW, VK
import os
import config
import guiconfig
from util.debug import dprint, ERROR, is_debugging
from display_options import all_options, get_js_option_value
from util.string_util import convert_rtf_to_html
from util.unicode import try_unicode, to_unicode
from util import languages, default_timer
import urllib
from gui.htmlbase import convert_language
import json

counter = 0

BASE_HTML = '''\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" 
                      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="%(lang)s">
<head>
	<meta http-equiv='Content-Type' content='text/html; charset=utf-8'>
	%(head)s
</head>
<body lang="%(lang)s" %(bodyattrs)s>
	%(content)s
	%(timer)s
</body></html>'''

class ProtocolHandler(object):
	def get_content_type(self, path):
		return 'text/html'
	
	def get_document(self, path):
		return "No content specified"
	
	def _get_html(self, module, content, bodyattrs="", timer="", 
		stylesheets=[], scripts=[], javascript_block="", styles="", contentclass="",
		include_wrapper_divs=True):
		resources = []

		### Should we keep using the file:/// protocol?
		### For the XUL port we intended to switch to using the chrome:/// protocol.
		prefix = "file:///" + os.getcwd() + "/"
		css_dir = "css"
		script_dir = "js"
		for item in stylesheets:
			if "://" in item:
				resources.append('<link rel="stylesheet" type="text/css" href="%s"/ >' % (item))
			else:
				resources.append('<link rel="stylesheet" type="text/css" href="%s/%s/%s"/ >' % (prefix, css_dir, item))

		for item in scripts:
			resources.append('<script type="text/javascript" src="%s/%s/%s"></script>' % (prefix, script_dir, item))

		if styles:
			resources.append('<style type="text/css">%s</style>' % styles)

		if javascript_block:
			resources.append('<script type="text/javascript">%s</script>' % javascript_block)

		if include_wrapper_divs:
			content = '<div id="content" class="%(contentclass)s">\n%(content)s\n</div>' % locals()

		text = BASE_HTML % dict(
			lang=module.Lang() if module else "en",
			head='\n'.join(resources),
			bodyattrs=bodyattrs, 
			content=content, 
			timer=timer)

		if is_debugging():
			self.log_generated_html(text)

		return text
		
	def log_generated_html(self, text):
		if not os.path.isdir('generated_html'):
			return

		try:
			global counter
			counter += 1
			filename = "generated_html/tmp%d.html" % counter
			open(filename, "w").write(text.encode("utf8"))
		except Exception, e:
			print "Error writing tmp.html", e


class NullProtocolHandler(ProtocolHandler):
	def get_document(self, path):
		return "<html><body>Content not loaded</body></html>"

class PageProtocolHandler(ProtocolHandler):
	bible_stylesheets = ("bpbible_html.css", "bpbible_chapter_view.css", 
						"passage_tag.css",
						"bpbible://content/quotes_skin/",
						"bpbible://content/fonts/")
	standard_scripts = ["contrib/jquery-1.6.1.js", "contrib/jquery.waitforimages.js", "utils.js"]
	bible_scripts = ["bpbible_strongs.js"]

	def _get_html(self, module, content, bodyattrs="", timer="", 
		stylesheets=[], scripts=[], javascript_block="", styles="", contentclass="",
		include_wrapper_divs=True):
		if not scripts:
			scripts = self.standard_scripts

		return super(PageProtocolHandler, self)._get_html(
			module, content, bodyattrs, timer, 
			stylesheets, scripts, javascript_block, styles, contentclass,
			include_wrapper_divs)

	def _get_document_parts(self, path):
		module_name, ref = path.split("/", 1)
		assert ref, "No reference"

		return self._get_document_parts_for_ref(module_name, ref)

	def _get_document_parts_for_ref(self, module_name, ref, do_current_ref=True):
		t = default_timer()

		stylesheets = list(self.bible_stylesheets)
		scripts = self.standard_scripts + self.bible_scripts + ["highlight.js", "bpbible_html.js", "contrib/hyphenate.js", "columns.js"]

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

				ref_id = VK(ref).get_chapter_osis_ref()
				
			else:
				c = book.GetReference(ref, headings=True)
				ref_id = VK(ref).getOSISRef()


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

		lang = module.Lang() if module else "en",
		c = convert_language(c, lang)
		c = '<div class="segment%s" ref_id="%s">%s</div>' % (clas, urllib.quote(ref_id.encode("utf8")), c)

		return dict(
			module=module, content=c,
			bodyattrs=self._get_body_attrs(module),
			stylesheets=stylesheets,
			scripts=scripts,
			timer="<div class='timer'>Time taken: %.3f (ref_id %s)</div>" % (default_timer() - t, ref_id))

	def _get_body_attrs(self, module, overrides=None):
		options = []
		for option in all_options():
			if overrides and option in overrides:
				options.append((option, overrides[option]))
			else:
				options.append((option, get_js_option_value(option)))

		if module: 
			options.append(("module", module.Name()))
		
		options.append(("dir", get_module_css_text_direction(module)))
		return ' '.join('%s="%s"' % option for option in options)
	
	
	def get_document(self, path):
		#print "Getting document", path
		d = self._get_document_parts(path)
		if d.get("include_wrapper_divs", True):
			d["content"] = '<div class="page_segment" id="original_segment">%s</div>' % d["content"]
		d["contentclass"] = "chapterview"
		return self._get_html(**d)

class PageFragmentHandler(PageProtocolHandler):
	def get_document(self, path):
		module_name, rest = path.split("/", 1)
		ref, direction = rest.rsplit("/", 1)
		assert direction in ("next", "previous")

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
							new_ref = vk.get_chapter_osis_ref()
						else:
							new_ref = vk.getOSISRef()
				finally:
					mod.setKey(SW.Key())
					mod.setSkipConsecutiveLinks(old_mod_skiplinks)
		
		elif book.is_dictionary:
			# XXX: Would using an index rather than a reference (as the XUL code did) be more efficient?
			book.snap_text(ref)
			book.mod.increment(dir)
			if mod.Error() == '\x00' and book.mod.getKey().getText():
				new_ref = to_unicode(mod.getKey().getText(), mod)
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
			tk.set_text(ref)
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
			message = (_("You are at the start of this book.") if dir == -1
				else _("You are at the end of this book."))
			class_name = "book-%s" % ("start" if dir == -1 else "end")
			return '''
			<div class="page_segment" empty="true">
				<div class='no_more_text %(class_name)s'>
					%(message)s
				</div>
			</div>''' % locals()
		
		return '<div class="page_segment">%(content)s%(timer)s</div>' % self._get_document_parts_for_ref(module_name, new_ref, do_current_ref=False)
	
class ModuleInformationHandlerBase(ProtocolHandler):
	config_entries_to_ignore = ["Name", "Description", "DistributionLicense", "UnlockURL", "ShortPromo", "Lang", "About"]

	def _get_moduleinfo(self, module):
		rows = []
		name = u"%s - %s" % (module.Name(), to_unicode(module.Description(), module))
		default_items = (
			("Name", name),
			("Language", languages.get_language_description(module.Lang())),
			("License", self.get_formatted_config_entry(module, "DistributionLicense")),
			("Unlock", self.get_formatted_unlock_url(module)),
			("More", self.get_formatted_config_entry(module, "ShortPromo")),
			("About", self.get_formatted_config_entry(module, "About")),
		)
		for key, value in default_items:
			if value:
				rows.append('''
				<tr>
					<th class="module_information_key">%s</th>
					<td class="module_information_value">%s</td>
				</tr>''' % (key, value))

		html, javascript = self.add_additional_config_entries(module)
		rows.append(html)
		table = u"<table class='module_information'>%s</table>" % (''.join(rows))

		return self._get_html(module, table, stylesheets=["book_information_window.css"],
				scripts=PageProtocolHandler.standard_scripts, javascript_block=javascript)

	def add_additional_config_entries(self, module):
		config_map = self.get_config_map(module)

		config_file_options = ''.join('<option value="%s">%s</option>' % (index, name) for index, (name, value) in enumerate(config_map))
		html = '''
		<tr>
			<td class="config_file_entries_combo">
				<select name="config_file_entries" id="config_file_entries">%s</select>
			</td>
			<td class="module_information_value" id="current_config_file_entry"></td>
		</tr>''' % config_file_options

		javascript = """
			var config_entry_values = %s;

			function on_config_file_entry_changed()	{
				var new_entry_index = document.getElementById("config_file_entries").selectedIndex;
				$("#current_config_file_entry").html(config_entry_values[new_entry_index]);
			}

			$(document).ready(function() {
				$("#config_file_entries").change(on_config_file_entry_changed);
				on_config_file_entry_changed();
			});
		""" % json.dumps([value for key, value in config_map])

		return html, javascript

	def get_formatted_config_entry(self, module, entry):
		value = module.getConfigEntry(entry)
		return convert_rtf_to_html(try_unicode(value, module))

	def get_formatted_unlock_url(self, module):
		unlock_url = self.get_formatted_config_entry(module, "UnlockURL")
		if not unlock_url:
			return ""

		message = _('Click here to unlock this book')
		return u'<a href="%s">%s</a>' % (unlock_url, message)

	def get_config_map(self, module):
		return [
			(
				item.c_str(), 
				convert_rtf_to_html(try_unicode(value.c_str(), module))
			)
			for item, value in module.getConfigMap().items()
			if item.c_str() not in self.config_entries_to_ignore
		]
	
class ModuleInformationHandler(ModuleInformationHandlerBase):
	def get_document(self, path):
		module_name = path

		book = biblemgr.get_module_book_wrapper(module_name)
		if not book:
			dprint(ERROR, "Book `%s' not found." % module_name)
			return "Error: Book `%s' not found." % module_name

		module = book.mod
		return self._get_moduleinfo(module)
	
class ModuleInformationHandlerModule(ModuleInformationHandlerBase):
	# Used in install_module for modules which aren't in the standard
	# hierarchy
	registered = {}
	upto = 0

	@classmethod
	def register(cls, config):
		cls.upto += 1
		k = str(cls.upto)
		cls.registered[k] = config
		return "bpbible://content/moduleinformationmodule/%s" % k

	def get_document(self, path):
		module = self.registered.pop(path)
		return self._get_moduleinfo(module)
		
class QuotesHandler(ProtocolHandler):
	def get_content_type(self, path):
		return 'text/css'
	
	def get_document(self, path):
		import quotes
		style, mapping = quotes.get_quotes()
		return style
	
class FontsHandler(ProtocolHandler):
	def get_content_type(self, path):
		return 'text/css'
	
	def get_document(self, path):
		from gui import fonts
		return fonts.get_css()

class TooltipConfigHandler(PageProtocolHandler):
	registered = {}
	upto = 0

	@classmethod
	def register(cls, config):
		cls.upto += 1
		k = str(cls.upto)
		cls.registered[k] = config
		return "bpbible://content/tooltip/%s" % k

	def _get_document_parts(self, path):
		config = self.registered.pop(path)
		bg, textcolour = guiconfig.get_tooltip_colours()
		style = """
body {
	background-color: %s;
	color: %s
}
""" % (bg, textcolour)
		text = config.get_text()
		text = '<div class="segment">%s</div>' % (text)
		bodyattrs = self._get_body_attrs(config.get_module(),
			overrides = {"columns": "false"}
		)
		return dict(module=config.get_module(), content=text,
				stylesheets=self.bible_stylesheets,
				bodyattrs=bodyattrs,
				styles=style)

class FragmentHandler(PageProtocolHandler):
	registered = {}
	upto = 0

	@classmethod
	def register(cls, text, module, include_wrapper_divs):
		cls.upto += 1
		k = str(cls.upto)
		cls.registered[k] = text, module, include_wrapper_divs
		return "bpbible://content/fragment/%s" % k

	def _get_document_parts(self, path):
		text, module, include_wrapper_divs = self.registered.pop(path)

		scripts = self.standard_scripts
		if include_wrapper_divs:
			scripts = scripts + self.bible_scripts
			stylesheets = self.bible_stylesheets
		else:
			stylesheets = ()

		return dict(module=module, content=text,
				stylesheets=stylesheets,
				scripts=scripts,
				bodyattrs=self._get_body_attrs(module),
				include_wrapper_divs=include_wrapper_divs)

handlers = {
	"page": PageProtocolHandler(), 
	'pagefrag': PageFragmentHandler(),
	'fragment': FragmentHandler(),
	'': NullProtocolHandler(),
	'moduleinformation': ModuleInformationHandler(),
	'moduleinformationmodule': ModuleInformationHandlerModule(),
	'quotes_skin': QuotesHandler(),
	'fonts': FontsHandler(),
	'tooltip': TooltipConfigHandler(),
}

