from gui.reference_display_frame import ReferenceDisplayFrame
from backend.verse_template import VerseTemplate
from xrc.guess_verse_xrc import xrcGuessVerseFrame
import random
from swlib.pysw import VK, UserVK
import wx

class GuessVerseFrame(xrcGuessVerseFrame):
	def __init__(self, parent):
		super(GuessVerseFrame, self).__init__(parent)
		
		self.reference_frame.template = VerseTemplate(
			body=u"$text", headings=""
		)

		self.guess_button.Bind(wx.EVT_BUTTON, self.on_guess)
		self.books.AppendItems([book.bookname for book in VK.books])
		self.books.Selection = 0
		self.new_guess()
		self.Children[0].Fit()
		self.Fit()
	
	def new_guess(self):
		randomnum = random.randint(1, 31102)
		self.key = VK("Gen 1:%d" % randomnum)
		self.reference_frame.SetReference(self.key.text)

	def on_guess(self, event):
		won = self.key.getBookName() == self.books.StringSelection
		if won:
			wx.MessageBox(
				_("Yes, you are right. The verse was %s")
					% UserVK(self.key).text,
				_("Correct"),
				parent=self
			)

			self.new_guess()
		else:
			wx.MessageBox(
				_("No, you are wrong. Try again."), 
				_("Try again."),
				parent=self
			)

if __name__ == '__main__':
	a = wx.App(0)
	f = GuessVerseFrame(None)
	f.Show()
	a.MainLoop()
