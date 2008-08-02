import re

from backend.verse_template import VerseTemplate
from util.string_util import KillTags, ReplaceUnicode, replace_amp, htmlify_unicode, remove_amps
from util.debug import dprint, ERROR
from util.unicode import to_unicode

from search import removeformatting

from backend.bibleinterface import biblemgr
from gui.reference_display_frame import ReferenceDisplayFrame

tokens = re.compile(r"""
	(<glink[^>]*>.*?</glink>)	| # a strongs number and contents
	(<a\ [^>]*>.*?</a>)			| # a link and contents	
	(<h4>.*?</h4>)				| # a heading and contents	
	(<[^>]+>)					| # any other html tag - not contents
	(&(?P<amps>[^;]*);)			| # a html escape
	(.)							  # anything else
""", flags=re.DOTALL|re.VERBOSE|re.IGNORECASE)

not_word = re.compile(r"\W", flags=re.UNICODE)

OPENING_TAG = 0
CLOSING_TAG = 1
ZERO_WIDTH_TAG = 2

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

def tokenize(string):
	for item in tokens.finditer(string):
		text = item.group(0)
		if item.group('amps'):
			text = replace_amp(item)

		yield text

def unite(string1, string2):
	"""Unite string1 and string2.
	
	This maps each token in string1 into a sequence of tokens in string2."""
	iter1 = tokenize(string1)
	iter2 = tokenize(string2)

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
				result.append(list(iter2))
				return result
			
		else:
			# otherwise put it in the list associated with the last token from
			# string1
			result[-1].append(token2)

		# and get our next token from string2
		try:
			token2 = iter2.next()
		except StopIteration:
			dprint(ERROR, "Didn't match token in first string", token1,
				string1, string2)

			return []

def highlight(string1, string2, regexes, 
		start_tag='<b><font color="#008800">', end_tag='</font></b>'):
	"""Highlight string2 with the regular expressions regexes, being matched
	on string1

	string1 should be text processed through striptext
	string2 should be the same text, but with extra rendering niceties
	start_tag and end_tag give the tags for the start and end of highlighting
	"""
	results = unite(string1, string2)
	
	# if we couldn't process it, return string2 intact
	if not results:
		return string2
	
	for regex in regexes:
		matched = False
		for match in regex.finditer(string1):
			matched = True
			start, end = match.span()
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
		
		if not matched:
			dprint(ERROR, "Regular expression not matched against plain text",
				regex.pattern, string1)
	
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
		super(HighlightedDisplayFrame, self).__init__()

	def _RefreshUI(self):
		if not self.reference:
			self.SetPage("")
			return

		data = biblemgr.bible.GetReference(self.reference)

		mod = biblemgr.bible.mod
		#mod.KeyText(self.reference)

		# TODO: put a function in search to do this for us...
		biblemgr.temporary_state(biblemgr.plainstate)
		template = VerseTemplate("$text ", headings="")
		biblemgr.bible.templatelist.append(template)
		
		
		content = biblemgr.bible.GetReference(self.reference, stripped=True)
		biblemgr.restore_state()
		biblemgr.bible.templatelist.pop()

		content = remove_amps(KillTags(ReplaceUnicode(content)))
		content = content.replace("\n", " ")
		content = removeformatting(content)

		data = highlight(content, data, self.regexes)
		
		# XXX: This replace should be done for us by the backend Bible
		# interface (or by Sword itself).
		data = data.replace("<!P>","</p><p>")
		#if not wx.USE_UNICODE:
		#	#replace common values
		#	data = ReplaceUnicode(data)
		self.SetPage("%s" % data)		

if __name__ == '__main__':
	string1 = u"abcd TE ST\u03b6"
	string2 = u"a<b>b</b>c&#8220;d TE.ST&#950;."
	match1 = 2, 4

	items = unite(string1, string2)
	assert len(items) == len(string1) + 2

	print "Before", items[0]
	for string_part, item in zip(string1, items[1:-1]):
		print string_part, item

	print "After", items[-1]
	print highlight(string1, string2, [re.compile("b.*T"), re.compile("b.*T")])

