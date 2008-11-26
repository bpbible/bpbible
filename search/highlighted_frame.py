import re
import unicodedata

import wx
from backend.verse_template import VerseTemplate
from backend.book import Bible
from util.string_util import KillTags, ReplaceUnicode, replace_amp, htmlify_unicode, remove_amps
from util.debug import dprint, ERROR, WARNING

from search import removeformatting

from backend.bibleinterface import biblemgr
from gui.reference_display_frame import ReferenceDisplayFrame
from swlib.pysw import SW, VerseList

#TODO: highlight Aenon - AE joined up, that is - in KJV

regex = r"""
	(<glink[^>]*>.*?</glink>)		 | # a strongs number and contents
	(&lt;<a\ [^>]*>.*?</a>&gt;) 	 | # a link with <> around and contents		
	(<a\ href="genbook:[^>]+>.*?</a>)| # a genbook link 
	
	%s								   # if we are in a bible, exclude text
									   # from cross-reference links
	(<a\ href="passagestudy.jsp\?(
		(action=showRef[^>]*>)  	 | # a reference - don't include text
		([^>]*>.*?</a>) 		 	   # or another sword link and contents	
	))								 |
	(\(<a\ href="passagestudy.jsp\?
		action=showMorph 			   # a morph link and text with brackets
		([^>]*>.*?</a>) 		 	   
	\)) 							 |
	
	(<h6\ class="heading"\ 
		canonical="false">.*?</h6>)	 | # a heading (not canonical) and contents
	(<[^>]+>)						 | # any other html tag - not contents
	(&(?P<amps>[^;]*);)				 | # a html escape
	(.)							  	   # anything else
""" 

tokens = [
	re.compile(regex % item, flags=re.DOTALL|re.VERBOSE|re.IGNORECASE)
		for item in (
			'',
			'(<a\ href="bible:[^>]+>.*?</a>)	| # a bible link from xrefs', 
	)]
	
not_word = re.compile(r"\W", flags=re.UNICODE)

OPENING_TAG = 0
CLOSING_TAG = 1
ZERO_WIDTH_TAG = 2

def is_mark(char):
	if len(char) > 1:
		return False
	
	return unicodedata.category(char).startswith("M")

def get_tag(text):
	if text.startswith("<") and text.endswith(">"):
		text = text.strip("<>")
		tag = text.split(" ")[0].strip("/")
		type = OPENING_TAG
		if text.endswith("/"):
			type = ZERO_WIDTH_TAG
		elif text.startswith("/"):
			type = CLOSING_TAG
		
		return tag, type
	
	return None, -1

def tokenize(string, is_bible):
	for item in tokens[is_bible].finditer(string):
		text = item.group(0)
		if item.group('amps'):
			text = replace_amp(item)

		yield text

def unite(string1, string2, is_bible):
	"""Unite string1 and string2.
	
	This maps each token in string1 into a sequence of tokens in string2."""
	assert isinstance(string1, unicode) and isinstance(string2, unicode), \
		"%r %r %r %r" % (string1, string2, type(string1), type(string2))
	iter1 = tokenize(string1, is_bible)
	iter2 = tokenize(string2, is_bible)

	# the empty list is the before section
	result = [[]]

	# get our first two tokens
	try:
		token1 = iter1.next()
		token2 = iter2.next()
	except StopIteration:
		dprint(ERROR, "Couldn't get first tokens")
		return []
		
	
	# this loop is guaranteed to stop as we are taking a token from token2
	# each time.
	while True:
		# if the match is the same, or if it is a space instead of a
		# non-alphanumeric character, we take it
		
		# TODO: get rid of .lower below
		# This is in here because NASB's divineName tag doesn't get put to
		# uppercase properly as it contains a lemma.
		if token1.lower() == token2.lower() \
			or (token1 == " " and not_word.match(token2)):
			# put it as a new item on our list of results
			result.append([token2])
			
			# get our next token from string1
			try:
				token1 = iter1.next()
			except StopIteration:
				# if we have run out of tokens, add on all the rest of the 
				# tokens from the other string at the end
				
				# put diacritics on the last token
				l = list(iter2)
				while l and is_mark(l[0]):
					result[-1].append(l.pop(0))

				# and the rest on the end
				result.append(l)
				
				return result
			
		else:
			# otherwise put it in the list associated with the last token from
			# string1
			
			# an ending diactric should get put with the previous token,
			# however, as it has been replaced by a space, we have put it in
			# as representing a space. If we come across another separator, 
			# stick the diacritic onto the previous one
			if (len(result) > 2
				and len(result[-1]) == 1
				and is_mark(result[-1][0])):
				result[-2].append(result[-1][0])
				result[-1] = []
			
			result[-1].append(token2)
				

		# and get our next token from string2
		try:
			token2 = iter2.next()
		except StopIteration:
			dprint(ERROR, "Didn't match token in first string", token1,
				string1, string2, list(iter1))
			global s1, s2
			s1 = string1
			s2 = string2

			return []

