import re
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
	ret = mystr

	# remove commas in numbers
	# Example "123,456" -> "123456"
	#TODO: some locales may have 2.345.345 instead of 2,345,345
	#ret = r["(?<=\d),(?=\d)"].sub("", ret)
	
	# remove apostrophes in words
	#ret = r["(?<=\w)'(?=\w)"].sub("", ret)

	#remove hyphenation
	#ret = r["(?<=\w)-(?=\w)"].sub("", ret)

	ret = r["l"].sub("", ret)
	
	#TODO: replace symbols with nothing?
	#for a in string.punctuation:
	ret = r["p"].sub(" ", ret)
	ret = r[u"[^\\w\s\uFDD0-\uFDEF]"].sub("", ret)
	ret = r["\\s+"].sub(" ", ret)
	ret = ret.strip()
	return ret

def removeformatting2(mystr):
	"""Remove some formatting, but leave enough data in place to display an
	intelligent output to user with spell checking."""
	ret = mystr
	#TODO: replace symbols with nothing?
	ret = r["(?<!\d),"].sub(" ", ret)
	ret = r[",(?!\d)"].sub(" ", ret)
	
	# remove apostrophes not in words
	ret = r["(?<!\w)'"].sub(" ", ret)
	ret = r["'(?!\w)"].sub(" ", ret)

	#don't remove hyphenation, but all other dashes
	ret = r["(?<!\w)-"].sub(" ", ret)
	ret = r["-(?!\w)"].sub(" ", ret)
	
	ret = r["punctuation_2"].sub(" ", ret)
	ret = r[" +"].sub(" ", ret)
	ret = ret.strip()
	return ret

def split_words(words):
	"""Splits the words into results and excluded.
	
	>>> from search import search
	>>> esv=search.ReadIndex("ESV")
	>>> esv.split_words('hyphen-test -"excluded phrase"'
	...                 ' word -excl "test phrase"')
	(['hyphen-test', 'word', 'test phrase'], ['excluded phrase', 'excl'])
	"""

	phrase = ""
		

	def clear_phrase():
		is_excluded2 = is_excluded
		if phrase:
			if is_excluded:
				if in_regex:
					excl_regexes.append(phrase)
				else:
					excludes.append(phrase)
			else:
				if in_regex:
					regexes.append(phrase)
				else:
					results.append(phrase)

			is_excluded2 = False

		return "", is_excluded2
		
	
	in_phrase = False
	in_regex = False
	in_brackets = False
	is_excluded = False
	was_escape = False
	was_space = True
	results = []
	excludes = []
	regexes = []
	excl_regexes = []

	for letter in words:
		if letter == "-" and was_space:
			phrase, is_excluded = clear_phrase()
			is_excluded = True
			was_space = False
			

		elif not in_regex and letter == '"':
			phrase, is_excluded = clear_phrase()
		
			in_phrase = not in_phrase
			was_space = True
		
		elif not in_regex and not in_phrase and letter == '(':
			#phrase, is_excluded = clear_phrase()
			phrase += "("
		
			in_brackets = True
			was_space = True
		
		elif not in_regex and not in_phrase and letter == ')':
			phrase += ")"
			#phrase, is_excluded = clear_phrase()
		
			in_brackets = False
			was_space = True
		
		elif not in_phrase and not was_escape and letter == '/':
			phrase, is_excluded = clear_phrase()
		
			in_regex = not in_regex
			was_space = True
			
		elif not in_brackets and not in_phrase \
			and not in_regex and letter == " ":
			phrase, is_excluded = clear_phrase()
			was_space = True


		elif was_escape and letter == "\\":
			was_space = False
			was_escape = False
		
		elif in_regex and letter == "\\":
			was_escape = True
			was_space = False
			phrase += letter
			

		elif was_escape and letter == "/":
			phrase = phrase[:-1] + "/"
			was_space = False
			was_escape = False
		else:
			phrase += letter
		
			was_space = False
			was_escape = False
			

	phrase, is_excluded = clear_phrase()
	return results, excludes, regexes, excl_regexes

def WildCard(words):
	# \w is our basic word unit. However, this includes _
	# This shouldn't ever occur anyway.
	wildcards = {
		# * - 0 or more letters
		r"\*": "\w*", 

		# ? - 1 letter
		r"\?": "\w", 

		# + - 0 or more letters
		r"\+": "\w+",

		# [] - one of these characters
		r"\[([^]]+)\]": r"[\1]",

		# \d - a number
		r"\\d": r"\d",
		
		# One of the words (test, or, this)
		# TODO: in NASB,
		# "son of (three, God, test)" exclude man returns 33
		# "son of (three, God)" exclude man returns 35
		# "son of (three, God, test)" -man returns 24
		# "son of (three, God)" -man returns 26
		# this is to do with search string length, I think
		r"\(([^)]+)\)": lambda x:r"(%s)" % r[',\s*'].sub('|', x.group(1)),
		
	}

	# compile re's
	wildcards = [(re.compile(wildcard, flags=re.UNICODE), replace)
				  for wildcard, replace in wildcards.iteritems()]

	# if we make a substitution, we will not run the spellcheck
	# so it is important to return whether we did
	subbed = False

	for wildcard, replace in wildcards:
		words, was_subbed = wildcard.subn(replace, words)
		if was_subbed: 
			subbed = True
	
	return words, subbed

def process_word(phrase, flags, wordlist=None):
	# TODO We only remove punctuation, etc. when it is not a wildcard one.
	# FIX THIS!

	length = len(phrase)
	phrase, subbed = WildCard(phrase)

	# Check spelling (not for wildcarded or regex)
	if not subbed:
		phrase = removeformatting(phrase)
		badwords = []
		for word in phrase.lower().split(" "):
			if wordlist is not None and word not in wordlist:
				badwords.append(word)

		if(badwords):
			raise SpellingException, badwords

	phrase = phrase.replace(" ", r"\s+")
	phrase = r"\b%s\b" % phrase
	regex = re.compile(phrase, flags)

	return regex, length
