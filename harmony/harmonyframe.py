#from Sword2 import *
import sys

from harmony import read_harmony
#import ParseHarmony
import glob
import wx
from swlib.pysw import GetBestRange
from wx import xrc
import backend.bibleinterface as BI
from backend.verse_template import VerseTemplate
from util import noop
from util.debug import dprint, MESSAGE
from util import osutils

from xrc.harmonyfrm_xrc import xrcHarmonyFrame, xrcHarmonyPanel
import config, guiconfig
from protocols import protocol_handler
from util.configmgr import config_manager

harmony_settings = config_manager.add_section("Harmony")
harmony_settings.add_item("last_harmony", "")


def on_harmony_click(frame, href, url):
	num = int(url.getHostName())
	frame.owner.set_pericope(frame.owner.harmony.sections[num])

protocol_handler.register_handler("harmony", on_harmony_click)
protocol_handler.register_hover("harmony", noop)

class HarmonyFrame(xrcHarmonyFrame):
	"""HarmonyFrame: The main frame containing everything."""
	def __init__(self, parent):
		super(HarmonyFrame, self).__init__(parent)
		self.setup()
	
	def status(self, msg):
		#dprint(MESSAGE, msg)
		pass
	
	def setup(self):
		self.harmonies = glob.glob(r"harmony/*.harm")
		self.status("Processing Harmonies")
		self.harmonies = [read_harmony.process_harmony(harmony, self.status) 
			for harmony in self.harmonies]

		self.status("Done processing Harmonies")
		
		selection = 0
		last_harmony = harmony_settings["last_harmony"]
		harmony_names = [h.name for h in self.harmonies]

		if last_harmony in harmony_names:
			selection = harmony_names.index(last_harmony)

		self.harmony = self.harmonies[selection]

		#self.harmony_notebook.InsertPage(0, self.frame, self.harmony.name, True)
		parent = self.harmony_notebook#.Parent
		#self.frame = HarmonyPanel(parent)
		#parent.Sizer.Add(self.frame, 1, wx.GROW)
		#parent.Sizer.Layout()
		
		for harmony in self.harmonies:
			self.harmony_notebook.AddPage(
			#wx.Window(self.harmony_notebook, size=(0,0)), 
			HarmonyPanel(self.harmony_notebook), 
			#self.frame,
			harmony.name, True)
			

		self.frame = self.harmony_notebook.GetPage(selection)
		self.harmony_notebook.SetSelection(selection)

		# The following line stops it crashing if settings are changed
		self.Bind(wx.EVT_CLOSE, self.HarmonyFrameClose)

		self.harmony_notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
				self.harmony_changed)

		#self.gosp = [("Matt","M"), ("Mark","m"), ("Luke","L"), ("John","J")]
		self.frame.harmony = self.harmony
		self.frame.fill_pericope_list()
		#self.Fit()
		self.SetSize((800, 600))
		self.SetMinSize((400, 300))
		guiconfig.mainfrm.bible_observers += self.on_settings_change
		guiconfig.mainfrm.on_close += self.Destroy
		#l1=sorted(ParseHarmony.pericopeintlist.items(), lambda x,y: x[0]-y[0])
#		for number, peri in l1: 
#			gospels = []
#			for gospel in peri.sources:
#				gospels.append(gospel.gospel)
#
#			s=""
#			for a in self.gosp:
#				if a[0] in gospels:
#					s+=a[1]
#				else:
#					s+="-"
#				
#			self.pericopechoice.Append("%d: %s | %s" % (number, peri.title, s))
#			#ParseHarmony.pericopeintlist[a].title))
#		self.pericopechoice.SetSize(self.pericopechoice.GetBestSize())
		
