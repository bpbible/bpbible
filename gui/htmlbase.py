import wx
import wx.html
import wx.lib.wxpTag
from wx import html
from gui import guiutil
from util import string_util
import guiconfig
import re
from util.configmgr import config_manager
from util.debug import dprint, ERROR, MESSAGE


html_settings = config_manager.add_section("Html")
html_settings.add_item("font_name", "Arial")
html_settings.add_item("base_text_size", 10, item_type=int)
html_settings.add_item("zoom_level", 0, item_type=int)

HTML_TEXT = '<body bgcolor="%s"><div><font color="%s">%s</font></div></body>'

# some magic zoom constants
zoom_levels = {-2: 0.75, 
			   -1: 0.83, 
			   	0: 1, 
				1: 1.2, 
				2: 1.44, 
				3: 1.73, 
				4: 2,
				5: 2.5,
				6: 3,
				7: 3.5
				}


class TagHandler(wx.html.HtmlWinTagHandler):
	tags = None
	def GetSupportedTags(self):
		return self.tags

	def HandleTag(self, tag):
		try:			
			return self.HandleTag2(tag)
		except Exception, e:
			import traceback
			traceback.print_exc()
			dprint(ERROR, e.args, e.message)

	def HandleTag2(self, tag):
		return False
	
class GLinkTagHandler(TagHandler):
	tags = "GLINK"

	def HandleTag2(self, tag):
		parser = self.GetParser()

		if tag.HasParam("HREF"):
			#oldlnk = parser.GetLink()
			oldclr = parser.GetActualColor()

			name = tag.GetParam("HREF")

			target = ""
			colour = config_manager["Filter"]["strongs_colour"]
			if tag.HasParam("COLOUR"):
				colour = tag.GetParam("COLOUR")

			if (tag.HasParam("TARGET")):
				target = tag.GetParam("TARGET")

			parser.SetActualColor(colour)
			parser.GetContainer().InsertCell(html.HtmlColourCell(colour))
			
			parser.GetContainer().InsertCell(
				html.HtmlFontCell(parser.CreateCurrentFont())
			)
			parser.SetLink(name)#, target))

			self.ParseInner(tag)

			parser.SetLink("")#oldlnk.GetHref())
			parser.GetContainer().InsertCell(
				html.HtmlFontCell(parser.CreateCurrentFont())
			)
			parser.SetActualColor(oldclr)
			parser.GetContainer().InsertCell(html.HtmlColourCell(oldclr))

			return True
		return False

class HighlightedTagHandler(TagHandler):
	tags = "HIGHLIGHTED"

	def HandleTag2(self, tag):
		parser = self.GetParser()

		colour = "blue"
		if tag.HasParam("COLOUR"):
			colour = tag.GetParam("COLOUR")


		container = parser.OpenContainer()
		container.SetBackgroundColour(colour)
		#container2 = parser.OpenContainer()
		
		container.SetBackgroundColour("green")#colour)
		
		#container2.SetBackgroundColour("red")#colour)
		
		
		self.ParseInner(tag)

		#parser.CloseContainer()
		parser.CloseContainer()
		

		return True

	

class HtmlAnchorCell(html.HtmlCell):
	def __init__(self, anchor):
		self.anchor = anchor
		super(html.HtmlCell, self).__init__()
	
	def Draw(self, dc, x, y, view_y1, view_y2, info):
		pass

class AnchorTagHandler(TagHandler):
	tags = "ANCHOR"

	def HandleTag2(self, tag):
		parser = self.GetParser()
		if tag.HasParam("NAME"):
			parser.GetContainer().InsertCell(HtmlAnchorCell(tag.GetParam("NAME")))
			return True

class CheckTagHandler(TagHandler):
	tags = "CHECK"

	def HandleTag2(self, tag):
		parser = self.GetParser()
		label = ""
		if tag.HasParam("label"):
			label = tag.GetParam("label")
		
		parent = parser.GetWindowInterface().GetHTMLWindow()
		assert parent
		obj = wx.CheckBox(parent, label=label)#**self.ctx.kwargs)
		obj.Show(True)
		
		floatwidth = 0
		parser.GetContainer().InsertCell(
				wx.html.HtmlWidgetCell(obj, floatwidth))
			
		return True

from passage_list import lookup_passage_list, lookup_passage_entry

