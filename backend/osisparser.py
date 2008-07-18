from backend import filterutils
from swlib.pysw import SW, GetBestRange
from util.debug import dprint, WARNING

class OSISParser(filterutils.ParserBase):
	def __init__(self, *args, **kwargs):
		super(OSISParser, self).__init__(*args, **kwargs)
		self.did_xref = False
		
		self.strongs_bufs = []
		self.morph_bufs = []
	
	def start_reference(self, attributes):
		if "osisref" not in attributes:
			self.ref = None
			self.success = SW.INHERITED
			dprint(WARNING, "No osisref in reference", attributes)
			
			return
			

		#TODO check this
		#TODO check for Bible:Gen.3.5
		self.ref = attributes["osisref"]
		idx = self.ref.find(":")
		if idx != -1:
			self.ref = self.ref[idx+1:]

		self.u.suspendLevel += 1
		self.u.suspendTextPassThru = self.u.suspendLevel
	
	def end_reference(self):
		if self.ref is None:
			self.success = SW.INHERITED
			return

		self.u.suspendLevel -= 1
		self.u.suspendTextPassThru = self.u.suspendLevel

		ref = GetBestRange(self.ref, context=self.u.key.getText(), abbrev=True)
		
		self.buf += '<a href="bible:%s">%s</a>' % (
			ref, self.u.lastTextNode.c_str()
		)
	
	def start_w(self, attributes):
		self.strongs_bufs = []
		# w lemma="strong:H03050" wn="008"
	
		if ("lemma" not in attributes or self.u.suspendTextPassThru or 
			not	filterutils.filter_settings["strongs_headwords"]):
			self.success = SW.INHERITED		
			return

		lemmas = attributes["lemma"]
		for lemma in lemmas.split(" "):
		
			if (not lemma.startswith("strong:") and 
				not lemma.startswith("x-Strongs:") and
				not lemma.startswith("Strong:")):
				dprint(WARNING, "Could not match lemma", lemma)
				self.success = SW.INHERITED		
				
				return
			
			headword = self.get_strongs_headword(lemma[lemma.index(":")+1:])
			if not headword:
				self.success = SW.INHERITED
				return
			
			self.strongs_bufs.append(headword)
			
		self.morph_bufs = []
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
					self.morph_bufs.append("<small><em>(<a href=\"passagestudy.jsp?action=showMorph&type=%s&value=%s\">%s</a>)</em></small>"%(
							SW.URL.encode(morph).c_str(),
							SW.URL.encode(val).c_str(),
							val2))
			
	
	def end_w(self):
		if self.strongs_bufs:
			self.buf += " ".join(self.strongs_bufs + self.morph_bufs)
			return

		self.success = SW.INHERITED
		
	def start_note(self, attributes):
		self.did_xref = False
		
	
		if "type" not in attributes or "swordFootnote" not in attributes:
			self.success = SW.INHERITED
		
		elif(attributes["type"] in ("crossReference", "x-cross-ref") and
				filterutils.filter_settings["footnote_ellipsis_level"]):
			footnoteNumber = attributes["swordFootnote"]
			footnotes = SW.Buf("Footnote")			
			refList = SW.Buf("refList")
			number = SW.Buf(footnoteNumber)
			map = self.u.module.getEntryAttributesMap()
			try:
				refs = map[footnotes][number][refList].c_str()
			except IndexError:
				dprint(WARNING, "Error getting Footnote '%s' refList" % 
					footnoteNumber)
				self.success = SW.INHERITED
				return

			if not refs:
				# if there weren't any references, just do the usual
				self.success = SW.INHERITED
				return
				

			self.u.inXRefNote = True
			self.u.suspendLevel += 1
			self.u.suspendTextPassThru = self.u.suspendLevel
			
			self.buf += filterutils.ellipsize(
				refs.split(";"), 
				self.u.key.getText(),
				int(filterutils.filter_settings["footnote_ellipsis_level"])
			)
			self.did_xref = True
			
			
		else:
			self.success = SW.INHERITED

	def end_note(self):
		if self.did_xref:
			self.u.inXRefNote = False
			self.u.suspendLevel -= 1
			self.u.suspendTextPassThru = self.u.suspendLevel
			self.did_xref = False
			
			return
		
			

		self.success = SW.INHERITED	
	
		

class OSISRenderer(SW.RenderCallback):
	def __init__(self):
		super(OSISRenderer, self).__init__()
		self.thisown = False

	@filterutils.return_success
	@filterutils.report_errors
	@filterutils.OSISUserData
	def run(self, buf, token, u):
		if not filterutils.filter_settings["use_osis_parser"]: 
			return "", SW.INHERITED
	
		# w lemma="strong:H03050" wn="008"		
		p.process(token, u)
		return p.buf, p.success

	def set_biblemgr(self, biblemgr):
		p.set_biblemgr(biblemgr)

p = OSISParser()

