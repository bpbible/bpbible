import wx.wc
import protocol_handlers
from util.debug import dprint, ERROR, MESSAGE
import urlparse, urllib

def get_url_host_and_page(url):
	parsed_url = urlparse.urlsplit(url)
	if parsed_url.netloc:
		url_host = parsed_url.netloc
		page = str(parsed_url.path.lstrip('/'))
	else:
		temp = parsed_url.path.lstrip('/')
		d = temp.split("/", 1)
		url_host = d[0]
		assert len(d) > 1, "No path for protocol handler."
		page = str(d[1])
	
	page = urllib.unquote(page)
	page = page.decode("utf8")
	
	return url_host, page

class MasterProtocolHandler(wx.wc.ProtocolHandler):
	def _breakup_url(self, url):
		url_host, page = get_url_host_and_page(url)

		assert url_host == "content", \
			"only content is supported at the moment..."

		d = page.split("/", 1)
		if len(d) == 1:
			d.append('')

		protocol, path = d
		
		assert protocol in protocol_handlers.handlers, \
			"No handler for host type %s" % protocol

		return protocol, path

	def GetContentType(self, url):
		protocol, path = self._breakup_url(url)
		return unicode(protocol_handlers.handlers[protocol].get_content_type(path))

	def GetContent(self, url):
		try:
			dprint(MESSAGE, "GetContent called for url:", url)
			protocol, path = self._breakup_url(url)
			return unicode(protocol_handlers.handlers[protocol].get_document(path))
		except Exception, e:
			dprint(ERROR, "EXCEPTION in GetContent")
			import traceback
			traceback.print_exc()
			raise
