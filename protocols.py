from swlib.pysw import SW

from util.debug import *
from util import noop
from gui import guiutil


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
