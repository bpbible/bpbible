from backend import filterutils
from swlib.pysw import SW, GetBestRange
from util.debug import dprint, WARNING, ERROR
import os.path
import quotes

class OSISParser(filterutils.ParserBase):
	def __init__(self, *args, **kwargs):
		super(OSISParser, self).__init__(*args, **kwargs)
		self.reset()
	
	def reset(self):
		self.did_xref = False
		
		self.strongs_bufs = []
		self.morph_bufs = []
		self.was_sword_ref = False
		self.in_indent = False
		self.in_morph_seg = False
		self._end_hi_stack = []
		self.in_lg = False
		self._quotes = []
		self._quotes_data = []

	def write_quote(self, qID, who, start):
		if who == "NULL": return
		if start:
			self.write('<span class="quote" qID="%s" who="%s" title="%s">' % (qID, who, who))
		else:
			self.write("</span>")

	def blocklevel_start(self):
		for qID, who in self._quotes_data:
			self.write_quote(qID, who, True)
			
	def blocklevel_end(self):
		for qID, who in self._quotes_data:	
			self.write_quote(qID, who, False)

	def block_start(self):
		self.reset()
		
	def block_end(self):
		if self.in_lg:
			return '</blockquote>'
		
		return ""

	def start_abbr(self, xmltag):
		exp = xmltag.getAttribute("expansion")
		if not exp:
			dprint(WARNING, "abbr tag does not have expansion attribute.")

		self.write('<abbr title="%s">' % SW.URL.encode(exp).c_str())

	def end_abbr(self, xmltag):
		self.write("</abbr>")

	def start_q(self, tag):
		style, quote_mapping = quotes.get_quotes()
		#print "Q", tag.toString()
		type      = tag.getAttribute("type");
		who       = tag.getAttribute("who");
		tmp		  = tag.getAttribute("level");
		level	  = int(tmp) if tmp else 1
		mark      = tag.getAttribute("marker");
		# open <q> or <q sID... />
		if ((not tag.isEmpty() and not tag.isEndTag()) or (tag.isEmpty() and tag.getAttribute("sID"))):
			# if <q> then remember it for the </q>
			if not tag.isEmpty():
				self._quotes.append(tag.toString())

			# Do this first so quote marks are included as WoC
			if (who == "Jesus"):
				self.write("<span class='WoC'>")

			# first check to see if we've been given an explicit mark
			if mark:
				self.write(mark)
			
			# alternate " and '
			elif (self.u.osisQToTick):
				self.write('"' if (level % 2) else '\'')
		
			if tag.getAttribute("sID"):
				qID = tag.getAttribute("sID").replace(".", "_")
				d = quote_mapping.get(qID, "")
				if not d:
					dprint(WARNING, "No who found for qID", qID)

				self.write_quote(qID, d, True)
				self._quotes_data.append((qID, d))
			else:
				#print "non-sid Start", tag.toString()
				pass
				
		# close </q> or <q eID... />
		elif ((tag.isEndTag()) or (tag.isEmpty() and tag.getAttribute("eID"))):
			# if it is </q> then pop the stack for the attributes
			if (tag.isEndTag() and self._quotes):
				tagData  = self._quotes.pop()
				qTag = SW.XMLTag(tagData)

				type    = qTag.getAttribute("type");
				who     = qTag.getAttribute("who");
				tmp     = qTag.getAttribute("level");
				level   = int(tmp) if tmp else 1
				mark    = qTag.getAttribute("marker");

			qID = tag.getAttribute("eID")
			if qID:
				qID = qID.replace(".", "_")
			
				if not self._quotes_data:
					dprint(ERROR, "Quotes data empty", qID,
					self.u.key.getText())

				else:
					d = self._quotes_data.pop()
					if d[0] != qID:
						dprint(ERROR, "Mismatching closing quotes", d, qID)

					self.write_quote(d[0], d[1], False)
			#else:
			#	print tag.toString()

			# first check to see if we've been given an explicit mark
			if (mark):
				self.write(mark)

			# finally, alternate " and ', if config says we should supply a mark
			elif (self.u.osisQToTick):
				self.write('"' if (level % 2) else '\'')

			# Do this last so quote marks are included as WoC
			if (who == "Jesus"):
				self.write("</span>")

					
	end_q = start_q
	def start_hi(self, xmltag):
		assert not xmltag.isEmpty(), "Hi cannot be empty"
		type = xmltag.getAttribute("type")
		types = {
			"acrostic": ("<i>", "</i>"),
			"bold": ("<b>", "</b>"),
			"b": ("<b>", "</b>"),
			"x-b": ("<b>", "</b>"),
			"emphasis": ("<em>", "</em>"),
			"illuminated": ("<i>", "</i>"),
			"italic": ("<i>", "</i>"),
			"line-through": ('<span class="line-through">', "</span>"),
			"normal": ("", ""),
			"ol": ('<span class="overline">', "</span>"),
			"small-caps": ('<span class="small-caps">', "</span>"),
			"sub": ("<sub>", "</sub>"),
			"super": ("<sup>", "</sup>"),
			"underline": ("<u>", "</u>"),
		}
		if type not in types:
			dprint(WARNING, "Unhandled hi type", type)
			type = "italic"
		
		start, end = types[type]
		self.buf += start
		self._end_hi_stack.append(end)
	
	def end_hi(self, xmltag):
		self.buf += self._end_hi_stack.pop()
		
	def start_reference(self, xmltag):
		self.ref = xmltag.getAttribute("osisRef")
		if not self.ref:
			self.ref = None
			self.success = SW.INHERITED
			dprint(WARNING, "No osisRef in reference", xmltag.toString())
			
			return
			

		#TODO check this
		#TODO check for Bible:Gen.3.5
		idx = self.ref.find(":")
		self.was_sword_ref = False
		
		if idx != -1:
			if not self.ref[:idx].startswith("Bible"):
				self.ref = "sword://%s/%s" % (
					self.ref[:idx], SW.URL.encode(self.ref[idx+1:]).c_str()
				)
				self.was_sword_ref = True
			else:
				self.ref = self.ref[idx+1:]

		self.u.suspendLevel += 1
		self.u.suspendTextPassThru = self.u.suspendLevel
	
	def end_reference(self, xmltag):
		if self.ref is None:
			self.success = SW.INHERITED
			return

		self.u.suspendLevel -= 1
		self.u.suspendTextPassThru = self.u.suspendLevel

		if self.was_sword_ref:
			self.buf += '<a href="%s">%s</a>' % (
				self.ref, self.u.lastTextNode.c_str()
			)
		else:			
			ref = GetBestRange(self.ref, abbrev=True, use_bpbible_locale=True)
			self.buf += '<a href="bible:%s">%s</a>' % (
				ref, self.u.lastTextNode.c_str()
			)
			
	def start_lb(self, xmltag):
		type = xmltag.getAttribute("type")
		if not xmltag.isEmpty():
			print "Can lb's really be non-empty?"
		if type == "x-end-paragraph":
			self.blocklevel_end()
			self.buf += "</p>"
		elif type == "x-begin-paragraph":
			self.buf += "<p>"
			self.blocklevel_start()

	def start_w(self, xmltag):
		self.strongs_bufs = []
		self.morph_bufs = []
		self.was_G3588 = None
		# w lemma="strong:H03050" wn="008"
	
		lemmas = xmltag.getAttribute("lemma") or ""
		if self.u.suspendTextPassThru:
			#(not lemmas or 
			#not	filterutils.filter_settings["strongs_headwords"]):
			dprint(WARNING, "W while suspended?", xmltag.toString())
			self.success = SW.INHERITED		
			return

		# TODO: gloss, xlit?, POS?

		for lemma in lemmas.split(" "):
		
			if (not lemma.startswith("strong:") and 
				not lemma.startswith("x-Strongs:") and
				not lemma.startswith("Strong:")):
				if lemma:
					dprint(WARNING, "Could not match lemma", lemma)
				#self.success = SW.INHERITED
				continue
				
				#return
			
			strongs = lemma[lemma.index(":")+1:]
			if self.was_G3588 is None and strongs == "G3588":
				self.was_G3588 = True
			else:
				self.was_G3588 = False
		
			headword = self.get_strongs_headword(strongs)
			if not headword:
				self.success = SW.INHERITED
				return
			
			self.strongs_bufs.append(headword)
			
		morph = xmltag.getAttribute("morph")
		if morph:
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
					self.morph_bufs.append("<a class=\"morph\" href=\"morph://%s/%s\">%s</a>"%(
							SW.URL.encode(morph).c_str(),
							SW.URL.encode(val).c_str(),
							val2))
		
		if self.strongs_bufs or self.morph_bufs:
			self.u.suspendLevel += 1
			self.u.suspendTextPassThru = self.u.suspendLevel

		if xmltag.isEmpty(): 
			self.end_w(xmltag)
			
	
	def end_w(self, xmltag):
		if self.strongs_bufs or self.morph_bufs:
			self.u.suspendLevel -= 1
			self.u.suspendTextPassThru = self.u.suspendLevel
	
		if self.was_G3588 and not self.u.lastSuspendSegment.size():
			# and not self.morph_bufs:
			# don't show empty 3588 tags
			return
			
		if self.strongs_bufs or self.morph_bufs:
			self.buf += '<span class="strongs-block"><span class="strongs_word">'
			self.buf += self.u.lastSuspendSegment.c_str() or "&nbsp;"
			# empty that in case of adjacent words with no space (see issue 210)
			self.u.lastSuspendSegment.size(0)
			self.buf += '</span><span class="strongs"><span class="strongs_headwords">'
			self.buf += "".join(self.strongs_bufs) or "&nbsp;"
			if self.morph_bufs:
				self.buf += '</span><span class="strongs_morph">'
				self.buf += "".join(self.morph_bufs)

			self.buf += "</span></span></span>"
			return

		self.success = SW.INHERITED
		
	def start_note(self, xmltag):
		self.did_xref = False
		
	
		type = xmltag.getAttribute("type")
		footnoteNumber = xmltag.getAttribute("swordFootnote")
		if not type:
			print "Not type - module bug", xmltag.toString()
			type = "missing"
		if not type or not footnoteNumber:
			if type != "x-strongsMarkup":
				print "FAILED", xmltag.toString()
			self.success = SW.INHERITED
			return
		
		was_xref = type in ("crossReference", "x-cross-ref")
		
		footnote_type = "n"		
		if was_xref:
			footnote_type = "x"

		expand_crossref = filterutils.filter_settings["footnote_ellipsis_level"]
		footnotes = SW.Buf("Footnote")
		refList = SW.Buf("refList")
		n = SW.Buf("n")
		number = SW.Buf(footnoteNumber)

		map = self.u.module.getEntryAttributesMap()
		footnote = map[footnotes][number]
		if n in footnote:
			footnote_char = footnote[n].c_str()
		else:
			if was_xref: footnote_char = "x"
			else: footnote_char = "n"

		refs_to_expand = None
		if expand_crossref:
			try:			
				refs_to_expand = footnote[refList].c_str()
			
			except IndexError:
				dprint(WARNING, "Error getting Footnote '%s' refList" % 
					footnoteNumber)

		if refs_to_expand:
			self.u.inXRefNote = True
			
			self.buf += filterutils.ellipsize(
				refs_to_expand.split(";"), 
				self.u.key.getText(),
				int(filterutils.filter_settings["footnote_ellipsis_level"])
			)
		else:
			c = "footnote footnote_%s" % type
			self.buf += "<a class=\"%s\" href=\"newbible://content/passagestudy.jsp?action=showNote&type=%c&value=%s&module=%s&passage=%s\">%s</a>" % (
								c,
								footnote_type,
								SW.URL.encode(footnoteNumber).c_str(), 
								SW.URL.encode(self.u.version.c_str()).c_str(), 
								SW.URL.encode(self.u.key.getText()).c_str(), 
								footnote_char
			)
		self.did_xref = True
		self.u.suspendLevel += 1
		self.u.suspendTextPassThru = self.u.suspendLevel
		
			
		

	def end_note(self, xmltag):
		if self.did_xref:
			self.u.inXRefNote = False
			self.u.suspendLevel -= 1
			self.u.suspendTextPassThru = self.u.suspendLevel
			self.did_xref = False
			
			return
		
			

		self.success = SW.INHERITED	
	
	def start_milestone(self, xmltag):
		if not xmltag.isEmpty():
			print "Can milestone's really be non-empty?"
	
		if xmltag.getAttribute("type") == "x-p":
			# m = attributes["marker"] (Pilcrow character in KJV)
			self.buf += "<!P>"
		else:
			self.success = SW.INHERITED	

	def start_p(self, xmltag):
		print "IN P"
		self.buf += "<p>"
		self.blocklevel_start()
		if xmltag.isEmpty(): 
			self.end_p(xmltag)

	def end_p(self, xmltag):
		self.blocklevel_end()
		self.buf += "</p>"
	
	def start_div(self, xmltag):
		if xmltag.getAttribute("type") != "paragraph":
			self.success = SW.INHERITED
		elif xmltag.getAttribute("eID"):
			self.blocklevel_end()
			self.buf += "</p>"
		elif xmltag.getAttribute("sID"):
			self.buf += "<p>"
			self.blocklevel_start()
		else:
			print "What is this paragraph div?", xmltag.toString()


		
	# TODO:
	# lg starting in previous chapter
	# verse numbers on x-indent lines
	# verse numbers (and footnotes) float lefter? (hard)
	# version comparison problems - kill these!

	def start_title(self, xmltag):
		canonical = xmltag.getAttribute("canonical")
		canonical = canonical or "false"
		self.buf += '<h2 class="heading" canonical="%s">' % canonical
	
	def end_title(self, xmltag):
		self.buf += '</h2>'

	def start_lg(self, xmltag):
		if xmltag and xmltag.getAttribute("eID"):
			return self.end_lg(xmltag)

		if self.in_lg:
			dprint(WARNING, "Nested lg's? (or l outside lg, then lg?)")

		self.in_lg = True
		clas = ""
		if not xmltag:
			clas = " forced_lg"

		if not self.in_copy_verses_mode:
			self.buf += '<blockquote class="lg" width="0">'
	
	def end_lg(self, xmltag):
		self.in_lg = False
		if not self.in_copy_verses_mode:
			self.buf += '</blockquote>'
	
	def write(self, text):
		if self.u.suspendTextPassThru:
			self.u.lastSuspendSegment.append(text)
		else:
			self.buf += text

	def start_divineName(self, xmltag):
		self.write("<span class='divineName'>")

	def end_divineName(self, xmltag):
		self.write("</span>")
	
		
	def start_l(self, xmltag):
		if xmltag.getAttribute("eID"):
			return self.end_l(xmltag)

		if xmltag.isEmpty() and not xmltag.getAttribute("sID"):
			print "<l />?!?", xmltag.toString()
			self.success = SW.INHERITED
			return

		if not self.in_lg:
			dprint(WARNING, "l outside lg??? (or block doesn't contain lg)")
			self.start_lg(None)
		
		mapping = {
			# usual poetry indent in ESV
			"x-indent": 2,

			# extra indent - 1 Tim 3:16 (ESV) for example
			"x-indent-2": 4,

			# declares lines - Declares the Lord, Says the Lord, etc.
			"x-declares": 6,
			
			# doxology - Amen and Amen - Psalms 41:13, 72:19, 89:52 in ESV 
			"x-psalm-doxology": 6,

			# usual poetry indent in WEB
			"x-secondary": 2,
		}

		level = xmltag.getAttribute("level")
		if level:
			# the level defaults to 1 - i.e. no indent
			indent = 2 * (int(level) - 1)
		else:
			indent = mapping.get(xmltag.getAttribute("type"), 0)

		#if indent:
		if self.in_indent:
			dprint(WARNING, "Nested indented l's", self.u.key.getText())

		self.in_indent = True
		if not self.in_copy_verses_mode:
			self.buf += '<div class="indentedline" width="%d" source="l">' % indent
		self.blocklevel_start()

	def end_l(self, xmltag):
		if self.in_indent:
			self.blocklevel_end()			
			self.buf += "<br>" if self.in_copy_verses_mode else "</div>"
			self.in_indent = False
			
		else:
			self.success = SW.INHERITED
	
	def start_figure(self, xmltag):
		src = xmltag.getAttribute("src")
		if not src:
			self.success = SW.FAILED
			return

		data_path = self.u.module.getConfigEntry("AbsoluteDataPath")
		img_path = os.path.realpath("%s/%s" % (data_path, src))
		self.buf += '<img border=0 src="%s" />' % img_path
			
	def start_seg(self, xmltag):
		type = xmltag.getAttribute("type")
		if type in ("morph", "x-morph"):
			self.buf += '<span class="morphSegmentation">'
			if self.in_morph_seg:
				dprint(WARNING, "Nested morph segs", self.u.key.getText())

			self.in_morph_seg = True
		else:
			self.success = SW.INHERITED

	
	def end_seg(self, xmltag):
		if self.in_morph_seg:
			self.buf += "</span>"
			self.in_morph_seg = False
			
		else:
			self.success = SW.INHERITED

	@property
	def in_copy_verses_mode(self):
		return (self.biblemgr.parser_mode == filterutils.COPY_VERSES_PARSER_MODE)
		
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