def highlight_section(results, start, end, start_tag, end_tag):
	# +1 as we have preamble at start.
	results[start + 1].insert(0, start_tag)
	tags_open = []
	upto = start + 1

	pos = 1

	# go between our start and our end
	# this loop will find all the tags that are open by the end of the
	# match, and also find all the tags that are closed before the end
	# and close the highlighting just before and start it just after
	# the closed tag
	while upto <= end:
		# go through all the items for the current position
		while pos < len(results[upto]):
			tag, type = get_tag(results[upto][pos])

			# if it wasn't a tag, go to the next position
			if not tag:
				pos += 1
				continue
			
			# append opening tags to our stack
			if type == OPENING_TAG:
				tags_open.append((tag, results[upto][pos], upto, pos))

			elif type == CLOSING_TAG:
				while tags_open:
					# pop off tags until we match
					# We may be popping off tags without a matching
					# closing tag
					popped_tag, text, oldupto, oldpos = tags_open.pop()
					if popped_tag == tag:
						break
				
				# if we didn't find the tag, put in our end tag, the
				# closing tag, and then our start tag
				else:
					results[upto][pos:pos+1] = [
						end_tag,
						results[upto][pos],
						start_tag
					]

					# update the position to include the two new
					# entries
					pos += 2
					
			# go to the next position
			pos += 1
					
		upto += 1
		pos = 0
							
	# put the end tag in
	results[end].append(end_tag)
	
	last_upto = -1
	offset = 0

	while tags_open:
		# and finish off our tags open
		# this we do by finding the open tags and closing just before
		# them, and then opening just after them
		tag, text, upto, pos = tags_open.pop()

		if upto == last_upto:
			pos += offset
		else:
			offset = 0

		# close just before the first tag open that isn't closed		
		results[upto][pos:pos+1] = [
			end_tag,
			results[upto][pos],
			start_tag
		]

		# two new tags added in
		offset += 2

		last_upto = upto
		

def highlight(string1, string2, is_bible, regexes, fields=(),
		start_tag='<a href="#highlight" name="highlight"></a>'
		'<b><font color="#008800">', 
		end_tag='</font></b>'):
	"""Highlight string2 with the regular expressions regexes, being matched
	on string1

	string1 should be text processed through striptext
	string2 should be the same text, but with extra rendering niceties
	start_tag and end_tag give the tags for the start and end of highlighting
	"""
	results = unite(string1, string2, is_bible)
	
	# if we couldn't process it, return string2 intact
	if not results:
		return string2
	
	for regex in regexes:
		matched = False
		for match in regex.finditer(string1):
			matched = True
			start, end = match.span()
			highlight_section(results, start, end, start_tag, end_tag)

		if not matched:
			dprint(ERROR, "Regular expression not matched against plain text",
				regex.pattern, string1)
	
	for key, value in fields:
		if key == "strongs":
			match = re.match("([GH])(\d+)(\w?)", value)
			assert match, "couldn't interpret strong's number for highlighting"
			prefix, number, extra = match.group(1, 2, 3)
			lang = ["Hebrew", "Greek"][prefix=="G"]
			number = str(int(number))
			if extra:
				number += "!%s" % extra

			href = r"passagestudy.jsp\?action=showStrongs&type=%s" \
				"&value=0*%s(?:!\w)?"	% (lang, number)
			glink_matcher = re.compile(
				'^<glink([^>]*)(href="%s")([^>]*)>([^<]*)</glink>$' % href
			)
			strongs_matcher = re.compile(
				'^(&lt;<a [^>]*href="%s"[^>]*>)([^<]*)(</a>&gt;)$' % href
			)

			for tokens in results:
				for idx, token in enumerate(tokens):
					# highlight strong's numbers...
					# TODO: scroll to these?
					token = glink_matcher.sub(
						r'<b><glink colour="#008800"\1\2\3>\4</glink></b>',
						token)

					tokens[idx] = strongs_matcher.sub(
						r'<b><font color="#008800">\1<font color="#008800">\2</font>\3</font></b>',
						token)

		elif key == "morph":
			parts = value.split(":", 1)
			if len(parts) != 2:
				dprint(WARNING, "Not two parts in split. Skipping")
				continue

			k, v = parts
			if k == "Robinson":
				k = "(?:Robinson|Greek)"

			v = SW.URL.encode(str(v)).c_str()

			d = r'^(\(<a href="passagestudy.jsp\?action=showMorph&type=%s[^&]*&value=%s">)([^<]*)(</a>\))$' % (k, v)			

			count = 0
			morph_matcher = re.compile(d)
			for tokens in results:
				for idx, token in enumerate(tokens):
					tokens[idx], c = morph_matcher.subn(
						r'<b><font color="#008800">\1<font color="#008800">\2</font>\3</font></b>',
						token
					)
					count += c

			if count == 0:
				dprint(WARNING, "Didn't highlight morph - are they on?", value)

		elif key == "ref":
			if is_bible:
				ref = re.compile(
					r'^(<a href="bible:([^#]*)(#.*)?">)(.*?)(</a>)$'
				)
			else:
				# if we aren't in the bible, the start and end will be in
				# different tokens. So match start and then end
				ref = re.compile(
					r'^(<a href="bible:([^#]*)(#.*)?">)|(</a>)$'
				)

			v = VerseList(value, userInput=True)
			in_ref = [False]
			def subst(match):
				if (is_bible or match.group(1)):
					if match.group(2).startswith("%3F"):
						url = SW.URL("bible:" +
						SW.URL.decode(str(match.group(2))).c_str())
						values = url.getParameterValue("values")
						references = VerseList([
							url.getParameterValue("val%s" % value)
							for value in range(int(values))
						])
					else:
						references = VerseList(match.group(2))
				else:
					# our closing </a>?
					if not is_bible and in_ref[0] and match.group(4):
						in_ref[0] = False
						return "</font></b>%s" % match.group(4)

					return match.group(0)

				for item in v:
					for i in item:
						if references.VerseInRange(i):
							if is_bible:
								# wrap the contents of the <a> in formatting
								return '%s<b><font color="#008800">%s</font></b>%s' % match.group(1, 4, 5)
							else:
								# start the formatting, to be completed with
								# the </a> tag handling above
								in_ref[0] = True
								return '%s<b><font color="#008800">' % \
									match.group(1)

				return match.group(0)

			for tokens in results:
				for idx, token in enumerate(tokens):
					tokens[idx] = ref.sub(subst, token)
	
	replacements = {
		'<' : '&lt;',
		'>' : '&gt;',
		'&' : '&amp;'
	}

	for x in results:
		for idx, y in enumerate(x):
			# don't let <, > or & by themselves go straight through, as they
			# will have been translated from &lt;, ...
			if y in ('<', '>', '&'):
				x[idx]  = replacements[y]

	return htmlify_unicode(''.join(''.join(x) for x in results))
	
