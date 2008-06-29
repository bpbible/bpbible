import wx
from passage_list import PassageEntry, InvalidPassageError, \
		MultiplePassagesError
from swlib.pysw import VerseList
from xrc.passage_entry_dialog_xrc import xrcPassageEntryDialog

class PassageEntryDialog(xrcPassageEntryDialog):
	def __init__(self, parent, passage_entry):
		super(PassageEntryDialog, self).__init__(parent)
		self._passage_entry = passage_entry
		self._setup_validators()

	def _setup_validators(self):
		self.passage_text.SetValidator(PassageValidator(self._passage_entry))
		self.comment_text.SetValidator(CommentValidator(self._passage_entry))

class PassageValidator(wx.PyValidator):
	def __init__(self, passage_entry):
		self._passage_entry = passage_entry
		super(PassageValidator, self).__init__()
	
	def Clone(self):
		return PassageValidator(self._passage_entry)
	
	def TransferToWindow(self):
		self.GetWindow().ChangeValue(str(self._passage_entry))
		return True
	
	def TransferFromWindow(self):
		self._passage_entry.passage = str(self.GetWindow().GetValue())
		return True

	def Validate(self, window):
		try:
			passage = str(self.GetWindow().GetValue())
			PassageEntry(passage)
			return True
		except InvalidPassageError:
			self._showInformation(window,
					"Unrecognised passage `%s'." % passage)
			return False
		except MultiplePassagesError:
			self._showInformation(window,
					"Passage `%s' contains multiple passages.\n" \
					"Only one verse or verse range can be entered." \
					% passage)
			return False
	
	def _showInformation(self, window, message):
		dialog = wx.MessageDialog(window, message, "",
				wx.OK | wx.ICON_INFORMATION)
		dialog.ShowModal()
		dialog.Destroy()

class CommentValidator(wx.PyValidator):
	def __init__(self, passage_entry):
		self._passage_entry = passage_entry
		super(CommentValidator, self).__init__()
	
	def Clone(self):
		return CommentValidator(self._passage_entry)
	
	def TransferToWindow(self):
		self.GetWindow().ChangeValue(self._passage_entry.comment)
		return True
	
	def TransferFromWindow(self):
		self._passage_entry.comment = self.GetWindow().GetValue()
		return True

	def Validate(self, window):
		return True