#		last=self.conf.get("GospelHarmony", "LastPericope")
#		if last:
#			self.set_pericope(last)
#		else:

	def on_settings_change(self, event):
		if event.settings_changed:
			self.frame.refresh()

	def Destroy(self):
		# remove from the close list
		guiconfig.mainfrm.on_close -= self.Destroy
		self.harmony_notebook.Unbind(wx.EVT_NOTEBOOK_PAGE_CHANGED)
		
		#if osutils.is_gtk():
		#	while self.harmony_notebook.PageCount:
		#		print "Removing page 0"
		#		print self.harmony_notebook.PageCount
		#		self.harmony_notebook.RemovePage(0)
		#

		guiconfig.mainfrm.bible_observers -= self.on_settings_change
		super(HarmonyFrame, self).Destroy()
	
	def harmony_changed(self, event):
		if event:
			sel = event.GetSelection()
			event.Skip()
		else:
			sel = self.harmony_notebook.GetSelection()
		
		self.harmony = self.harmonies[sel]
		self.frame = self.harmony_notebook.GetPage(sel)
		
		harmony_settings["last_harmony"] = self.harmony.name
		self.set_harmony(self.harmony.name)

	#def FillHarmonyList(self):
	#	#self.harmony_notebook.SetPageText(0, self.harmonies[0].name)
	#	for a in self.harmonies:
	#		self.harmony_notebook.InsertPage(0, self.frame, a.name, True)

		#self.harmony_notebook.SetSelection(0)

			

	def HarmonyFrameClose(self, event=None):
		self.Destroy()

	def AboutClick(self, event):
		wx.MessageBox("Gospel Harmony Viewer 0.01 (c) Ben Morgan 2006-2008"
		"\nBuilt Using the Sword Project @ crosswire.org and "
		"\nthe Composite Gospel Index from www.semanticbible.com")
		
	#def OnPeriChoice(self, event):
	#	choice=event.GetString()
	#	ind=choice.find(":")
	#	if ind == -1:
	#		wx.MessageBox("Could not find pericope number")
	#		return
	#	choice=choice[:ind]

	#	self.set_pericope("Pericope.%03d" % int(choice))

	def set_harmony(self, name):
		for harmony in self.harmonies:
			if harmony.name == name:
				self.frame.harmony = harmony
				break
		else:
			print "Harmony %s not found" % name
			return
		
		self.frame.fill_pericope_list()

class HarmonyPanel(xrcHarmonyPanel):
	def __init__(self, parent):
		super(HarmonyPanel, self).__init__(parent)
		self.setup()

	def setup(self):
		self.pericope_list.Bind(wx.EVT_TREE_SEL_CHANGED, 
				self.on_pericope_change)

		self.tool_bible_ref.Bind(wx.EVT_TEXT_ENTER, self.bible_ref_enter)
		self.Bind(wx.EVT_TOOL, self.bible_ref_enter, id=xrc.XRCID('tool_go'))				

		self.bible_text.owner = self
		self.bible_text.book = BI.biblemgr.bible
		self.currentverse = ""
		self.currentperi = ""
	
	def refresh(self, event=None):
		#if not self.currentverse: 
		#	return

		ref = self.currentverse
		self.set_pericope()
		return
	
	def bible_ref_enter(self, event=None):
		self.update_bible_ui(self.tool_bible_ref.GetValue())
	
	def fill_pericope_list(self):
		if self.harmony.loaded:
			return
		busy_info = wx.BusyInfo(_("Loading harmony"))
		self.harmony.load()
		del busy_info

		def FillList(parent, child):
			tree_item = self.pericope_list.AppendItem(parent, child.name)
			self.pericope_list.SetPyData(tree_item, child)

			for item in child.children:
				FillList(tree_item, item)

			return tree_item

		self.pericope_list.DeleteAllItems()
		self.root = self.pericope_list.AddRoot("Root")
		#for a in self.harmonies:
		root = FillList(self.root, self.harmony.top)
		wx.CallAfter(self.pericope_list.Expand, root)
			#h=self.pericope_list.AppendItem(self.root, a.name, \
			#	data=wx.TreeItemData(a))
			#for b in a.top.children: FillList(h, b, wx.TreeItemData(b))

		#for a in self.harmony.top.children:
		#	FillList(self.root, a, wx.TreeItemData(a))
		
		self.set_pericope(self.harmony.top)

	def status(self, msg):
		#dprint(MESSAGE, msg)
		pass

	def on_pericope_change(self, event):
		item = event.GetItem()
		data = self.pericope_list.GetPyData(item)

		if self.currentperi == data:
			return

		#if data.harmony != self.harmony:
		#	self.harmony = data.harmony

		self.set_pericope(data)

	def update_bible_ui(self, ref="", version=""):
		if not ref:
			#Just refreshing, not a new verse
			return self.refresh()

		self.currentverse = ref
		peri = self.harmony.top.find_reference(ref)
		if not peri:
			wx.MessageBox(_("%s is not in this harmony") % ref)
			return

		#peri, gospel = ParseHarmony.reverseindex[index]
		self.status("Setting Pericope")	
		self.set_pericope(peri)

	def set_pericope(self, peri=None):
		#self.currentverse="Who knows?"
		#if((peri=="table") or (not peri and self.currentperi=="table")):
		#	self.currentperi="table"
		#	self.DoTable()
		#	return
