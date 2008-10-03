import wx
from swlib.pysw import TK
from bookframe import BookFrame
import genbooktree
from backend.bibleinterface import biblemgr
from util import string_util, noop
from util.debug import dprint, WARNING
from util.unicode import to_unicode
from protocols import protocol_handler
from swlib.pysw import SW


import config
import guiconfig

def on_genbook_click(frame, href, url):
	if frame != guiconfig.mainfrm.genbooktext:
		frame = guiconfig.mainfrm.genbooktext

	if url is None:
		url = SW.URL(href)
	
	host = to_unicode(
		url.getHostName(),
		frame.reference.module
	)

	if host == "previous":
		frame.chapter_back()

	elif host == "next":
		frame.chapter_forward()

	elif host.startswith("parent"):
		frame.go_to_parent(int(host[6:]))
	
	else:
		key = TK(frame.book.mod.getKey(), frame.book.mod)
		path = to_unicode(
			url.getPath(),
			frame.reference.module
		)
		ref = u"/%s" % host
		if path:
			ref += "/%s" % path
		key.text = ref
		
		frame.go_to_key(key)


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
		self.reference_text = None
		
		
	
	def SetReference(self, ref, context=None):
		self.reference = ref
		
		if isinstance(ref, basestring) and ref == "<empty>":
			if self.book.mod is None:
				data = config.MODULE_MISSING_STRING
			else:
				data = """This book is empty"""

			self.reference_text = "<empty>"
			
				
			self.SetPage(data)
			self.update_title()
			return
		
		self.reference_text = self.reference.text
		
		root, display_children = self.book.get_display_level_root(ref)

		if not display_children:
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

			breadcrumb = [string_util.htmlify_unicode(b) 
				for b in breadcrumb]

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
			

			text = self.book.GetReference(ref, context = context)
			data += text
		else:
			items = []
			def add_items(key):
				anchor = ""
				bgcolor = ""
				if key.equals(ref):
					bgcolor = ' bgcolor="#9999ff"'
					anchor = '<a name="current" href="#current">%s</a>' % key
				else:
					anchor = '<a href="genbook:%s">%s</a>' % (
						SW.URL.encode(key.getText()).c_str(), key,
					)
					
					
					
				items.append(
					'<table width=100%% cellspacing=0 cellpadding=0>'
					'<tr%s><td colspan=2px><b>%s</b>:%s</td></tr>'
					% (bgcolor, anchor, self.book.GetReference(key))
				)
				items.append("</table>")
				items.append(
					"<table width=100% cellspacing=0 cellpadding=0>"
				)

				for child in key:
					items.append("<tr><td width=20px></td><td>")
					add_items(child)
					items.append("</td></tr>")

				items.append("</table>")

			add_items(root)
			data = ''.join(items)


		data = data.replace("<!P>","</p><p>")

		self.SetPage(data)
		if display_children:
			self.scroll_to_current()
		
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

	def go_to_key(self, key):
		mod = self.book.mod
		if not mod: 
			return

		self.genbooktree.go_to_key(key)
	
	def get_window(self):
		return self.genbookpanel


	def on_genbook_change(self, event):
		self.SetReference(
			self.genbooktree.tree.GetPyData(self.genbooktree.popup.value)[0]
		)

	def genbook_version_changed(self, newversion):
		self.genbooktree.SetBook(biblemgr.genbook, self.reference_text)
