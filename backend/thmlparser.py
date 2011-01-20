from backend import filterutils
from swlib.pysw import SW, GetVerseStr, GetBestRange
from util.debug import dprint, MESSAGE
from util.unicode import to_unicode

class ThMLParser(filterutils.ParserBase):
	def start_scripRef(self, xmltag):
		if (#self.u.module.Type() ==  "Biblical Texts" or 
			not	filterutils.filter_settings["expand_thml_refs"]):
			# we don't do anything here. This may change when I have a module
			# to test it on...
			self.success = SW.INHERITED
			return
		
		self.scripRef_passage = xmltag.getAttribute("passage")
		self.u.suspendTextPassThru = True
	
	def end_scripRef(self, xmltag):
		if (#self.u.module.Type() ==  "Biblical Texts" or 
			not	filterutils.filter_settings["expand_thml_refs"]):
		
			self.success = SW.INHERITED
			return

		refList = self.scripRef_passage
		if self.u.module.Type() == "Biblical Texts":
			#self.success = SW.INHERITED
			if refList:
				dprint(MESSAGE, "FOUND ThML reflist in Bible", refList)
				self.success = SW.INHERITED
				return
				
			else:
				refs = self.u.lastTextNode.c_str().split(";")
				self.buf += filterutils.ellipsize(self.u.version.c_str(), refs, self.u.key.getText())

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
			last = GetVerseStr(self.u.key.getText())
			for item in refList.split(";"):
				vref = item
				vref = GetBestRange(to_unicode(vref), context=last, use_bpbible_locale=True)
				items.append('<a href="bible:%s">%s</a>' %(vref, item))
				last = vref
			self.buf += "; ".join(items)

		# let text resume to output again
		self.u.suspendTextPassThru = False
	
	def start_sync(self, xmltag):
		# This handles strongs numbers

		# <sync type="Strongs" value="G1985" />
		type = xmltag.getAttribute("type")
		value = xmltag.getAttribute("value")
		if type != "Strongs" or not value:
			#not filterutils.filter_settings["strongs_headwords"]):
			self.success = SW.INHERITED
			return
			
		headword = self.get_strongs_headword(value)
		if not headword:
			self.success = SW.INHERITED	
			return

		self.buf += headword

	def start_harmonytable(self, xmltag):
		from backend.bibleinterface import biblemgr
		references = xmltag.getAttribute('refs').split("|")
		if not references:
			return

		header_row = u"<tr>%s</tr>" % (
			u"".join(
				u"<th>%s</th>" % GetBestRange(reference, userOutput=True)
				for reference in references
			))
		# This is a nasty hack to work around the fact that ThML rendering in
		# SWORD is not properly reentrant.
		# Without copying the internal dictionary some references do not
		# display at all.
		my_internal_dict = self.__dict__.copy()
		body_row = u"<tr>%s</tr>" % (
			u"".join(
				u"<td>%s</td>" % biblemgr.bible.GetReference(reference)
				for reference in references
			))
		self.__dict__ = my_internal_dict
		table = u'<table class="harmonytable chapterview">%s%s</table>' % (header_row, body_row)
		self.buf += table.encode("utf8")

	def end_harmonytable(self, xmltag):
		# Prevent SWORD choking on this.
		pass

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
	
		p.process(token, userdata)

		return p.buf, p.success	

	def set_biblemgr(self, biblemgr):
		p.biblemgr = biblemgr


p = ThMLParser()		

