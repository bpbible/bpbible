ur"""
Parse search expressions

The simplest search string is just a word. This has \b's put around it so that
it makes a full match on a word
>>> print_regexes("test")
\btest\b

Unicode should be supported: (this is 'abba in greek - note the ' gets dropped)
>>> d=parse(u"\u1fbd\u0391\u03b2\u03b2\u03ac")
>>> d.items[0].to_regex() == u"\\b\u0391\u03b2\u03b2\u03ac\\b"
True

Phrases are almost the same, but have quotes around them. All spaces inside
are replaced by \s, so that they can match over verse boundaries
>>> print_regexes('"test ing"')
\btest\sing\b

Multiple words can also make up a search. Each is treated individually
>>> print_regexes('test ing')
\btest\b
\bing\b

Regular expressions are also allowed, delimited by /regex/
\ will escape / and \, but nothing else
>>> print_regexes(r'/test ing\/\\\a/')
test ing/\\a

Components of a search can also be excluded by placing a leading dash:
>>> print_regexes('-"ignore me"')
Excluded: \bignore\sme\b

Field search support looks like this:
>>> query = parse('strongs:G3550')
>>> query.get_field_values()
('strongs', 'G3550')

Fields can have dashes and colons in (unlike usual words)
>>> query = parse('ref:Gen3:15-Gen3:19')
>>> query.get_field_values()
('ref', 'Gen3:15-Gen3:19')

They can also have spaces in if they have quotes around them:
>>> query = parse('ref:"Genesis 3:15 - Genesis 3:19"')
>>> query.get_field_values()
('ref', 'Genesis 3:15 - Genesis 3:19')


Groups provide alternatives:
>>> print_regexes('(LORD, GOD) good')
(\bLORD\b|\bGOD\b)
\bgood\b
>>> print_regexes('(LORD,GOD) good')
(\bLORD\b|\bGOD\b)
\bgood\b

But if it isn't in a group, a comma should be ignored
>>> print_regexes('LORD, GOD')
\bLORD\b
\bGOD\b

So should a greek accent:
>>> d=parse(u'\u03b2\u03c5\u03c3\u03c3\u03bf\u0301\u03c2')
>>> len(d.items)
1
>>> d.items[0].to_regex() == u'\\b\u03b2\u03c5\u03c3\u03c3\u03bf\u03c2\\b'
True

As should hindi vowels (at the moment)
>>> d=parse(u'\u0921\u093e\u0932\u0942\u0902\u0917\u093e\u0964')
>>> len(d.items)
1
>>> d.items[0].to_regex() == u'\\b\u0921\u0932\u0917\\b'
True

There are a few special cases with punctuation
Dashes in words are ignored
>>> print_regexes('Beth-Hachilah')
\bBethHachilah\b

As are commas in the middle of numbers
>>> print_regexes('123,456')
\b123456\b

And apostrophes in the middle of words
>>> print_regexes("don't")
\bdont\b

However, em dashes are word separators, so we treate them as such
>>> print_regexes(u'that\N{EM DASH}this')
\bthat\b
\bthis\b

Wildcards are allowed.
Star is for 0 or more characters
>>> print_regexes("*ites")
\b\w*ites\b

Plus is for 1 or more characters
>>> print_regexes("foot+")
\bfoot\w+\b

However, plus at the start means to match exactly - no stemming
>>> print_regexes("+good")
\bgood\b

Question mark is for a single character
>>> print_regexes("b?ll")
\bb\wll\b

Also, groups of characters can be specified
>>> print_regexes("b[aei]ll")
\bb[aei]ll\b
>>> print_regexes("b[^a-ie]ll")
\bb[^a-ie]ll\b

Special cases worth testing:
>>> print_regexes("-test, ing")
Excluded: \btest\b
\bing\b

>>> print_regexes('  leading . ~" and ! trailing "~ ? stuff! ')
\bleading\b
\band\strailing\b
\b\w\b
\bstuff\b

>>> print_regexes('test-\x15-\x12ing\x15 "\x15 test-ing-- This is a\x15"')
\btesting\b
\btesting\sThis\sis\sa\b


Error cases. These probably should work, but can fail for now.
>>> print_regexes("(test, ing") # doctest: +SKIP
(\btest\b|\bing\b)
>>> print_regexes('"test ing') # doctest: +SKIP
\btest\sing\b
"""
import re