#		self.status(peri.fulldescription)
		if not peri:
			peri = self.currentperi

		self.currentperi = peri
		
		self.status("Selecting tree item")
		self.select_tree_item(peri)
		
		self.load_html()
	
	def load_html(self):
		self.status("Loading html")
	
		peri = self.currentperi
		if not peri.visible:
			self.write_toc(peri)
			return

		verses = self.pericope_header(peri)
		verses += ("<center><b>%s</b></center><br>" % (peri.fulldescription))

		verses += ''.join(self.render_refs(ref) for ref in peri.references)

		self.bible_text.SetPage(verses)

#		verses += "<table width=95%><tr><td align=left>"
#		if(pericope.previous):
#			peri = ParseHarmony.pericopelist[pericope.previous]
#			verses+="<a href='%s'><img src='%s'>%s</a><br>%s" % (peri.about,
#			"back.xpm", peri.number, peri.title)
		
#		verses+="</td><td align=right>"
#		if(pericope.next):
#			peri = ParseHarmony.pericopelist[pericope.next]
##			verses+="<a href='%s'>%s<img src='%s'></a><br>%s" % (peri.about,
#			peri.number, "forward.xpm", peri.title)
	
#		verses+="</td></tr></table>"

	def write_toc(self, peri):
		if(isinstance(peri, read_harmony.Harmony)):
			print "TOP"
			item = peri.top
		else:
			item = peri

		text = self.pericope_header(item)
		text += "<b>%s</b>" % peri.fulldescription
		if peri.references and peri.references[0]:
			for refs in peri.references:
				text += "<br />"
				text += ";".join(
					'<a href="bible:%s">%s</a>' % (ref, ref) for ref in refs
				)

		text += "<br />" + self.write_toc_children(item)
		self.bible_text.SetPage(text)
	
	def write_toc_children(self, peri):
		text = "<b></b><br /><ul>"
		for child in peri.children:
			text += "<li><a href='harmony:%d'>%s</a></li>" % (
				child.id, child.name
			)
		text += "</ul>"
		return text
	
	def pericope_header(self, peri):
		if not peri.parent:
			return ""

		parent = peri.parent
		up = ("<a href='harmony:%s'><img src='%sgo-up.png'>&nbsp;%s</a>" % 	
			(parent.id, config.graphics_path, parent.name))

		up = "<td align=CENTER>%s</td>" % up
		
		text = "<table width=100%><tr>"
		#text = text % s2
				
		item = peri.previous
		if item: 
			text += ("<td align=LEFT><a href='harmony:%s'>"
				  "<img src='%sgo-previous.png'>&nbsp;%s</a></td>" % 
				  (item.id, config.graphics_path, item.name))
		
		text += up
		item = peri.next
		if item: 
			text += ("<td align=RIGHT><a href='harmony:%s'>"
				  "<img src='%sgo-next.png'>&nbsp;%s</a></td>" % 
				  (item.id, config.graphics_path, item.name))
		
		return text + "</tr></table>"

				


	def render_refs(self, refs):		
		self.status("Rendering %s" % refs)
	
		if not refs: 
			return ""

		verses = "<table border=1 width=95%>\n\t<tr >\n"
		num = len(refs)
		width = (100/num)
		
		widths = [0]*num
		total = 0

		for j in range(num):
			if j == len(refs)-1: #last item
				widths[j] = str(100-total)
			else:
				widths[j] = str(width)
				total += width
		
		# header
		for ref in refs:
			#refs.append(verse)
			verses += """\
			<th align=center valign=center>
				<b>%s</b>
			</th>
			""" % GetBestRange(ref, userOutput=True)
		
		verses += "\t</tr>\n"
		
		#text
		verses += "\t<tr valign=top>\n"

		body = "\t\t$versenumber $text "
		header = "\t\t<td VALIGN='TOP'>"# width=" + width + "%>\n"
		footer = "\t\t</td>\n"
			
		template = VerseTemplate(body=body, header=header, footer=footer)
		if BI.biblemgr.bible.version is None:
			verses += header + footer
		else:
			try:
				BI.biblemgr.bible.templatelist.append(template)

				for ref, width in zip(refs, widths):
					self.status(" Getting reference %s"%ref)
				
					ref_text = BI.biblemgr.bible.GetReference(
						ref.GetBestRange()
					)
					verses += ref_text
					self.status(" /Getting reference")
					
				verses += "\t</tr>\n<tr valign=top>\n"

				verses += "</tr></table>"

			finally:
				BI.biblemgr.bible.templatelist.pop()

		return verses

	# TODO: table?
	# def DoTable(self):
	# 	html="<table width=95% border=1><thead><td>Pericopes</td>"
	# 	for a in self.gosp:
	# 		html+="<td>%s</td>" % a[0]
	# 	html+="</thead>"
	# 	for a in ParseHarmony.pericopeintlist.values():
	# 		html+="<tr>"

	# 		html+="<td><a href=harmony:%s>%s</a></td>" % (a.about, a.title)
	# 		for gosp in self.gosp:
	# 			st2="<td>%s</td>"
	# 			st=""
	# 			gospel=ParseHarmony.getPericopeFromGospel(a, gosp[0])
	# 			if gospel:
	# 				st=gospel.range
	# 			html += st2 % st
	# 		html+="</tr>"
	# 	html+="</table>"
	# 	self.bible_text.SetPage(html)

	def select_tree_item(self, peri):
		#select the item in the tree
		def find_tree_item(current):
			child, cookie = self.pericope_list.GetFirstChild(current)
			while child:
				if self.pericope_list.GetPyData(child) == peri:
					return child

				ansa = find_tree_item(child)
				if ansa: 
					return ansa

				child, cookie = self.pericope_list.GetNextChild(current, cookie)

		item = find_tree_item(self.root)
		assert item, "Didn't find pericope in tree"
		
		self.pericope_list.SelectItem(item)
		
	#def random_verse(self, event):
	#	self.set_pericope(random.choice(ParseHarmony.reverseindex.values())[0])


class HarmonyFrameXRC(HarmonyFrame):
	def __init__(self):
		pre = wx.PreFrame()
		self.PostCreate(pre)
		self.Bind(wx.EVT_WINDOW_CREATE, self.OnCreate)
	
	def OnCreate(self, event):
		self.Unbind(wx.EVT_WINDOW_CREATE)
		wx.CallAfter(self.setup)
		event.Skip()
		return True


class MyApp(wx.App):
	def OnInit(self):
		#self.res = xrc.XmlResource( "mainfrm2.xrc" )
		frame = HarmonyFrame(None)#self.res.LoadFrame(None,  "MainFrame" )
		self.SetTopWindow(frame)
		frame.Show(True)
		return True

if __name__ == '__main__':
	if(len(sys.argv)>1):
		execfile(sys.argv[1:])
		sys.exit()
	app = MyApp(0)
	app.MainLoop()
