import wx
import wx.stc as stc
import wx.xrc as xrc
from gui import styled_text

		
class CPXmlHandler(xrc.XmlResourceHandler):
	def __init__(self):
		xrc.XmlResourceHandler.__init__(self)
		# Standard styles
		self.AddWindowStyles()
		# Custom styles
		#self.AddStyle('wxLED_ALIGN_LEFT', gizmos.LED_ALIGN_LEFT)
		#self.AddStyle('wxLED_ALIGN_RIGHT', gizmos.LED_ALIGN_RIGHT)
		#self.AddStyle('wxLED_ALIGN_CENTER', gizmos.LED_ALIGN_CENTER)
		#self.AddStyle('wxLED_DRAW_FADED', gizmos.LED_DRAW_FADED)
		
	def CanHandle(self,node):
		return self.IsOfClass(node, 'CollapsiblePane')

	# Process XML parameters and create the object
	def DoCreateResource(self):
		assert self.GetInstance() is None
		w = wx.CollapsiblePane(self.GetParentAsWindow(),
								self.GetID(),
								self.GetText('label'),
								pos=self.GetPosition(),
								size=self.GetSize(),
								style=self.GetStyle())
		
		#w.SetValue(self.GetText('value'))
		self.SetupWindow(w)
		#w.Size=w.DoBestSize()
		#w.SetWrapMode(stc.STC_WRAP_WORD)
		#for a in range(3):
		#	w.SetMarginWidth(a,0)
		def Toggle(event):
			print "EVENT"
			#w.Collapse(w.IsExpanded())
			w.Layout()
		w.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, Toggle)
		
		return w

	def CreateChildren(self, *args):
		print args

	def CreateChildrenPrivately(self, *args):
		print args	

class STCXmlHandler(xrc.XmlResourceHandler):
	def __init__(self):
		xrc.XmlResourceHandler.__init__(self)
		# Standard styles
		self.AddWindowStyles()
		# Custom styles
		#self.AddStyle('wxLED_ALIGN_LEFT', gizmos.LED_ALIGN_LEFT)
		#self.AddStyle('wxLED_ALIGN_RIGHT', gizmos.LED_ALIGN_RIGHT)
		#self.AddStyle('wxLED_ALIGN_CENTER', gizmos.LED_ALIGN_CENTER)
		#self.AddStyle('wxLED_DRAW_FADED', gizmos.LED_DRAW_FADED)
		
	def CanHandle(self,node):
		return self.IsOfClass(node, 'StyledTextCtrl')

	# Process XML parameters and create the object
	def DoCreateResource(self):
		assert self.GetInstance() is None
		w = styled_text.StyledText(parent=self.GetParentAsWindow(),
								id=self.GetID(),
								pos=self.GetPosition(),
								size=self.GetSize(),
								style=self.GetStyle())
		
		w.SetText(self.GetText('value'))
		self.SetupWindow(w)
		#w.Size=w.DoBestSize()
		w.SetWrapMode(stc.STC_WRAP_WORD)
		for a in range(3):
			w.SetMarginWidth(a,0)
		
		return w
	

def set_text(item, text):
	item.SetReadOnly(False)
	
	#item.autocomplete.set_text(self.template[item.field])
	em = item.GetModEventMask()
	item.SetModEventMask(0)

	item.SetText(text)

	# turn events back on
	item.SetModEventMask(em)

stc.StyledTextCtrl.set_text = set_text

xrc.XmlResource.Get().AddHandler(STCXmlHandler())
#import wx.tools.XRCed.xxx as xxx#import xxx
# Register XML handler
#xxx.register(STCXmlHandler)

