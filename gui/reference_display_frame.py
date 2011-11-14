import json
from backend.bibleinterface import biblemgr
from displayframe import DisplayFrameXRC
from util import overridableproperty
from swlib.pysw import GetBestRange
import config

class ReferenceDisplayFrame(DisplayFrameXRC):
	"""This class is a display frame which is able to show references.

	The complete text of the reference is displayed in the frame when
	SetReference() is called.
	"""
	def __init__(self):
		self.reference = None
		self.show_reference_string = False
		self.has_reference_been_shown = False
		super(ReferenceDisplayFrame, self).__init__()

	def SetReference(self, reference, *args, **kwargs):
		"""Sets the reference to be displayed in the view (as a string).
		
		The additional arguments are passed to Bible.GetReference().
		"""
		old_reference = self.reference
		self.reference = reference
		if self.reference or old_reference:
			self._RefreshUI(*args, **kwargs)

	def RefreshUI(self, event=None):
		if event and not event.settings_changed:
			return
		self._RefreshUI()

	def _RefreshUI(self, *args, **kwargs):
		if not self.reference:
			self.ShowReferenceHTML("")
			return

		template = self.template
		if template:
			kwargs["template"] = template

		data = biblemgr.bible.GetReference(self.reference, *args, **kwargs)
		if self.show_reference_string:
			reference_text = GetBestRange(self.reference, userOutput=True)
			reference_string = (u'<p><a href="bible:%s"><small><em>'
					'%s (%s)</em></small></a></p><br>' %
					(self.reference, reference_text, self.book.version))
		else:
			reference_string = ""
		if data is None:
			data = config.MODULE_MISSING_STRING()

		else:
			# XXX: This replace should be done for us by the backend Bible
			# interface (or by Sword itself).
			data = data.replace("<!P>","</p><p>")

		self.ShowReferenceHTML("%s%s" % (reference_string, data))

	def ShowReferenceHTML(self, data):
		if self.has_reference_been_shown:
			self.defer_call_till_document_loaded(ReferenceDisplayFrame.Execute,
				"""$("#original_segment").html(%s);""" %
					json.dumps(data))
		else:
			self.has_reference_been_shown = True
			self.SetPage(data)
		self.SetFocus()
	
	@overridableproperty
	def template(self):
		return config.bible_template_without_headings
	
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
