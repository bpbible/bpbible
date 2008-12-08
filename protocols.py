from swlib.pysw import SW
from backend.bibleinterface import biblemgr

from util.debug import *
from util import noop
from util.unicode import to_unicode, to_str
from gui import guiutil
import guiconfig


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
	module = url.getHostName()
	key = SW.URL.decode(url.getPath()).c_str()
	
	f = find_frame(module)
	if f:
		f.mod.KeyText(key)
		
		ref = to_unicode(f.mod.getKeyText(), f.mod)
		ref = f.format_ref(f.mod, ref)
		text = f.mod.RenderText()

		frame.tooltip.SetText("%s (%s)<br>%s" % (
			ref, f.mod.Name(), text
		))
	else:
		frame.tooltip.SetText(
			_("The book '%s' is not installed, "
				"so you cannot view "
				"details for this entry (%s)") % (module, key))
		
	frame.show_tooltip(x, y)

protocol_handler.register_handler("sword", on_sword_opened)
protocol_handler.register_hover("sword", on_sword_hover)