class PassageTagHandler(TagHandler):
	"""This tag handler inserts passage tag widgets for passage tags."""
	tags = "PASSAGE_TAG"

	def HandleTag2(self, tag):
		assert tag.HasParam("topic_id")
		passage_list = lookup_passage_list(
				int(tag.GetParam("topic_id"))
			)
		assert tag.HasParam("passage_entry_id")
		passage_entry = lookup_passage_entry(
				int(tag.GetParam("passage_entry_id"))
			)
		assert passage_entry in passage_list.passages
		
		parser = self.GetParser()
		parent = parser.GetWindowInterface().GetHTMLWindow()
		assert parent
		from gui.passage_tag import PassageTag
		passage_tag = PassageTag(parent, passage_list, passage_entry)
		passage_tag.Show(True)
		
		floatwidth = 0
		parser.GetContainer().InsertCell(
				wx.html.HtmlWidgetCell(passage_tag, floatwidth))
			
		return True

wx.html.HtmlWinParser_AddTagHandler(GLinkTagHandler)
wx.html.HtmlWinParser_AddTagHandler(HighlightedTagHandler)
wx.html.HtmlWinParser_AddTagHandler(AnchorTagHandler)
wx.html.HtmlWinParser_AddTagHandler(CheckTagHandler)
wx.html.HtmlWinParser_AddTagHandler(PassageTagHandler)


def get_text_size(base):
	ansa = zoom_levels[html_settings["zoom_level"]] * base
	return ansa

def zoom(direction):
	if direction == 0:
		# reset zoom
		html_settings["zoom_level"] = 0
	else:
		html_settings["zoom_level"] += direction

		# but make sure it is in bounds
		html_settings["zoom_level"] = (
			max(min(html_settings["zoom_level"], 7), -2)
		)
	



class HtmlBase(wx.html.HtmlWindow):
	loading_a_page = False
	override_loading_a_page = False

	def __init__(self, *args, **kwargs):
		super(HtmlBase, self).__init__(*args, **kwargs)
		self._setup()
		

	def setup(self):
		self._setup()

	def _setup(self):
		self.top_left_cell = None
		self.Bind(wx.EVT_SIZE, self.on_size)
		self.Bind(wx.EVT_IDLE, self.on_idle)
		
	
	def on_idle(self, event):
		# calculate the logical position from the screen point 0, 0
		#x, y = self.GetViewStart()#self.CalcUnscrolledPosition(0, 0)
		x, y = [scroll_units*scroll_unit for scroll_units, scroll_unit 
			in zip(self.ViewStart, self.GetScrollPixelsPerUnit())]

		# now get the top left cell
		# possibly we should only get this after the user moves somewhere, so
		# that multiple sizings don't jump about so much

		# Before or after?
		self.top_left_cell = self.InternalRepresentation.FindCellByPos(x, y,
										 #html.HTML_FIND_NEAREST_BEFORE)
			html.HTML_FIND_NEAREST_AFTER)
		
		event.Skip()
	
	def on_size(self, event):
		# Under GTK, we are getting extra size events when html is loaded,
		# even though the size hasn't changed. 
		# Don't skip the event, or wxHtml will try to handle it 
		# (i.e. scroll to top of window)
		if HtmlBase.loading_a_page and not HtmlBase.override_loading_a_page:
			return
		
		c = self.top_left_cell

		event.Skip()
		if not c: 
			return

		y = 0
		scrollstep = self.GetScrollPixelsPerUnit()[1]

		while c:
			y += c.GetPosY()
			c = c.GetParent()

		d = None#guiutil.FreezeUI(self)
		
		wx.CallAfter(self.ScrollNow, -1, y / scrollstep, d)
		
	def ScrollNow(self, x, y, disabler=None):
		self.Scroll(x, y)
		
	
	def SetPage(self, *args, **kwargs):
		# don't handle sizing during loading
		# or it may crash due to an invalid top left cell
		self.Unbind(wx.EVT_SIZE)
		HtmlBase.loading_a_page = True
	
		try:
			self.set_page(*args, **kwargs)
		finally:
			def finish():
				HtmlBase.loading_a_page = False
				if self:
					self.Bind(wx.EVT_SIZE, self.on_size)
				

			wx.CallAfter(finish)
		
		
	def set_page(self, text, raw=False, text_colour=None, body_colour=None):
		"""Set the page with the given text and colour. 
		
		Either or neither of text_colour and body_colour can be specified"""
		self.top_left_cell = None
	
		#text = text.replace("<small>", "<font size=-1>")
		#text = text.replace("</small>", "</font>")
		text = string_util.htmlify_unicode(text)

		if body_colour is None or text_colour is None:
			body_colour, text_colour = guiconfig.get_window_colours()

		self.SetStandardFonts(get_text_size(html_settings["base_text_size"]), 
			html_settings["font_name"])
		
		text = HTML_TEXT % (body_colour, text_colour, text)

		if raw:
			text = text.replace("&", "&amp;")
			text = text.replace(">", "&gt;")
			text = text.replace("<", "&lt;")
			text = text.replace("\n", "<br>\n")
		else:
			# apos is valid xml, but not valid html.
			# Jub seems to use it, and it is valid osis, but the osishtmlhref
			# filters don't get rid of it
			text = text.replace("&apos;", "&#39;")
			

		return super(HtmlBase, self).SetPage(text)