# make sure contrib is imported for ply
import contrib
import ply.lex as lex
import util

import string

class SpellingException(Exception):
	def __init__(self, wordlist):
		self.wrongwords=wordlist

	def __str__(self):
		return ", ".join(self.wrongwords)


# pre compile our regular expressions
re_list = (
	"(?<=\d),(?=\d)", 
	"(?<=\w)'(?=\w)",
	"(?<=\w)-(?=\w)", 
	" +", 
	r"\s+", 
	u"[^\\w\s\uFDD0-\uFDEF]",
	"(?<!\d),",
	",(?!\d)",
	"(?<!\w)'",
	"'(?!\w)",
	"(?<!\w)-",
	"-(?!\w)",
	',\s*'	
)
r = {}
for a in re_list:
	r[a] = re.compile(a, flags=re.UNICODE)

l = "(?<=\d),(?=\d)|(?<=\w)'(?=\w)|(?<=\w)-(?=\w)"

r["l"]=re.compile(l, flags=re.UNICODE)
r["p"]=re.compile("[%s]" % re.escape(
	string.punctuation + 
	u'\N{RIGHT DOUBLE QUOTATION MARK}' 
	u'\N{LEFT DOUBLE QUOTATION MARK}'
	u'\N{EM DASH}'
	u'\N{RIGHT SINGLE QUOTATION MARK}'
	u'\N{LEFT SINGLE QUOTATION MARK}'
	
), flags=re.UNICODE)
r["punctuation_2"]=re.compile("[%s]" % re.escape(
	''.join(x for x in string.punctuation if x not in "',-")
), flags=re.UNICODE)

def removeformatting(mystr):
	# remove commas in numbers
	# Example "123,456" -> "123456"
	#TODO: some locales may have 2.345.345 instead of 2,345,345
	#mystr = r["(?<=\d),(?=\d)"].sub("", mystr)
	
	# remove apostrophes in words
	#mystr = r["(?<=\w)'(?=\w)"].sub("", mystr)

	#remove hyphenation
	#mystr = r["(?<=\w)-(?=\w)"].sub("", mystr)

	mystr = r["l"].sub(u"", mystr)
	
	#TODO: replace symbols with nothing?
	#for a in string.punctuation:
	mystr = r["p"].sub(u" ", mystr)
	mystr = r[u"[^\\w\s\uFDD0-\uFDEF]"].sub(u"", mystr)
	mystr = r["\\s+"].sub(u" ", mystr)
	mystr = mystr.strip()
	return mystr

def removeformatting2(mystr):
	"""Remove some formatting, but leave enough data in place to display an
	intelligent output to user with spell checking."""
	ret = mystr
	#TODO: replace symbols with nothing?
	ret = r["(?<!\d),"].sub(u" ", ret)
	ret = r[",(?!\d)"].sub(u" ", ret)
	
	# remove apostrophes not in words
	ret = r["(?<!\w)'"].sub(u" ", ret)
	ret = r["'(?!\w)"].sub(u" ", ret)

	#don't remove hyphenation, but all other dashes
	ret = r["(?<!\w)-"].sub(u" ", ret)
	ret = r["-(?!\w)"].sub(u" ", ret)
	
	ret = r["punctuation_2"].sub(u" ", ret)
	ret = r[" +"].sub(u" ", ret)
	ret = ret.strip()
	return ret


# the parser proper
def indent(item, level=4):
	return re.sub("(?m)^", u" " * level, item)


