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

class TextPanel(wx.PyPanel):
	def __init__(self, parent, style=0):
		super(TextPanel, self).__init__(parent, style=style)
		self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt:None)
		self.Bind(wx.EVT_PAINT, self.on_paint)
		self.Bind(wx.EVT_KILL_FOCUS, self.end_parent_modal)
		self.text = ""
		self.insertion_point = 0
		self.Bind(wx.EVT_CHAR, self.add_letter)
		#self.font = 
		self.font = wx.Font(20, wx.SWISS, wx.NORMAL, wx.FONTWEIGHT_BOLD, False)
		dc = wx.MemoryDC()
		dc.SetFont(self.font)
		w, self.height = dc.GetTextExtent(string.letters)
		w = dc.GetTextExtent("a")[0]
		self.w = w
		self.Caret = wx.Caret(self, (w,3))
		self.Caret.Show()
	
	def end_parent_modal(self, event):
		self.Parent.EndModal(wx.CANCEL)

	def on_paint(self, event):
		dc = wx.PaintDC(self)
		dc.Background = wx.Brush(self.BackgroundColour)
		dc.SetFont(self.font)
		dc.Clear()

		w, h = self.Size
		tw, th = dc.GetTextExtent(self.text)
		caret_pos, _ = dc.GetTextExtent(self.text[:self.insertion_point])
		
		p = " "
		if self.insertion_point != len(self.text):
			p = self.text[self.insertion_point]
		
		cw, _ = dc.GetTextExtent(p)
		cw2, _ = dc.GetTextExtent(" ")
		
		self.Caret.SetSize((cw,3))
		self.w = cw
		
		

		offset = (w-tw)/2 - cw2/2, (h-th)/2

		dc.TextForeground = text_colour
		dc.DrawText(self.text, *offset)
		self.Caret.Move((offset[0] + (caret_pos), 
						h-3))
		#self.Caret.Show()
		

	def add_letter(self, event):
		if event.KeyCode == wx.WXK_RETURN:
			# unbind the kill focus, or we will have cancelled it
			self.Unbind(wx.EVT_KILL_FOCUS)
			self.Parent.EndModal(wx.OK)
			return
		if event.KeyCode == wx.WXK_BACK:
			self.text = (self.text[:self.insertion_point-1] +
						self.text[self.insertion_point:])

			self.insertion_point -= 1
			self.insertion_point = max(0, self.insertion_point)
			
		
			self.Refresh()
			return

		if event.KeyCode == wx.WXK_ESCAPE:
			self.Unbind(wx.EVT_KILL_FOCUS)
			self.Parent.EndModal(wx.CANCEL)
		
		if event.KeyCode == wx.WXK_LEFT:
			self.insertion_point -= 1
			self.insertion_point = max(0, self.insertion_point)
			self.Refresh()
			

		if event.KeyCode == wx.WXK_RIGHT:
			self.insertion_point += 1
			self.insertion_point = min(len(self.text), self.insertion_point)
			self.Refresh()

		if event.KeyCode == wx.WXK_HOME:
			self.insertion_point = 0
			self.Refresh()
			
		if event.KeyCode == wx.WXK_END:
			self.insertion_point = len(self.text)
			self.Refresh()

		if event.KeyCode == wx.WXK_DELETE:
			if self.text[self.insertion_point:]:
				self.text = (self.text[:self.insertion_point] +
						self.text[self.insertion_point+1:])
			self.Refresh()
			
		if event.KeyCode > 255:
			return

		allowed_keys = (string.punctuation + string.letters + " " + 
						string.digits)
		if chr(event.KeyCode) in allowed_keys:
			self.text = (self.text[:self.insertion_point] + chr(event.KeyCode)
						+ self.text[self.insertion_point:])
			self.insertion_point += 1
						
			self.Refresh()
	
	def DoGetBestSize(self):
		return (150, self.height)


if osutils.is_gtk():
	# under wxGTK, the miniframe has a border around it which we don't want
	quick_selector_class = wx.Frame
else:
	quick_selector_class = wx.MiniFrame

class QuickSelector(quick_selector_class):
	def __init__(self, parent, size=wx.DefaultSize, title="", style=0):
		super(QuickSelector, self).__init__(parent, size=size, 
			style=style|
                           wx.FRAME_SHAPED
                         | wx.NO_BORDER
                         | wx.FRAME_NO_TASKBAR
                         #| wx.STAY_ON_TOP
			#wx.NO_BORDER|wx.FRAME_SHAPED|wx.FRAME_NO_TASKBAR)
		)
		
		if not self.SetTransparent(opacity * 255):
			dprint(WARNING, "Transparency not supported")
			set_theme("white")

		self.SetBackgroundColour(back_colour)
		
		
		text = wx.StaticText(self, label=title, #pos=(0, radius + 10), 
			style=wx.ALIGN_CENTRE)

		hrule = Line(self)
		hrule.SetSize((-1, 1))
		#self.text = wx.TextCtrl(self)
		self.panel = TextPanel(self, style=wx.WANTS_CHARS)
		self.panel.SetBackgroundColour(back_colour)
		
		sizer = wx.BoxSizer(wx.VERTICAL)
		

		sizer.Add(text, 0, wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT, 10)
		sizer.Add(hrule, 0, wx.GROW|wx.LEFT|wx.RIGHT, 10)
		sizer.Add(self.panel, 1, wx.GROW|wx.ALL, 20)
		
		text.ForegroundColour = text_colour
		f = text.Font
		f.SetWeight(wx.FONTWEIGHT_BOLD)
		f.SetPointSize(12)
		text.Font = f
		self.SetSizerAndFit(sizer)
		self.Size = 300, self.Size[1]
		self.Layout()
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
			
			self.panel.SetFocusIgnoringChildren()
			
		
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

if __name__ == "__main__":
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

