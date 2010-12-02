from swlib.pysw import SW
from backend.bibleinterface import biblemgr
from tooltip import TextTooltipConfig, StrongsTooltipConfig

from util.debug import *
from util import noop
from util.unicode import to_unicode, to_str
from gui.webconnect_protocol_handler import get_url_host_and_page
from gui import guiutil
import guiconfig
import wx


class ProtocolHandler(object):
	def __init__(self):
		self.hover = {}
		self.protocols = {}
		#self.hover.name = "hovering"
		#self.hover.protocols = "opening link"
		
	def register_hover(self, protocol, handler):
		self.hover[protocol] = handler
	
	def register_handler(self, protocol, handler):
		self.protocols[protocol] = handler
		
	def on_hover(self, frame, href, x, y):
		self._handle(self.hover, frame, href, x, y)
	
	def on_link_opened(self, frame, href):
		self._handle(self.protocols, frame, href)
	
	def _handle(self, d, frame, href, *args):
		url = SW.URL(str(href))
		protocol = url.getProtocol()
		# don't decode if no protocol, or : in decoded may become the protocol
		if protocol:
			href = SW.URL.decode(str(href)).c_str()
			url = SW.URL(href)
			protocol = url.getProtocol()
		
		if protocol in d:
			d[protocol](frame, href, url, *args)
		else:
			dprint(WARNING, 
				"Protocol %s has no handler" % protocol,
				href)

protocol_handler = ProtocolHandler()

def on_web_opened(frame, href, url):
	guiutil.open_web_browser(href)

for item in ("http", "https", "ftp"):
	protocol_handler.register_handler(item, on_web_opened)
	protocol_handler.register_hover(item, noop)

def find_frame(module):
	for frame in guiconfig.mainfrm.frames:
		if hasattr(frame, "book") and frame.book.ModuleExists(module):
			return frame

def on_sword_opened(frame, href, url):
	module = url.getHostName()
	key = SW.URL.decode(url.getPath()).c_str()
	frame = find_frame(module)
	if not frame:
		return
	
	guiconfig.mainfrm.set_module(module, frame.book)
	
	frame.SetReference_from_string(
		to_unicode(
			key,
			frame.book.mod,
		)
	)
	

def on_sword_hover(frame, href, url, x, y):
	tooltip_config = TextTooltipConfig("", mod=None)

	module = url.getHostName()
	key = SW.URL.decode(url.getPath()).c_str()
	
	f = find_frame(module)
	if f:
		mod = biblemgr.get_module(module)
		mod.KeyText(key)
		
		ref = to_unicode(mod.getKeyText(), mod)
		ref = f.format_ref(mod, ref)
		text = mod.RenderText()

		tooltip_config.module = mod
		tooltip_config.text = ("%s (%s)<br>%s" % (
			ref, mod.Name(), text
		))
	else:
		tooltip_config.text = (
			_("The book '%s' is not installed, "
				"so you cannot view "
				"details for this entry (%s)") % (module, key))

	frame.show_tooltip(tooltip_config)

protocol_handler.register_handler("sword", on_sword_opened)
protocol_handler.register_hover("sword", on_sword_hover)

def on_strongs_click(frame, href, url):
	dictionary = biblemgr.dictionary		
	type = url.getHostName() #Hebrew or greek
	value = url.getPath() #strongs number
	type = "Strongs"+type #as module is StrongsHebrew or StrongsGreek
	if biblemgr.dictionary.ModuleExists(type):
		guiconfig.mainfrm.set_module(type, biblemgr.dictionary)
		wx.CallAfter(guiconfig.mainfrm.UpdateDictionaryUI, value)

	if not type or not value: 
		print "Not type or value", href
		return

def on_strongs_hover(frame, href, url, x, y):
	dictionary = biblemgr.dictionary		
	type = url.getHostName() #Hebrew or greek
	value = url.getPath() #strongs number
	if not type or not value: 
		print "Not type or value", href
		return

	frame.show_tooltip(StrongsTooltipConfig(type, value))

protocol_handler.register_handler("strongs", on_strongs_click)
protocol_handler.register_hover("strongs", on_strongs_hover)

def on_bpbible_hover(frame, href, url, x, y):
	from new_displayframe import DisplayFrame
	host, page = get_url_host_and_page(href)
	assert host == "content"
	d = page.split("/", 3) + ['','','']
	type, module, p = d[:3]
	passage, query = (p.split("?", 1) + [''])[:2]

	if type != "page":
		print "Unhandled bpbible link", href
		return

	if passage != "passagestudy.jsp":
		print "Unhandled bpbible link", href

	u = SW.URL(p.replace(":", '%3A'))
	return DisplayFrame.on_hover(frame, p, u, x, y)

def on_bpbible_click(frame, href, url):
	from new_displayframe import DisplayFrame
	host, page = get_url_host_and_page(href)
	assert host == "content"
	d = page.split("/", 3) + ['','','']
	type, module, p = d[:3]
	passage, query = (p.split("?", 1) + [''])[:2]

	if type != "page":
		print "Unhandled bpbible link", href
		return

	if passage != "passagestudy.jsp":
		print "Unhandled bpbible link", href

	u = SW.URL(p.replace(":", '%3A'))
	return DisplayFrame.on_link_clicked(frame, p, u)

protocol_handler.register_handler("bpbible", on_bpbible_click)
protocol_handler.register_hover("bpbible", on_bpbible_hover)

	
