import wx
from swlib.pysw import TK
from bookframe import BookFrame
import genbooktree
from backend.bibleinterface import biblemgr
from util import string_util, noop
from util.debug import dprint, WARNING
from protocols import protocol_handler


import config

def on_genbook_click(frame, href, url):
	if url is None:
		url = SW.URL(href)
	
	host = url.getHostName()

	if host == "previous":
		frame.chapter_back()

	elif host == "next":
		frame.chapter_forward()

	elif host.startswith("parent"):
		frame.go_to_parent(int(host[6:]))
	
	else:
		dprint(WARNING, "Unknown genbook action", href)


protocol_handler.register_handler("genbook", on_genbook_click)
protocol_handler.register_hover("genbook", noop)	 

class GenBookFrame(BookFrame):
	title="Other Books"
	use_quickselector = False
	def __init__(self, parent, book):
		self.genbookpanel = wx.Panel(parent)
		super(GenBookFrame, self).__init__(self.genbookpanel)
		self.SetBook(book)

		self.genbooktree = genbooktree.GenBookTree(self.genbookpanel, 
				book, self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.genbooktree, flag = wx.GROW)
		sizer.Add(self, 3, flag = wx.GROW)
		self.genbookpanel.SetSizer(sizer)
		self.genbookpanel.Fit()
		self.genbooktree.Bind(wx.EVT_COMBOBOX, self.on_genbook_change)
		biblemgr.genbook.observers += self.genbook_version_changed
		
		
	
	def SetReference(self, ref, context=None):
		self.reference = ref
		if self.book.mod:
			before = self.genbooktree.get_item(-1)
			after = self.genbooktree.get_item(1)
			data = '<table width="100%" VALIGN=CENTER ><tr>'
			
			graphics = config.graphics_path

			if before:
				data += ('<td align="LEFT" valign=CENTER>'
						 '<a href="genbook:previous">'
						 '<img src="%(graphics)sgo-previous.png">&nbsp;'
						 '%(before)s</a></td>'
				) % locals()
			else:
				data += '<td align=LEFT>'+ '&nbsp;'*15 + '</td>'
						


			bref = TK(ref)
			breadcrumb = ['%s' % bref]
			item = 0

			while bref.parent():
				item += 1
				breadcrumb.append(
					'<a href="genbook:parent%d">%s</a>' % (item , bref)
				)
			
			breadcrumb[-1] = self.book.version

			breadcrumb = [string_util.htmlify_unicode(b) for b in breadcrumb]

			data += "<td align=CENTER><center><b>%s</b></center></td>" % \
				" &gt; ".join(reversed(breadcrumb))
			
			if after:
				data += ('<td align="RIGHT" valign=CENTER>'
						 '<a href="genbook:next">%(after)s&nbsp;'
						 '<img src="%(graphics)sgo-next.png">'
						 '</a></td>'
				) % locals()
			else:
				data += '<td align=RIGHT>'+ '&nbsp;'*15 + '</td>'

			data += "</tr></table>\n"
			

		
			text = self.book.GetReferenceFromKey(ref, context = context)
			data += text
			data = data.replace("<!P>","</p><p>")

		else:
			data = config.MODULE_MISSING_STRING
				
		self.SetPage(data)
		self.update_title()
		

	def chapter_move(self, amount):
		mod = self.book.mod
		if not mod: 
			return

		self.genbooktree.go(amount)

	def go_to_parent(self, amount):
		mod = self.book.mod
		if not mod: 
			return

		self.genbooktree.go_to_parent(amount)

	def get_window(self):
		return self.genbookpanel


	def on_genbook_change(self, event):
		self.SetReference(
			self.genbooktree.tree.GetPyData(self.genbooktree.popup.value)[0]
		)

	def genbook_version_changed(self, newversion):
		if newversion:
			key = TK(newversion.getKey(), newversion)
			key.root()
			self.SetReference(key)
		else:
			self.SetReference(None)

		self.genbooktree.SetBook(biblemgr.genbook)
	