class GroupOfObjects(object):
	def __init__(self, *args):
		self.items = []
		self.items.extend(args)

	def __add__(self, base):
		self.items.append(base)
		return self
	
	def __repr__(self):
		str = "<%s object at 0x%x\n  Items:\n" % (type(self).__name__, id(self))
		str += '\n'.join(indent(repr(item)) for item in self.items)
		return str + "\n>"
	
	def item_to_regex(self, item):
		if isinstance(item, basestring):
			return item

		return item.to_regex()

	def iter_children(self):
		yield self
		for item in self.items:
			if isinstance(item, basestring):
				yield item
			else:
				for child in item.iter_children():
					yield child

	def to_regex(self):
		return ''.join(self.item_to_regex(item) for item in self.items)
		
	def is_excluded(self):
		return any(not isinstance(item, basestring) and item.is_excluded() 
					for item in self.items)

	def is_field(self):
		return any(not isinstance(item, basestring) and item.is_field() 
					for item in self.items)

	def get_field_values(self):
		assert self.is_field(), "Trying to get field values for non-field"
		fields = [item for item in self.items 
			if not isinstance(item, basestring) and item.is_field()]

		assert len(fields) == 1, "Too many fields"

		return fields[0].get_field_values()

class Query(GroupOfObjects): pass
class MultiQuery(GroupOfObjects): pass


class Exclusion(GroupOfObjects):
	def is_excluded(self):
		return True

class Inclusion(GroupOfObjects): pass
		

cross_verse = True

class WordsWithDashWords(GroupOfObjects): 
	def to_regex(self):
		return " ".join(self.item_to_regex(item) for item in self.items)


class Words(GroupOfObjects): 
	def to_regex(self):
		delimiter = r"\s"

		# if we are not doing a cross-verse search, don't match a phrase
		# across a verse - so use a space.
		if not cross_verse:
			delimiter = " "

		return delimiter.join(self.item_to_regex(item) for item in self.items)

class Option(GroupOfObjects): 
	def to_regex(self):
		return "(%s)" % '|'.join(
			self.item_to_regex(item) for item in self.items
		)

class Word(GroupOfObjects): pass
class Regex(GroupOfObjects): pass
class Phrase(GroupOfObjects): 
	def to_regex(self, ):
		assert len(self.items) == 1
		return r"\b%s\b" % self.item_to_regex(self.items[0])

class SingleWord(Phrase): pass

class WildCard(GroupOfObjects): 
	def to_regex(self):
		if self.items[0] == "?":
			return "\w"
		
		return "\w" + self.items[0]
		
class Field(GroupOfObjects):
	def to_regex(self):
		print "Field: key: %s value: %s" % (
			''.join(self.items[0].items), 
			self.item_to_regex(self.items[1])
		)
		return "<No REGEX>"

	def is_field(self):
		return True
	
	def get_field_values(self):
		"""Return key, value pair for this field"""
		return ''.join(self.items[0].items), self.item_to_regex(self.items[1])
		

tokens = (
	'STAR', 'PLUS', 'QUESTION_MARK', 'GROUP', 'LETTER',
	'MINUS', 'QUOTE', 'REGEX', 'LPAREN', 'RPAREN', 
	'FIELD', 
	'WS', 'OTHER', 'INPLACE_PUNCTUATION', 'PUNCTUATION', 'COMMA_WS', 
	)

states = (
   ('brackets','inclusive'),
)


# Tokens
def t_REGEX(t):
	r'/((?:\\.|[^/\\])+)/'
	def replace(match):
		if match.group(1) in r'\/':
			return match.group(1)

		return match.group()

	t.value = Regex(re.sub(r'\\(.)', replace, t.value[1:-1]))
	return t

def t_QUOTE(t):
	'"'
	return t

def t_MINUS(t):
	r'-'
	return t

def t_LPAREN(t):
	r'\('
	t.lexer.push_state('brackets')
	return t

def t_brackets_RPAREN(t):
	r'\)'
	t.lexer.pop_state() # Back to the previous state
	return t

def t_PLUS(t):
	r'\+'
	return t

def t_STAR(t):
	r'\*'
	return t

def t_QUESTION_MARK(t):
	r'\?'
	return t

def t_GROUP(t):
	r"\[[\w\-^]+\]"
	return t

def t_LETTER(t):
	r'\w'
	return t

def t_WS(t):
	r"\s+"
	return t

def t_FIELD(t):
	r':'
	return t

def t_INPLACE_PUNCTUATION(t):
	r"(?<=\d),(?=\d)|(?<=\w)'(?=\w)|(?<=\w)-(?=\w)"
	return t

