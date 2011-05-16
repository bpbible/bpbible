import wx
from swlib.pysw import TK, VK, VerseParsingError
from swlib.pysw import GetVerseStr, GetBestRange

from bookframe import BookFrame
import genbooktree
from backend.bibleinterface import biblemgr
from gui import guiutil
import versetree
from util import string_util, noop
from util.debug import dprint, WARNING
from util.unicode import to_unicode
from protocols import protocol_handler
from swlib.pysw import SW
import events


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

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.add_navigation_controls(sizer)
		sizer.Add(self, 3, flag = wx.GROW)
		self.genbookpanel.SetSizer(sizer)
		self.genbookpanel.Fit()
		self.genbooktree.Bind(wx.EVT_COMBOBOX, self.on_genbook_change)
		self.book.observers += self.genbook_version_changed
		self.book.cleanup_module += self.cleanup_module
		guiconfig.mainfrm.on_close += lambda:self.book.observers.remove(
			self.genbook_version_changed
		)
		guiconfig.mainfrm.on_close += lambda:self.book.cleanup_module.remove(
			self.cleanup_module
		)
		
		self.reference_text = None
		
	def add_navigation_controls(self, sizer):
		self.genbooktree = genbooktree.GenBookTree(self.genbookpanel, self.book, self)
		sizer.Add(self.genbooktree, flag=wx.GROW)
		
	def cleanup_module(self, module):
		if self.book.mod == module:
			print "CLEANING"
			# clean up all our TK's
			self.reference = "<empty>"
			self.reference_text = "<empty>"

			self.genbooktree.tree.DeleteChildren(self.genbooktree.tree.RootItem)
			self.genbooktree.value = None

	def SetReference(self, ref, settings_changed=False):
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
		# Remove the leading "/" from the key text so that we can construct a
		# proper URL.
		self.ChangeReference(self.reference_text[1:], settings_changed)
	
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

		# due to complex initialization with the bible reference changing and
		# the genbook tree being set up, we have to use CallAfter at least for
		# the first time (so easiest to do it for all)
		wx.CallAfter(self.genbooktree.go_to_key, key)
	
	def get_window(self):
		return self.genbookpanel


	def on_genbook_change(self, event):
		self.SetReference(
			self.genbooktree.tree.GetPyData(self.genbooktree.popup.value)[0]
		)

	def genbook_version_changed(self, newversion):
		self.genbooktree.SetBook(self.book, self.reference_text)
	
	def format_ref(self, module, ref):
		k = TK(module.getKey(), module)
		k.text = ref		
		return k.breadcrumb(delimiter=">")

	def get_reference_textbox(self):
		return self.genbooktree

class HarmonyFrame(GenBookFrame):
	id = N_("Harmony")
	has_menu = False
	allow_search = False
	def __init__(self, parent):
		super(HarmonyFrame, self).__init__(parent, biblemgr.harmony)

		# This reference is set to the latest reference that should be
		# displayed.  If the pane is hidden then it will not have been
		# displayed.
		self.latest_reference = ""
		# True if the settings have changed since the pane was hidden.
		self.settings_changed = False
		guiconfig.mainfrm.bible_observers += self.bible_ref_changed

	def add_navigation_controls(self, sizer):
		super(HarmonyFrame, self).add_navigation_controls(sizer)
		self.create_toolbar()
		sizer.Add(self.toolbar, flag=wx.GROW)

	def create_toolbar(self):
		self.toolbar = wx.ToolBar(self.genbookpanel, style=wx.TB_FLAT)
		self.create_toolbar_items()
		self.toolbar.Realize()
		self.toolbar.MinSize = self.toolbar.Size
	
	def create_toolbar_items(self):		
		self.gui_reference = versetree.VerseTree(self.toolbar, with_verses=True)
		self.gui_reference.SetSize((140, -1))
		
		self.gui_go = self.toolbar.AddTool(wx.ID_ANY,  
			guiutil.bmp("accept.png"),
			shortHelpString=_("Go to this reference"))

		self.toolbar.AddSeparator()
		
		self.gui_link = self.toolbar.AddCheckTool(
			wx.ID_ANY,
			guiutil.bmp("link.png"), 
			shortHelp=_("Link the %s to the Bible") % self.title
		)

		self.linked = True
		self.toolbar.ToggleTool(self.gui_link.Id, True)

		self.toolbar.InsertControl(0, self.gui_reference)

		self.toolbar.Bind(wx.EVT_TOOL, self.set_ref, id=self.gui_go.Id)
		self.toolbar.Bind(wx.EVT_TOOL, self.on_link, id=self.gui_link.Id)
		self.gui_reference.Bind(wx.EVT_TEXT_ENTER, self.set_ref)
		self.gui_reference.on_selected_in_tree += self.set_ref
	
	def set_ref(self, event):
		ref = self.gui_reference.Value
		if not ref: return
		ref = self.get_verified(ref)
		if not ref: return
		self.latest_reference = ref
		if not self.SetVerseReference(ref):
			wx.MessageBox(_("%s is not in this harmony.") % ref, config.name())

	def get_verified(self, ref):
		try:
			ref = GetVerseStr(ref, "", 
				raiseError=True, userInput=True, userOutput=False)
			return ref
		
		except VerseParsingError, e:
			wx.MessageBox(str(e), config.name())

	# XXX: We cannot use BookFrame's get_verified_one_verse, because it
	# assumes that there is a valid current reference which is a verse.
	# Our current reference is a Genbook tree reference.
	#get_verified = BookFrame.get_verified_one_verse
	
	def on_link(self, event=None):
		self.linked = not self.linked
		if self.linked:
			self.SetVerseReference(guiconfig.mainfrm.currentverse)
	
	"""
	def on_shown(self, shown=None):
		if shown:
			if self.linked and self.latest_reference != self.reference:
				self.SetVerseReference(self.latest_reference)
		super(HarmonyFrame, self).on_shown(shown)
	"""

	def bible_ref_changed(self, event):
		# only update if we are linked, and it isn't just a settings change
		if self.linked and not event.settings_changed:
			self.latest_reference = event.ref
			if self.aui_pane.IsShown():
				self.SetVerseReference(event.ref)

		elif event.settings_changed and event.source not in events.sources_not_to_reload_harmony_for:
			if self.aui_pane.IsShown():
				self.refresh()
			else:
				self.settings_changed = True

	def SetVerseReference(self, ref, settings_changed=False):
		genbook_key = self.book.find_reference(ref)
		found_reference = (genbook_key is not None)
		if found_reference:
			self.SetReference_from_string(genbook_key)
			self.gui_reference.Value = ref

		return found_reference

	def SetReference(self, ref, settings_changed=False):
		if biblemgr.bible.mod is None:
			self.reference = ref
			self.SetPage(config.HARMONY_UNSUPPORTED_MESSAGE())
			return

		super(HarmonyFrame, self).SetReference(ref, settings_changed)

	def refresh(self):
		self.SetReference(self.reference, settings_changed=True)

