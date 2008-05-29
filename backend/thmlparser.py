from backend import filterutils
from swlib.pysw import SW, GetVerseStr, GetBestRange
from util.debug import dprint, MESSAGE

class ThMLParser(filterutils.ParserBase):
	def start_scripref(self, attributes):
		if (#self.u.module.Type() ==  "Biblical Texts" or 
			not	filterutils.filter_settings["expand_thml_refs"]):
			# we don't do anything here. This may change when I have a module
			# to test it on...
			self.success = SW.INHERITED
			return
		
		self.start_tag = dict(attributes)
		self.u.suspendTextPassThru = True
	
	def end_scripref(self):
		if (#self.u.module.Type() ==  "Biblical Texts" or 
			not	filterutils.filter_settings["expand_thml_refs"]):
		
			self.success = SW.INHERITED
			return

		refList = self.start_tag.get("passage", None)
		if self.u.module.Type() == "Biblical Texts":
			#self.success = SW.INHERITED
			if refList:
				dprint(MESSAGE, "FOUND ThML reflist in Bible", refList)
				self.success = SW.INHERITED
				return
				
			else:
				refs = self.u.lastTextNode.c_str().split(";")
				self.buf += filterutils.ellipsize(refs, self.u.key.getText())

			self.u.suspendTextPassThru = False
			
			return

		# if we have a ref list, then we need to display the text and just
		# pop up usual thing
		if refList:
			self.buf += ("<a href=\"passagestudy.jsp?action=showRef&type=scripRef&value=%s&module=%s\">") % (
				SW.URL.encode(refList).c_str(), ""
			)
			self.buf += self.u.lastTextNode.c_str()
			self.buf += "</a>"
		else:
			# break it up into its constituent parts and display each as a
			# separate link
			refList = self.u.lastTextNode.c_str()
		
			items = []
			vkey = SW.VerseKey.castTo(self.u.key)
			if (vkey):
				last = GetVerseStr(vkey.getText())
			else:
				last = ""
			for item in refList.split(";"):
				vref = item
				vref = GetBestRange(vref, context=last)
				items.append('<a href="bible:%s">%s</a>' %(vref, item))
				last = vref
			self.buf += "; ".join(items)

		# let text resume to output again
		self.u.suspendTextPassThru = False
	
	def start_sync(self, attributes):
		# This handles strongs numbers

		# <sync type="Strongs" value="G1985" />
		attributes = dict(attributes)
		if ("type" not in attributes or attributes["type"]!="Strongs" or 
			"value" not in attributes or 
			not filterutils.filter_settings["strongs_headwords"]):
			self.success = SW.INHERITED
			return
			
		headword = self.get_strongs_headword(attributes["value"])
		if not headword:
			self.success = SW.INHERITED	
			return

		self.buf += headword

class THMLRenderer(SW.RenderCallback):
	def __init__(self):
		super(THMLRenderer, self).__init__()
		self.thisown = False

	@filterutils.return_success
	@filterutils.report_errors
	@filterutils.ThMLUserData
	def run(self, buf, token, userdata):
		if not filterutils.filter_settings["use_thml_parser"]: 
			return "", SW.INHERITED
	
		p.init(token, userdata)
		p.feed("<%s>" % token)

		return p.buf, p.success	

	def set_biblemgr(self, biblemgr):
		p.biblemgr = biblemgr


p = ThMLParser()		