def t_brackets_COMMA_WS(t):
	r',\s*'
	return t

@lex.TOKEN("(?u)[%s]" % re.escape(
	string.punctuation + 
	u'\N{RIGHT DOUBLE QUOTATION MARK}' 
	u'\N{LEFT DOUBLE QUOTATION MARK}'
	u'\N{EM DASH}'
	u'\N{RIGHT SINGLE QUOTATION MARK}'
	u'\N{LEFT SINGLE QUOTATION MARK}'
	
))
def t_PUNCTUATION(t):
	return t

def t_OTHER(t):
	r'.'
	return t

def t_error(t):
	print "Illegal character '%s'" % t.value[0]
	t.lexer.skip(1)
	
# Build the lexer
lex.lex(optimize=True,
	reflags=re.UNICODE)
	


def p_multi_query(p):
	'''multi_query : multi_query separators query'''
	p[1].items += p[3].items
	p[0] = p[1]

def p_empty_multi_query(p):
	'''multi_query : separators'''

def p_multi_query_leading_junk(p):
	'''multi_query : separators multi_query'''
	p[0] = p[2]

def p_junk_multi_trailing_junk(p):
	'''multi_query : multi_query separators'''
	p[0] = p[1]

def p_multi_query_single(p):
	'''multi_query : query'''
	p[0] = p[1]

def p_query(p):
	'''query : query_part'''
	p[0] = Query(p[-1])

def p_exclusion(p):
	'''exclusion : MINUS query_part'''
	p[0] = Exclusion(p[2])

def p_inclusion(p):
	'''inclusion : PLUS query_part'''
	p[0] = Inclusion(p[2])
	

def p_query_part_without_option_phrase(p):
	'''query_part_without_option : phrase'''
	p[0] = Phrase(p[1])

def p_query_part_without_option_word(p):
	'''query_part_without_option : word'''
	p[0] = SingleWord(p[1])
	

def p_query_part_regex_field_without_option(p):
	'''query_part_without_option : REGEX
								 | field'''
	p[0] = p[1]

def p_query_part(p):
	'''query_part : LPAREN option RPAREN
				  | query_part_without_option
				  | exclusion
				  | inclusion'''
	if len(p) == 2:
		p[0] = p[1]
	else:
		p[0] = p[2]

#def p_query_part_option(p):
#	'''query : option'''
#	# this allows commas between words
#	p[0] = Query(p[1])

def p_field(p):
	'''field : word FIELD word-with-dash
			 | word FIELD phrase-with-dash'''
	p[0] = Field(p[1], p[3])

def p_word_with_dash_dash(p):
	'''word-with-dash : word MINUS word-with-dash
					  | word FIELD word-with-dash'''
	p[0] = p[1]
	p[1].items += [p[2]] + p[3].items

def p_word_with_dash(p):
	'''word-with-dash : word'''
	p[0] = p[1]

def p_word_with_dash_as_dash(p):
	'''word-with-dash : MINUS
					  | FIELD'''
	p[0] = p[1]
	
	

def p_word_and_item(p):
	'''word : word word_item'''
	p[0] = p[1] + p[2]

#def p_word_other(p):
#	'''word : word inplace_item word_item'''
#	p[0] = p[1] + p[-1]

def p_word_trailing_item(p):
	'''word : word inplace_item'''
	p[0] = p[1]

def p_inplace_item(p):
	'''inplace_item : OTHER
					| INPLACE_PUNCTUATION
					| MINUS
					| inplace_item OTHER
					| inplace_item INPLACE_PUNCTUATION
					| inplace_item MINUS
	'''

def p_word(p):
	'''word : word_item'''
	p[0] = Word(p[1])

def p_option_parts(p):
	'''option : option COMMA_WS query_part_without_option'''
	p[0] = p[1] + p[-1]

def p_option_part(p):
	'''option : query_part_without_option'''
	p[0] = Option(p[1])

def p_phrase(p):
	'''phrase : QUOTE words QUOTE'''
	p[0] = p[2]

def p_phrase_width_dash(p):
	'''phrase-with-dash : QUOTE words-with-dash QUOTE'''
	p[0] = (p[2])