def HtmlSelection_Set(self, fromCell, toCell):
	# this version doesn't occur in the swig wrapped version, so here it is in
	# python code
	p1 = wx.DefaultPosition
	p2 = wx.DefaultPosition
	
	if fromCell:
		p1 = fromCell.GetAbsPos()
	if toCell:
		p2 = toCell.GetAbsPos()
		p2.x += toCell.GetWidth()
		p2.y += toCell.GetHeight()
	
	self.Set(p1, fromCell, p2, toCell);

# stuff from displayframe
def eq(a, b):
	return str(a)==str(b)

def choptext(faketext, d):
	dels = d[:]
	c = 0
	while dels:
		f, to = dels[0][0]-c, dels[0][1]+dels[0][0]-c
		faketext = faketext[:f] + faketext[to:]

		c+=dels[0][1]
		del dels[0]
	return faketext


class linkiter(object):
	def __init__(self, start, end):
		self.m_to = end
		self.m_pos = start

	def next(self):
		if ( not self.m_pos ):
			return None

		while 1:
			if eq(self.m_pos,self.m_to):
				self.m_pos = None;
				return None;

			if ( self.m_pos.GetNext() ):
				self.m_pos = self.m_pos.GetNext();
			else:
				while ( not self.m_pos.GetNext()):
					self.m_pos = self.m_pos.GetParent();
					if ( not self.m_pos ):
						return None;
				self.m_pos = self.m_pos.GetNext();

			while ( self.m_pos.GetFirstChild() != None ):
				self.m_pos = self.m_pos.GetFirstChild();

			if(self.m_pos.IsTerminalCell()):
				return self.m_pos

	def __nonzero__(self):
		return self.m_pos is not None

		
class HtmlSelectableWindow(HtmlBase):
	"""Handle the fact (among other things) that you can't get at the
	selection. This handles selection and copying
	
	Lots of this code comes from the wxhtml sources"""
	def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
	  		size=wx.DefaultSize, style = html.HW_DEFAULT_STYLE):
		super(HtmlSelectableWindow, self).__init__(parent,id,pos,size,style)  
		#self.buffer = wx.TextCtrl(self)
		#self.buffer.Hide()
		self.setup()

	def setup(self):

		self.lastcell = None
		self.Bind(wx.EVT_MOTION, self.MouseMove)
		self.Bind(wx.EVT_IDLE, self.Idle)
		self.Bind(wx.EVT_LEFT_DOWN, self.MouseDown)
		self.Bind(wx.EVT_LEFT_UP, self.MouseUp)