class HighlightedDisplayFrame(ReferenceDisplayFrame):
	def __init__(self):
		self.regexes = []
		self.fields = []
		self.parent = None
		super(HighlightedDisplayFrame, self).__init__()

	@property
	def book(self):
		assert self.parent, "HighlightedDisplayFrame without parent..."
		return self.parent.book

	def _RefreshUI(self):
		if not self.reference:
			self.SetPage("")
			return
		
		ref_parts = self.reference.split(" - ")
		reference = ref_parts.pop(0)
		end_reference = None
		if ref_parts:
			end_reference = ref_parts[0]

		if self.parent.template:
			self.parent.book.templatelist.append(self.parent.template)

		data = self.parent.book.GetReference(
			reference,
			end_ref=end_reference)

		if self.parent.template:
			self.parent.book.templatelist.pop()

		# TODO: put a function in search to do this for us...
		biblemgr.temporary_state(biblemgr.plainstate)
		template = VerseTemplate(u"$text ")#, headings=u"")
		self.parent.book.templatelist.append(template)
		
		
		content = self.parent.book.GetReference(reference, stripped=True,
				end_ref=end_reference)
		biblemgr.restore_state()
		self.parent.book.templatelist.pop()

		#TODO: highlight with \n's properly
		# e.g. /word\nanother/

		# remove non-canonical headings
		content = re.sub('(<h6 class="heading" canonical="false">.*?</h6>)',
						 '', content)	

		content = remove_amps(KillTags(ReplaceUnicode(content)))
		content = content.replace("\n", " ")
		content = removeformatting(content)

		data = highlight(content, data,
			is_bible=self.parent.book.mod.Type() == Bible.type,
			regexes=self.regexes, fields=self.fields,
			)
		
		# XXX: This replace should be done for us by the backend Bible
		# interface (or by Sword itself).
		data = data.replace("<!P>","</p><p>")
		#if not wx.USE_UNICODE:
		#	#replace common values
		#	data = ReplaceUnicode(data)
		self.SetPage("%s" % data)
		
		# don't give error if this doesn't work
		d = wx.LogNull()
		self.ScrollToAnchor("highlight")
		self.ScrollLines(-1)

if __name__ == '__main__':
	string1 = u"abcd TE ST\u03b6"
	string2 = u"a<b>b</b>c&#8220;d TE.ST&#950;."
	match1 = 2, 4

	items = unite(string1, string2, True)
	assert len(items) == len(string1) + 2

	print "Before", items[0]
	for string_part, item in zip(string1, items[1:-1]):
		print string_part, item

	print "After", items[-1]
	print highlight(string1, string2, [re.compile("b.*T"), re.compile("b.*T")])