def p_words(p):
	'''words : words separators word'''
	p[0] = p[1] + p[3]

def p_words_as_word(p):
	'''words : word'''
	p[0] = Words(p[1])

def p_words_leading_junk(p):
	'''words : separators words'''
	p[0] = p[2]

def p_words_trailing_junk(p):
	'''words : words separators'''
	p[0] = p[1]	

def p_words_with_dash(p):
	'''words-with-dash : words-with-dash separators word-with-dash'''
	p[0] = p[1] + p[3]

def p_words_with_dash_as_word(p):
	'''words-with-dash : word-with-dash'''
	p[0] = WordsWithDashWords(p[1])

def p_words_with_dash_leading_junk(p):
	'''words-with-dash : separators words-with-dash'''
	p[0] = p[2]

def p_words_with_dash_trailing_junk(p):
	'''words-with-dash : words-with-dash separators'''
	p[0] = p[1]	

def p_wildcard(p):
	'''word_item : STAR
				 | PLUS
				 | QUESTION_MARK'''
	
	p[0] = WildCard(p[1])

def p_word_item(p):
	'''word_item : GROUP
				 | LETTER'''
	p[0] = p[1]

def p_separators(p):
	'''separators : separator
				  | separator separators'''

def p_separator(p):
	'''separator : WS
				 | PUNCTUATION
				 | OTHER'''

class ParseError(Exception):
	def __init__(self, string1, len):
		self.string1 = string1
		self.len = len

	def __str__(self):
		return u"""\
%s ``
%s
%*s^``""" % (_("Could not understand string"), self.string1, self.len, "")

def p_error(t):
	if t is None: 
		print "Unexpected end of file"
		return
	print "ERROR", t, dir(t)
	print t.lexpos
	raise ParseError(current_string, t.lexpos)
	raise SyntaxError("Syntax error at '%s'" % t.value)
	
def parse(string):
	global current_string
	current_string = string
	return yacc.parse(current_string)

def print_regexes(string, verbose=False):
	result = parse(string)
	if verbose: print result
	if result:
		for item in result.items:
			if item.is_excluded():
				print "Excluded:",
			print item.to_regex()

def separate_words(string, wordlist=None, stemming_data=None, stemmer=None,
		cross_verse_search=True):
	global cross_verse
	cross_verse = cross_verse_search

	result = parse(string)
	if not result: 
		return ([], []), ([], [])
	

	def get_whole_word(item):
		if isinstance(item, SingleWord):
			c = item.items[0]
		
			for child in c.items:
				if not isinstance(child, basestring):
					return None

			return ''.join(c.items)

		return None
	

	def check_proper_word(item):
		had_non_letter = False
	
		for child in item.items:
			if not isinstance(child, (basestring, Field)):
				had_non_letter = True
				for badword in check_proper_word(child):
					yield badword
		
		if not had_non_letter and isinstance(item, Word):
			word = ''.join(item.items)
			if wordlist is not None and word.lower() not in wordlist:
				yield word

	badwords = list(check_proper_word(result))
	if badwords:
		raise SpellingException(badwords)	
	
	regexes = [], []
	fields = [], []
	for item in result.items:
		if item.is_field():
			fields[item.is_excluded()].append(item.get_field_values())
		else:
			# Don't stem for wildcards or phrases or regexes,
			# or for excluded words
			word = get_whole_word(item)
			if word is None or item.is_excluded() or stemmer is None:
				regexes[item.is_excluded()].append(item.to_regex())
			else:
				regexes[item.is_excluded()].append(r"\b%s\b" %
					stemmer.compose_regex(stemming_data, word)
				)

	return regexes, fields
		

if util.is_py2exe():
	# explicitly note the dependency
	import parsetab
	import lextab

import ply.yacc as yacc
import config
yacc.yacc(optimize=config.is_release())

def _test():
	import doctest as d
	return d.testmod()[0]


if __name__ == '__main__':
	import sys
	if "interactive" not in sys.argv:
		sys.exit(_test())
	
	while 1:
		try:
			s = raw_input('calc > ')
		except EOFError:
			print
			break
		print_regexes(s, True)	
