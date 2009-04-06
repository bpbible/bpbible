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

		self.show_answer_button.Bind(wx.EVT_BUTTON, self.on_show_answer)
		self.guess_button.Bind(wx.EVT_BUTTON, self.on_guess)
		self.books.AppendItems([unicode(book) for book in UserVK.books])
		self.books.Selection = 0
		self.new_guess()
		self.Children[0].Fit()
		self.Fit()
	
	def new_guess(self):
		randomnum = random.randint(1, 31102)
		self.key = VK("Gen 1:%d" % randomnum)
		self.user_key = UserVK(self.key)
		self.reference_frame.SetReference(self.key.getText())

	def on_show_answer(self, event):
		wx.MessageBox(
			_("The verse was %s") % UserVK(self.key).getText(),
			parent=self
		)

		self.new_guess()

	def on_guess(self, event):
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

if __name__ == '__main__':
	a = wx.App(0)
	f = GuessVerseFrame(None)
	f.Show()
	a.MainLoop()
