import wx
from wx import stc

class StyledText(stc.StyledTextCtrl):
	def __init__(self, *args, **kwargs):
		super(StyledText, self).__init__(*args, **kwargs)
		
		self.SetWrapMode(stc.STC_WRAP_WORD)
		for a in range(3):
			self.SetMarginWidth(a, 0)

		# Selection background
		
		self.SetSelBackground(True, 
			wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))

		self.SetSelForeground(True, 
			wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))

		if wx.Platform == '__WXMSW__':
			faces = { 'times': 'Times New Roman',
					  'mono' : 'Courier New',
					  'helv' : 'Arial',
					  'other': 'Comic Sans MS',
					  'size' : 10,
					  'size2': 8,
					 }
		else:
			faces = { 'times': 'Times',
					  'mono' : 'Courier',
					  'helv' : 'Helvetica',
					  'other': 'new century schoolbook',
					  'size' : 12,
					  'size2': 10,
					 }
		
		
		# Global default styles for all languages
		self.StyleSetSpec(stc.STC_STYLE_DEFAULT, 
			"face:%(helv)s,size:%(size)d" % faces)

