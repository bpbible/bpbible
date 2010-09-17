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
from util.i18n import N_


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
	id=N_("Other Books")
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
		biblemgr.genbook.cleanup_module += self.cleanup_module
		guiconfig.mainfrm.on_close += lambda:biblemgr.genbook.observers.remove(
			self.genbook_version_changed
		)
		guiconfig.mainfrm.on_close += lambda:biblemgr.genbook.cleanup_module.remove(
			self.cleanup_module
		)
		
		self.reference_text = None
		
		
	def cleanup_module(self, module):
		if self.book.mod == module:
			print "CLEANING"
			# clean up all our TK's
			self.reference = "<empty>"
			self.reference_text = "<empty>"

			self.genbooktree.tree.DeleteChildren(self.genbooktree.tree.RootItem)
			self.genbooktree.value = None

	def SetReference(self, ref, context="", settings_changed=False):
		if isinstance(ref, TK):
			ref = TK(ref)
		self.reference = ref
		
		if isinstance(ref, basestring) and ref == "<empty>":
			if self.book.mod is None:
				data = config.MODULE_MISSING_STRING()
			else:
				data = """This book is empty"""

			self.reference_text = "<empty>"
			
			self.SetPage(data)
			self.update_title()
			return
		
		self.reference_text = self.reference.text
		self.OpenURI("bpbible://content/page/%s%s" % (self.book.version, self.reference_text))
		
		self.update_title()
	
	def SetReference_from_string(self, string):
		key = TK(self.book.mod.getKey(), self.book.mod)
		key.text = string
		self.go_to_key(key)

	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		version = self.book.version
		ref = self.reference
		
		text = "%s - %s (%s)" % (self.title, ref, version)
		m.set_pane_title(p.name, text)
	

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
	
	def format_ref(self, module, ref):
		k = TK(module.getKey(), module)
		k.text = ref		
		return k.breadcrumb(delimiter=">")

	def get_reference_textbox(self):
		return self.genbooktree
