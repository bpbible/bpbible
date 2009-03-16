import wx

from bookframe import LinkedFrame, BookFrame
import config, guiconfig
from config import BIBLE_VERSION_PROTOCOL
from gui.multichoice import MultiChoiceDialog
from gui import guiutil

from gui.menu import MenuItem
from backend.bibleinterface import biblemgr
from protocols import protocol_handler
from util import noop
from util.configmgr import config_manager
from displayframe import IN_POPUP, process_html_for_module
from swlib.pysw import GetBestRange, SW, VK
from swlib import pysw
from util.unicode import to_str

from util.i18n import N_

verse_comparison_settings = config_manager.add_section("Verse Comparison")
verse_comparison_settings.add_item(
	"comparison_modules",
	biblemgr.bible.GetModuleList,
	is_initial_lazy=True,
	item_type="pickle"
)

verse_comparison_settings.add_item(
	"parallel",
	False,
	item_type=bool
)



def on_bible_version(frame, href, url):
	biblemgr.bible.SetModule(url.getHostName())

protocol_handler.register_handler(BIBLE_VERSION_PROTOCOL, on_bible_version)
protocol_handler.register_hover(BIBLE_VERSION_PROTOCOL, noop)


class VerseCompareFrame(LinkedFrame):
	id = N_("Version Comparison")
	has_menu = False
	shows_info = False

	def __init__(self, parent, book):
		super(VerseCompareFrame, self).__init__(parent)
		self.SetBook(book)
		#verse_comparison_settings["comparison_modules"] = book.GetModuleList()
	
	def SetReference(self, ref, context=""):
		text = "<h3>%s</h3>" % ref
		self.reference = ref
		text_func = [
			self.get_compare_text,
			self.get_parallel_text
		][verse_comparison_settings["parallel"]]

		
		self.SetPage(text_func(ref, context))

		self.gui_reference.SetValue(pysw.GetBestRange(ref, userOutput=True))
		self.gui_reference.currentverse = ref
		self.update_title()
	

	def get_parallel_text(self, ref, context):		
		vk = SW.VerseKey()
		verselist = vk.ParseVerseList(to_str(ref), to_str(context), True)
		
		items = []
		text = ["<table border=1 valign=TOP>", "<tr>"]
		for item in self.book.GetModules():
			name = item.Name()
			if name in verse_comparison_settings["comparison_modules"]:
				items.append((
					item, 
					list(self.book.GetReference_yield(
						verselist, module=item, max_verses=176
					))
				))
				
				text.append(process_html_for_module(item, 
					u"<th><b><a href='%s:%s'>"
					"%s</a></b></th>" % (BIBLE_VERSION_PROTOCOL, name, name))
				)

		text.append("</tr>")
		
		# if we have no bibles to compare, return the empty string
		if not items:
			return ""

		rows = []
		was_clipped = False
		while True:
			text.append("<tr>")
			for module, refs in items:
				if not refs:
					text.append("</tr>")
					break
				
				body_dict, headings = refs.pop(0)

				if not body_dict:
					was_clipped = True
					# remove opening row
					text.pop() 
					break

				text.append("<td>")
				
				t = ""
				for heading_dict in headings:
					t += biblemgr.bible.templatelist[-1].\
						headings.safe_substitute(heading_dict)
				
				t += "<sup>%(versenumber)s</sup> %(text)s" % body_dict
				t = process_html_for_module(module, t)

				text.append(t)
				
				text.append("</td>")
						
			else:
				text.append("</tr>")
				continue

			break

		text.append("</table>")
		
		if was_clipped:
			text.append(config.MAX_VERSES_EXCEEDED() % 177)
		

		return ''.join(text)
	
	def get_compare_text(self, ref, context):
		text = ""
		mod = self.book.mod
		
		try:
			self.book.templatelist.append(config.verse_compare_template)
		
			for item in self.book.GetModules():
				if item.Name() in \
					verse_comparison_settings["comparison_modules"]:
					self.book.mod = item
					# We exclude tags since otherwise the same tags appear in
					# every version, which isn't very sensible.
					text += process_html_for_module(item, 
						self.book.GetReference(ref, display_tags=False)
					)

		finally:
			self.book.mod = mod
			self.book.templatelist.pop()

		return text

	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		ref = pysw.GetBestRange(self.reference, userOutput=True)
		text = "%s - %s" % (self.title, ref)
		m.set_pane_title(p.name, text)
		
	def get_menu_items(self):
		actions = super(VerseCompareFrame, self).get_menu_items()
		actions = (
			(MenuItem(
				_("Set books to compare"), 
				self.set_versions,
				doc=_("Set the books this version comparison will use")
			), IN_POPUP),
		) + actions
		return actions

	def set_versions(self):
		
		modules = self.book.GetModuleList()
		mcd = MultiChoiceDialog(guiconfig.mainfrm, 
			_("Choose books to compare in the verse comparison window"), 
			_("Choose books"), 
			choices=modules)
		selections = [idx for idx, module in enumerate(modules) 
				if module in verse_comparison_settings["comparison_modules"]]

		mcd.SetSelections(selections)
		if mcd.ShowModal() == wx.ID_OK:
			verse_comparison_settings["comparison_modules"] = [
				modules[idx] for idx in mcd.GetSelections()
			]

			self.reload()
			

		mcd.Destroy()
				
	get_verified = BookFrame.get_verified_multi_verses

	def create_toolbar_items(self):
		super(VerseCompareFrame, self).create_toolbar_items()
		
		self.gui_book_choice = self.toolbar.InsertTool(3, wx.ID_ANY,  
			guiutil.bmp("book.png"),
			shortHelpString=_("Choose books to compare")
		)		

		self.gui_parallel = self.toolbar.InsertTool(4, wx.ID_ANY,
			guiutil.bmp("text_columns.png"),
			isToggle=True,
			shortHelpString=_("View in parallel mode")
		)
		self.toolbar.ToggleTool(self.gui_parallel.Id, 
			verse_comparison_settings["parallel"]
		)

		self.toolbar.InsertSeparator(5)

		self.toolbar.Bind(wx.EVT_TOOL, self.on_parallel_toggle, 
			id=self.gui_parallel.Id)

		self.toolbar.Bind(wx.EVT_TOOL, lambda evt:self.set_versions(),
			id=self.gui_book_choice.Id)
	
	def on_parallel_toggle(self, event):
		verse_comparison_settings["parallel"] = event.Checked()
		self.reload()
		
