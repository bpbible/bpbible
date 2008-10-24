import wx
from backend.bibleinterface import biblemgr
from displayframe import DisplayFrameXRC
from util import overridableproperty

class ReferenceDisplayFrame(DisplayFrameXRC):
	"""This class is a display frame which is able to show references.

	The complete text of the reference is displayed in the frame when
	SetReference() is called.
	"""
	def __init__(self):
		self.reference = None
		super(ReferenceDisplayFrame, self).__init__()

	def SetReference(self, reference, *args, **kwargs):
		"""Sets the reference to be displayed in the view (as a string).
		
		The additional arguments are passed to Bible.GetReference().
		"""
		self.reference = reference
		self._RefreshUI(*args, **kwargs)

	def RefreshUI(self, event):
		self._RefreshUI()

	def _RefreshUI(self, *args, **kwargs):
		if not self.reference:
			self.SetPage("")
			return

		template = self.template
		if template:
			kwargs["template"] = template

		data = biblemgr.bible.GetReference(self.reference, *args, **kwargs)
		# XXX: This replace should be done for us by the backend Bible
		# interface (or by Sword itself).
		data = data.replace("<!P>","</p><p>")
		self.SetPage("%s" % data)
	
	@overridableproperty
	def template(self):
		return None
	
	@property
	def book(self):
		return biblemgr.bible
	
		
class PlainReferenceDisplayFrame(ReferenceDisplayFrame):
	def _RefreshUI(self, *args, **kwargs):
		try:
			biblemgr.temporary_state(biblemgr.plainstate)
		
			return super(PlainReferenceDisplayFrame, self)._RefreshUI(
				*args, **kwargs
			)
		finally:
			biblemgr.restore_state()
