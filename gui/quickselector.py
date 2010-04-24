import wx
import string
from util import osutils
from util.debug import dprint, WARNING

theme = "black"
themes = dict(
	black=(10, 0.7, "black", "white"), 
	white=(10, 0.7, "white", "black"), 
	
	black_yellow=(10, 0.85, "black", "yellow"), 
	black_green=(10, 0.85, "black", "green"), 
	
	grey=(5, 1, "grey", "white"),
	red=(30, .7, "red", "black"),#(153, 102, 0)),
)

def set_theme(theme):
	global radius, opacity, back_colour, text_colour
	radius, opacity, back_colour, text_colour = themes[theme]

set_theme(theme)

class Line(wx.Window):
	def __init__(self, *args, **kwargs):
		super(Line, self).__init__(*args, **kwargs)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		
	def on_paint(self, event):
		dc = wx.PaintDC(self)
		dc.Background = wx.Brush((168,168,168))
		dc.Clear()

class TextPanel(wx.TextCtrl):#PyPanel):
	def __init__(self, parent,
	style=wx.TE_CENTRE|wx.TE_PROCESS_ENTER|wx.NO_BORDER):
		super(TextPanel, self).__init__(parent, style=style)
		self.Bind(wx.EVT_KILL_FOCUS, self.end_parent_modal)
		self.Bind(wx.EVT_CHAR, self.add_letter)
		self.Bind(wx.EVT_TEXT_ENTER, self.on_enter)
		self.SetFont(wx.Font(30, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False))
		dc = wx.MemoryDC()
		bmp = wx.EmptyBitmap(1, 1)
		dc.SelectObject(bmp)
		dc.SetFont(self.Font)
		w, self.height = dc.GetTextExtent(string.letters)
		self.MinSize = 1, self.height
#		w = dc.GetTextExtent("a")[0]
#		self.w = w
#		self.Caret = wx.Caret(self, (w,3))
#		self.Caret.Show()
	
	def end_parent_modal(self, event):
		event.Skip()
		wx.CallAfter(self.TopLevelParent.EndModal, wx.CANCEL)

	@property
	def text(self):
		return self.Value

	def on_enter(self, event):
		# unbind the kill focus, or we will have cancelled it
		self.Unbind(wx.EVT_KILL_FOCUS)
		self.TopLevelParent.EndModal(wx.OK)

	def add_letter(self, event):
		if event.KeyCode == wx.WXK_ESCAPE:
			self.Unbind(wx.EVT_KILL_FOCUS)
			self.TopLevelParent.EndModal(wx.CANCEL)
		elif event.KeyCode == wx.WXK_RETURN:
			self.on_enter(event)
		else:
			event.Skip()
		
if osutils.is_gtk():
	# under wxGTK, the miniframe has a border around it which we don't want
	quick_selector_class = wx.Frame
else:
	quick_selector_class = wx.MiniFrame

class QuickSelector(quick_selector_class):
	def __init__(self, parent, size=wx.DefaultSize, title="", style=0):
		super(QuickSelector, self).__init__(parent, size=size, 
			style=style
                         | wx.FRAME_SHAPED
                         | wx.NO_BORDER
                         | wx.FRAME_NO_TASKBAR
                         #| wx.STAY_ON_TOP
			#wx.NO_BORDER|wx.FRAME_SHAPED|wx.FRAME_NO_TASKBAR)
		)
		
		if not self.SetTransparent(opacity * 255):
			dprint(WARNING, "Transparency not supported")
			set_theme("white")

		self.SetBackgroundColour(back_colour)
		self.SetForegroundColour(text_colour)
		
		
		self.p = wx.Panel(self)
		self.p.SetBackgroundColour(back_colour)
		self.p.SetForegroundColour(text_colour)
		text = wx.StaticText(self.p, label=title, #pos=(0, radius + 10), 
			style=wx.ALIGN_CENTRE)

		text.SetBackgroundColour(back_colour)
		text.SetForegroundColour(text_colour)

		hrule = Line(self.p)
		hrule.SetSize((-1, 1))
		self.panel = TextPanel(self.p)
		self.panel.SetBackgroundColour(back_colour)
		self.panel.SetForegroundColour(text_colour)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		

		sizer.Add(text, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
		sizer.Add(hrule, 0, wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
		sizer.Add(self.panel, 0, wx.GROW|wx.BOTTOM|wx.LEFT|wx.RIGHT, 20)
		self.p.Sizer = sizer

		s1 = wx.BoxSizer(wx.HORIZONTAL)
		s1.Add(self.p, 1, wx.GROW|wx.ALL, 1)
		
		self.panel.ForegroundColour = text_colour
		f = text.Font
		f.SetWeight(wx.FONTWEIGHT_BOLD)
		f.SetPointSize(12)
		text.Font = f
		self.SetSizerAndFit(s1)
#		self.Size = self.p.BestSize
		self.SetSize((350, self.p.BestSize[1]))
#		self.SetSize(self.p.BestSize)

		if osutils.is_gtk():
			self.Bind(wx.EVT_WINDOW_CREATE, lambda evt:self.set_shape())
		else:
			self.set_shape()
		if not parent:
			self.CentreOnScreen()
		else:
			self.CentreOnParent()

	def set_shape(self):
		dc = wx.MemoryDC()
		bmp = wx.EmptyBitmap(*self.Size)
		dc.SelectObject(bmp)
		dc.Background = wx.WHITE_BRUSH
		dc.Clear()
		dc.Brush = wx.BLACK_BRUSH
		factor = 3
		dc.DrawRoundedRectangle(0, 0, self.Size[0]-factor, self.Size[1]-factor,
			radius)
		del dc

		img = wx.ImageFromBitmap(bmp)
		img.SetMaskColour(255,255,255)
		bmp = wx.BitmapFromImage(img)
		
		self.SetShape(wx.RegionFromBitmap(bmp))

	def ShowModal(self):
		self.panel.SetFocus()
		ansa = super(QuickSelector, self).ShowModal()
		return ansa

	@property
	def text(self):
		return self.panel.text
	
	def pseudo_modal(self, callback):
		def focus():
			#self.SetFocus()
			
			self.panel.SetFocus()
			
		
		#focus()
		self.Show()
		self.Raise()
		focus()
		
		
		self.callback = callback
	
	def EndModal(self, success):
		if isinstance(self, wx.Dialog) and self.IsModal():
			super(QuickSelector, self).EndModal(success)
		else:
			self.callback(self, success)

def main():
	a = wx.App(0)
	f = wx.Frame(None)
	b = wx.Button(f, label="test")
	def button_press(evt):
		def finish(qs, ansa):
			if ansa == wx.OK:
				wx.MessageBox("Text was " + qs.text)	

			qs.Destroy()
		
		qs = QuickSelector(f, size=(300, 150), title="Go to reference")
		qs.pseudo_modal(finish)

	b.Bind(wx.EVT_BUTTON, button_press)
	f.Show()

	a.MainLoop()

if __name__ == "__main__":
	main()