#		self.Bind(wx.EVT_TEXT_COPY, self.OnCopy)
#		self.Bind(wx.EVT_ERASE_BACKGROUND, self.Erase)
#		self.Bind(wx.EVT_PAINT, self.Paint)
		self.Bind(wx.EVT_KEY_UP, self.on_char)

		self.mousedown = False 
		self.mousemoved = False
		self.select = False
		self.mousecoords = (0, 0)
		self.lastmouse = [None, None]
		super(HtmlSelectableWindow, self).setup()

	def on_char(self, event):
		guiutil.dispatch_keypress(self.get_actions(), event)

	def get_actions(self):
		return {
			(ord("C"), wx.MOD_CMD): self.OnCopy,
		}
		
	def OnCopy(self, event=None, with_links=True):
		# problem here is that we have the text up to the word boundaries,
		# whereas internally it knows it to the character. However, internally
		# it comes with links, which we may not want. So we make two versions
		# of what we see - one without links, and one with links, and a list
		# of deletions to go from one to the other. We then turn our one
		# without links into the final product using the list of deletions 

		dprint(MESSAGE, "ON COPY")

		# what the html control thinks the selection is
		# This contains links
		text2 = self.SelectionToText()
		if with_links:
			guiutil.copy(text2)
			return
		
		if not self.m_selection:
			return
			
		from_cell = self.m_selection.GetFromCell()
		to_cell = self.m_selection.GetToCell()

		#the text without links
		text=""

		#the text with links, but, with list of dels, equivalent to above
		faketext=""

		#the differences between text and faketext
		dels = []

		i = linkiter(from_cell, to_cell)

		prev = i.m_pos

		# if it starts with a space, kill this. Otherwise, we can run into
		# nasty problems... (this seems to be a problem with a 
		# 0 width selection of a space i.e. it's not really selected, but we
		# think it is)
		if prev.ConvertToText(None) == " " and \
			not text2.startswith(" "):
			
			if i:
				i.next()

		while (i):
			# new block
			if (not eq(prev.GetParent(), i.m_pos.GetParent())):
				text += '\n';
				faketext += '\n'

			if(i.m_pos.GetLink()):
				#if we are a link, add to our *other* version

				#is it a verse number?
				#if(i.m_pos.GetLink().GetHref().startswith("bible")):
				#	c = 1
				m = i.m_pos.ConvertToText(None)
				dels += [[len(faketext), len(m)]]
				faketext += m
			else:

				m = i.m_pos.ConvertToText(None)
 
				text += m
				faketext += m
				prev = i.m_pos;
			i.next();

		c = 0
		#strip of trailing space
		words = faketext[:-1].split(" ")
		words2 = text2.split(" ")

		spaces = [False, False]
		if(len(words)!=len(words2)):
			# the selection ended or started in space(or both)
			# whole word or
			if not words2[-1]:
				words.append(" ")

		if(len(words2)<=1):
			words = words2
		else:
			if(words[0]!=words2[0]):
				c+= len(words[0])-len(words2[0])
				words[0]=words2[0]
				#idx = words[0].find(words2)
				#if(idx == -1):
				#else:
				#	c += idx
				#	words[0] = words[0][idx+1:]
			if(words[-1]!=words2[-1]):
				words[-1] = words2[-1]
		for idx, a in enumerate(dels):
			a[0] -= c
			if(a[0]>=len(faketext)):
				del dels[idx]

		realtext = choptext(" ".join(words), dels)
		faketext = " ".join(words)

		#get rid of extraneous spaces caused by spaces in between links.
		# TODO: This behaviour may not be desirable (if w/space is important)
		realtext = re.sub(" +", " ", realtext)


		guiutil.copy(realtext)

	#@html_source
	def SelectAll(self):
		m_Cell = self.GetInternalRepresentation()
		if m_Cell:
			self.m_selection = html.HtmlSelection()
			HtmlSelection_Set(self.m_selection,
				m_Cell.GetFirstTerminal(), m_Cell.GetLastTerminal())

		super(HtmlSelectableWindow, self).SelectAll()

	def MouseMove(self, event):
		event.Skip()
		if(self.mousecoords == event.GetPosition()):
			return

		self.mousecoords = event.GetPosition()
		if(self.mousedown):
			self.select = True
		else:
			self.select =False
		self.mousemoved = True
		self.Idle(None)

	def MouseDown(self, event):
		self.SetFocus()
		event.Skip()

		# we are getting two left downs and two left ups.
		# if a link is still there when another page appears 
		# (e.g. forward and back links), we get two mouse downs.
		if(self.lastmouse[0] == event.Timestamp):
			return
		self.lastmouse[0]=event.Timestamp

		if(event.Dragging()): return
		self.mousedown = True
		x, y = self.mousecoords
		cellover = self.FindCell(x,y)
		xx, yy = self.CalcUnscrolledPosition(x, y) 


		self.m_tmpSelFromPos = self.CalcUnscrolledPosition(event.GetPosition());
		self.m_tmpSelFromCell = None;
		self.m_selection = None

		if(cellover): self.CellClicked(cellover, xx, yy, event) 


	def FindCell(self, x,y):
		topcell = self.GetInternalRepresentation()
		#convert to position including scrolled position
		xx, yy = self.CalcUnscrolledPosition(x, y) 
		return topcell.FindCellByPos(xx, yy)


	def MouseUp(self, event):
		event.Skip()
		# getting called twice, bit weird
		if(self.lastmouse[1] == event.Timestamp):
			return
		self.lastmouse[1]=event.Timestamp
		if(self.select):
			x, y = event.GetPosition()
			self.select = False

		self.select = False
		self.mousedown = False

	def PutMeIn(self):
		#taken straight from the original source code :)
		m_Cell = self.GetInternalRepresentation()

		#xc, yc = wx.GetMousePosition();
		#xc, yc = self.ScreenToClient((xc, yc))
		#x, y = self.CalcUnscrolledPosition(xc, yc);
		x, y = guiutil.get_mouse_pos(self, scrolled=True)

		cell = m_Cell.FindCellByPos(x, y)
		if not self.m_tmpSelFromCell:
			self.m_tmpSelFromCell = m_Cell.FindCellByPos(
										 self.m_tmpSelFromPos.x,self.m_tmpSelFromPos.y);

		#// NB: a trick - we adjust selFromPos to be upper left or bottom
		#//	 right corner of the first cell of the selection depending
		#//	 on whether the mouse is moving to the right or to the left.
		#//	 This gives us more "natural" behaviour when selecting
		#//	 a line (specifically, first cell of the next line is not
		#//	 included if you drag selection from left to right over
		#//	 entire line):
		if not self.m_tmpSelFromCell:
			dirFromPos = self.m_tmpSelFromPos
		else:
			dirFromPos = self.m_tmpSelFromCell.GetAbsPos();
			if ( x < self.m_tmpSelFromPos.x ):
				dirFromPos.x += self.m_tmpSelFromCell.GetWidth()
				dirFromPos.y += self.m_tmpSelFromCell.GetHeight()
		goingDown = dirFromPos.y < y or \
							 (dirFromPos.y == y and dirFromPos.x < x);

		#// determine selection span:
		if not self.m_tmpSelFromCell:
			if (goingDown):
				self.m_tmpSelFromCell = m_Cell.FindCellByPos(
										 self.m_tmpSelFromPos.x,self.m_tmpSelFromPos.y,
										 html.HTML_FIND_NEAREST_AFTER);
				if (not self.m_tmpSelFromCell):
					self.m_tmpSelFromCell = m_Cell.GetFirstTerminal();
			else:
				self.m_tmpSelFromCell = m_Cell.FindCellByPos(
										 self.m_tmpSelFromPos.x,self.m_tmpSelFromPos.y,
										 html.HTML_FIND_NEAREST_BEFORE);
				if (not self.m_tmpSelFromCell):
					self.m_tmpSelFromCell = m_Cell.GetLastTerminal();

		selcell = cell
		if not selcell:
			if (goingDown):
				selcell = m_Cell.FindCellByPos(x, y,
												 html.HTML_FIND_NEAREST_BEFORE);
				if (not selcell):
					selcell = m_Cell.GetLastTerminal();
			else:
				selcell = m_Cell.FindCellByPos(x, y,
												 html.HTML_FIND_NEAREST_AFTER);
				if (not selcell):
					selcell = m_Cell.GetFirstTerminal()

		#// NB: it may *rarely* happen that the code above didn't find one
		#//	 of the cells, e.g. if wxHtmlWindow doesn't contain any
		#//	 visible cells.
		if ( selcell and self.m_tmpSelFromCell ):
			if not self.m_selection:
				#// start selecting only if mouse movement was big enough
				#// (otherwise it was meant as mouse click, not selection):
				PRECISION = 2;
				diff = self.m_tmpSelFromPos - wx.Point(x,y);
				if (abs(diff.x) > PRECISION or abs(diff.y) > PRECISION):
					self.m_selection = html.HtmlSelection()

			if ( self.m_selection ):
				if ( self.m_tmpSelFromCell.IsBefore(selcell) ):
					self.m_selection.Set(self.m_tmpSelFromPos, self.m_tmpSelFromCell,
										 wx.Point(x,y), selcell);
				else:
					self.m_selection.Set(wx.Point(x,y), selcell,
										 self.m_tmpSelFromPos, self.m_tmpSelFromCell);




	def Idle(self, event):
		if event: event.Skip()
		if not self.mousemoved:
			return
		self.mousemoved = False
		x, y = self.mousecoords
		cellover = self.FindCell(x,y)
		#convert to position including scrolled position
		xx, yy = self.CalcUnscrolledPosition(x, y) 

		if(self.select):
			self.PutMeIn()

		if eq(cellover, self.lastcell):
			return
		if(self.lastcell):
			self.OnCellMouseLeave(self.lastcell, xx, yy)

		if(cellover):
			self.OnCellMouseEnter(cellover, xx, yy)
		self.lastcell = cellover

	#trap link clicks
	def OnLinkClicked(self, *args): pass

	def SetPage(self, text, raw=False, text_colour=None, body_colour=None):
		self.m_selection = None
		return super(HtmlSelectableWindow, self).SetPage(text, raw=raw,		
		text_colour=text_colour, body_colour=body_colour)

		
class HtmlBaseXRC(HtmlBase):
	def __init__(self):
		pre = wx.html.PreHtmlWindow()
		self.PostCreate(pre)
		self.Bind(wx.html.EVT_HTML_LINK_CLICKED, lambda x:x)
		self._setup()
		
