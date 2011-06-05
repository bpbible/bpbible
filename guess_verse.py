from backend.verse_template import VerseTemplate
from backend.bibleinterface import biblemgr
from xrc.guess_verse_xrc import xrcGuessVerseFrame
import random
from swlib.pysw import VK, UserVK
import wx
from tooltip import Tooltip

class GuessVerseFrame(xrcGuessVerseFrame):
	def __init__(self, parent):
		super(GuessVerseFrame, self).__init__(parent)
		
		# This call makes sure that the reference display frame is loaded
		# with an empty reference.
		# This means that all future references displayed will be shown with
		# Javascript, and so there won't be any focus bugs.
		self.reference_frame.RefreshUI()

		self.reference_frame.template = VerseTemplate(
			body=u"$text", headings=""
		)

		self.show_answer_button.Bind(wx.EVT_BUTTON, self.on_show_answer)
		self.guess_button.Bind(wx.EVT_BUTTON, self.on_guess)
		self.books.AppendItems([unicode(book) for book in UserVK.books])
		self.books.Selection = 0
		self.new_guess()
		self.Children[0].Fit()
		self.Fit()
	
	def new_guess(self):
		self.key = None
		while not self.key or not biblemgr.bible.mod.hasEntry(self.key):
			randomnum = random.randint(1, 31102)
			self.key = VK("Gen 1:%d" % randomnum)
		self.user_key = UserVK(self.key)
		self.reference_frame.SetReference(self.key.getText())

	def on_show_answer(self, event):
		Tooltip.do_not_show_tooltip = True
		wx.MessageBox(
			_("The verse was %s") % UserVK(self.key).getText(),
			parent=self
		)
		Tooltip.do_not_show_tooltip = False

		self.new_guess()

	def on_guess(self, event):
		# XXX: We can't use the currently focused window trick to prevent
		# tooltips from grabbing focus when using a MessageBox, since it
		# gives the focused window as None.  Instead, we use this hack.
		Tooltip.do_not_show_tooltip = True
		won = self.user_key.getBookName() == self.books.StringSelection
		if won:
			wx.MessageBox(
				_("Yes, you are right. The verse was %s")
					% UserVK(self.key).getText(),
				_("Correct"),
				parent=self
			)

			self.new_guess()
		else:
			wx.MessageBox(
				_("No, you are wrong. Try again."), 
				_("Try again."),
				parent=self,
				style=wx.OK | wx.ICON_ERROR,
			)
		Tooltip.do_not_show_tooltip = False

if __name__ == '__main__':
	a = wx.App(0)
	f = GuessVerseFrame(None)
	f.Show()
	a.MainLoop()
