import wx

from bookframe import LinkedFrame, BookFrame
import config, guiconfig
from config import BIBLE_VERSION_PROTOCOL
from gui.multichoice import MultiChoiceDialog
from gui.menu import MenuItem
from backend.book import GetBestRange
from backend.bibleinterface import biblemgr
from swlib.pysw import VerseParsingError
from protocols import protocol_handler
from util import util
from util.configmgr import config_manager


verse_comparison_settings = config_manager.add_section("Verse Comparison")
verse_comparison_settings.add_item(
	"comparison_modules",
	biblemgr.bible.GetModuleList,
	is_initial_lazy=True,
	item_type="pickle"
)


def on_bible_version(frame, href, url):
	biblemgr.bible.SetModule(url.getHostName())

protocol_handler.register_handler(BIBLE_VERSION_PROTOCOL, on_bible_version)
protocol_handler.register_hover(BIBLE_VERSION_PROTOCOL, util.noop)


class VerseCompareFrame(LinkedFrame):
	title = "Verse Comparison"
	has_menu = False
	shows_info = False

	def __init__(self, parent, book):
		super(VerseCompareFrame, self).__init__(parent)
		self.SetBook(book)
		#verse_comparison_settings["comparison_modules"] = book.GetModuleList()
	
	def SetReference(self, ref, context=None):
		text = "<h3>%s</h3>" % ref
		mod = self.book.mod
		self.reference = ref
		
		try:
			self.book.templatelist.push(config.verse_compare_template)
		
			for item in self.book.GetModules():
				if item.Name() in \
					verse_comparison_settings["comparison_modules"]:
					self.book.mod = item
					text += self.book.GetReference(ref)

		finally:
			self.book.mod = mod
			self.book.templatelist.pop()

		self.SetPage(text)
		self.gui_reference.SetValue(ref)
		self.gui_reference.currentverse = ref
		self.update_title()
		

	def notify(self, reference, source=None):
		self.SetReference(reference)
	
	def update_title(self, shown=None):
		m = guiconfig.mainfrm
		p = m.get_pane_for_frame(self)
		ref = self.reference
		text = "%s - %s" % (p.name, ref)
		m.set_pane_title(p.name, text)
		
	def get_menu_items(self):
		actions = super(VerseCompareFrame, self).get_menu_items()
		actions = (
			MenuItem("Set versions to compare", self.set_versions),
		) + actions
		return actions

	def set_versions(self):
		"""Set the versions this version comparison will use"""
		modules = self.book.GetModuleList()
		mcd = MultiChoiceDialog(guiconfig.mainfrm, 
			"Choose modules to compare in the verse comparison window", 
			"Choose modules", 
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
		
