import wx
from backend.bibleinterface import biblemgr
from displayframe import DisplayFrameXRC
from util.util import ReplaceUnicode

class ReferenceDisplayFrame(DisplayFrameXRC):
	"""This class is a display frame which is able to show references.

	The complete text of the reference is displayed in the frame when
	SetReference() is called.
	"""
	def __init__(self):
		self.reference = None
		super(ReferenceDisplayFrame, self).__init__()

	def SetReference(self, reference):
		"""Sets the reference to be displayed in the view (as a string)."""
		self.reference = reference
		self.RefreshUI()

	def RefreshUI(self, event=None):
		if not self.reference:
			self.SetPage("")
			return

		data = biblemgr.bible.GetReference(self.reference)
		# XXX: This replace should be done for us by the backend Bible
		# interface (or by Sword itself).
		data = data.replace("<!P>","</p><p>")
		#if not wx.USE_UNICODE:
		#	#replace common values
		#	data = ReplaceUnicode(data)
		self.SetPage("%s" % data)
