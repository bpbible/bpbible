import re
from backend import filterutils
from backend.book import GetBestRange
from swlib.pysw import SW
from swlib import pysw
import config
from util.debug import *

strongs_re = re.compile(r"strong:([HG])(\d+)")


class OSISParser(filterutils.ParserBase):
	def start_reference(self, attributes):
		attributes = dict(attributes)
		
		# TODO suspend text through this below???
		if (self.u.BiblicalText and 
			not self.u.inXRefNote and 
			"osisref" in attributes):
			# initialize to empty so that addition below will work
			self.refs = ""

		elif(not filterutils.filter_settings["footnote_ellipsis_level"] or not self.u.BiblicalText or
				not self.u.inXRefNote):
			self.success=SW.INHERITED
			return
		
		attributes = dict(attributes)
		#TODO check this
		#TODO check for Bible:Gen.3.5
		self.refs += attributes["osisref"] + ";"
		self.u.suspendLevel += 1
		self.u.suspendTextPassThru = self.u.suspendLevel
	
	def end_reference(self):
		# processed already
		
		if not filterutils.filter_settings["footnote_ellipsis_level"] or not self.u.BiblicalText:
			self.success = SW.INHERITED
			return

		self.u.suspendLevel -= 1
		self.u.suspendTextPassThru = self.u.suspendLevel
		if not self.u.inXRefNote:
			# trim off ;
			ref = self.refs[:-1]
			ref = GetBestRange(ref, context=self.u.key.getText(), abbrev=True)
			
			self.buf += '<a href="bible:%s">%s</a>' %(ref,
				self.u.lastTextNode.c_str())
		
			return
		
	
	def start_w(self, attributes):
		self.strongs_bufs = []
		# w lemma="strong:H03050" wn="008"
		attributes = dict(attributes)
	
		if ("lemma" not in attributes or self.u.suspendTextPassThru or 
			not	filterutils.filter_settings["strongs_headwords"]):
			self.success = SW.INHERITED		
			return

		lemmas = attributes["lemma"]
		for lemma in lemmas.split(" "):
		
			if not lemma.startswith("strong:"):
				dprint(WARNING, "Could not match lemma", value)
				return
			
			headword = self.get_strongs_headword(lemma[7:])
			if not headword:
				self.success = SW.INHERITED
				return
			
			self.strongs_bufs.append(headword)
			
		self.morphbufs = []
		if "morph" in attributes:
			morph = attributes["morph"]
			for attrib in morph.split():
				val = attrib.find(":")
				if val == -1:
					val = attrib
				else:
					val = attrib[val+1:]
				val2 = val
				if val[0] == 'T' and val[1] in "GH" and val[2] in "0123456789":
					val2 = val2[2:]
				if not self.u.suspendTextPassThru:
					self.morphbufs.append("<small><em>(<a href=\"passagestudy.jsp?action=showMorph&type=%s&value=%s\">%s</a>)</em></small>"%(
							SW.URL.encode(morph).c_str(),
							SW.URL.encode(val).c_str(),
							val2))
			
	
	def end_w(self):
		if self.strongs_bufs:
			if self.morphbufs:
				self.buf += " ".join(
					"".join(a) for a in zip(self.strongs_bufs, self.morphbufs)
				)
			else:
				self.buf += " ".join(self.strongs_bufs)
				
			return
		self.success = SW.INHERITED
		
	def start_note(self, attributes):
		attributes = dict(attributes)
		if("type" not in attributes):
			self.success = SW.INHERITED
		
		elif(attributes["type"] in ("crossReference", "x-cross-ref") and
				filterutils.filter_settings["footnote_ellipsis_level"]):
			self.u.inXRefNote=True
			self.u.suspendLevel += 1
			self.u.suspendTextPassThru = self.u.suspendLevel
			self.refs=""
		else:
			self.success = SW.INHERITED

	def end_note(self):
		ellipsis = int(filterutils.filter_settings["footnote_ellipsis_level"])
	
		if(self.u.inXRefNote and ellipsis):
			refs = str(pysw.VerseList(self.refs)).split(";")

			self.buf += filterutils.ellipsize(refs, self.u.key.getText(),
					ellipsis)

			self.u.inXRefNote = False
			self.u.suspendLevel -= 1
			self.u.suspendTextPassThru = self.u.suspendLevel
			
			# clear the last segment
			# Otherwise in Ex 6:3 in ESV where there is a divinename right
			# after a note, it prints out contents of note uppercase
			self.u.lastSuspendSegment.size(0)
			return
		self.success = SW.INHERITED	
	
		

class OSISRenderer(SW.RenderCallback):
	def __init__(self):
		super(OSISRenderer, self).__init__()
		self.thisown = False

	@filterutils.me
	@filterutils.report_errors
	@filterutils.OSISUserData
	def run(self, buf, token, u):
		if not filterutils.filter_settings["use_osis_parser"]: 
			return "", SW.INHERITED
	
		# w lemma="strong:H03050" wn="008"		
		p.init(token,u)
		p.feed("<%s>" % token)
		return p.buf, p.success

	def set_biblemgr(self, biblemgr):
		p.set_biblemgr(biblemgr)

p = OSISParser()
