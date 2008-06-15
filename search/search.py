#import psyco
#psyco.log()
#psyco.full()
from backend.bibleinterface import biblemgr
from util.util import ReplaceUnicode, KillTags, VerseTemplate, remove_amps
from util.unicode import get_to_unicode
from util import search_utils
from util.search_utils import *
from swlib.pysw import SW, BookName
import os
import re
import string
import cPickle
from util.debug import *

#from copy import copy
wordlist2 = {}

_number = 0

def Number():
	global _number
	_number+=1
	return 1<<(_number - 1)

PHRASE = Number()
MULTIWORD = Number()
REGEX = Number()
CASESENSITIVE = Number()
ADVANCED = Number()
ADVANCED_REGEX = ADVANCED | REGEX
COMBINED = Number()

def WildCard(words):
	# \w is our basic word unit. However, this includes _
	# This shouldn't ever occur anyway.
	all = "\w"

	wildcards = {
		# * - 0 or more letters
		r"\*": all+"*", 

		# ? - 1 letter
		r"\?": all, 

		# + - 0 or more letters
		r"\+": all+"+",

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
		r"\(([^)]+)\)": lambda x:r"(%s)" % r[',\s*'].sub('|', x.group(1))
		
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

def RemoveDuplicates(vlist):
	"""This function removes duplicates and overlaps.

e.g. [Romans 6:3, Romans 6:3] -> [Romans 6:3]
	 [Romans 6:3-4, Romans 6:4] -> [Romans 6:3-4]"""
	btext = [] #second list
	verses = [] #list of verses included

	for a in vlist:
		spl = a.split(" - ")
		#remove single verses from list if already included
		#ie Lev 12:10, Lev 12:10-11 -> Lev 12:10-11
		#but Lev 12:9-10, Lev 12:10-11 stays same
		if(len(spl)==2):
			if(spl[0] in btext):
				btext.remove(spl[0])

		if(a not in btext):
			# if we have already been included, don't include again
			if not (len(spl)==1 and a in verses):
				btext.append(a)
			verses.extend(spl)
	return btext


class SearchException(Exception):
	pass

class Cancelled(Exception):
	pass

class SpellingException(Exception):
	def __init__(self, wordlist):
		self.wrongwords=wordlist

	def __str__(self):
		return ", ".join(self.wrongwords)


vk=SW.VerseKey()


class BookIndex(object):
	gatherstatistics=True
	#__slots__=["index", "text", "version", "testament", "book", "vk",\
	#"bookname", "wordlist"]
	def __init__(self, version, testament, booknumber):
		self.index=[("NULL", 0, 0)] # ref, start, length
		self.text=""
		self.version=version
		self.testament = testament
		self.book=booknumber
		self.bookname = vk.bookName(self.testament, self.book)
		
		self.GenerateIndex()

	def GenerateIndex(self):
		verses = []
		mod = biblemgr.bible.mod
		#mod_to_unicode = get_to_unicode(mod)
	
		vk = SW.VerseKey(self.bookname, self.bookname)

		old_vk = mod.getKey()
		
		vk.Persist(1)
		mod.setKey(vk)
		vk.thisown = False

		while vk.Error() == '\x00':
			# TODO: do tests to make sure striptext works as expected
			# (with respect to whitespace, uppercase, etc)
			# TODO: take this into a function so it can be used by
			# highlighting code
			content = mod.StripText().decode("utf-8", "ignore")
			
			#content = content.replace("<br />", "\n")

			#content = remove_amps(KillTags(ReplaceUnicode(content)))
			content = content.replace("\n", " ")
			#TODO: do wordlist statistics here, as then the user can get
			#the proper spelling suggestions
			#need new remove format
			# only punctuation not to remove would be ', I think
			###TODO### battle--you
			###TODO### number of each
			#def add(word):
			#	if(word in wordlist2):
			#		wordlist2[word]+=1
			#	else: wordlist2[word] = 1

			#for a in removeformatting2(content).split(" "):
			#	#if verse is empty, a will be to.
			#	if(a): add(a)

			content = removeformatting(content)
			
			# If verse is empty, don't include it
			if content:
				content+=" "
				#vk.setText(ref)
				ind=(vk.Chapter(), vk.Verse())
				
				# After here, we must not fiddle with text at all as its
				# indexes are in place.
				self.index.append((ind, self.index[-1][1] +
					self.index[-1][2], len(content)))

				verses.append(content)
			
			vk.increment(1)

		self.text = "".join(verses)


	def AdvancedRegex(self, phrase, case_sensitive=False):
		"""Like regex, but returns matched text as well"""
		mylist = []
		
		flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE

		comp = re.compile(phrase, flags)
		for a in comp.finditer(self.text):			
			mylist.append((a.start(), a.end()-a.start(), a.group()))

		return mylist
		
	def RegexSearch(self, comp, case_sensitive=False):
		mylist = []
		
		for a in comp.finditer(self.text):
			mylist.append((a.start(), a.end()-a.start()))

		return mylist

	def FindIndex(self, mylist):
		"""This function turns a sorted list of begin, end pairs and turns them
		into Bible References using the index"""
		vk.setText(self.bookname)
		upto = 0
		if(not mylist):
			return []
		num = mylist[upto][0]
		ret = []
		for idx, a in enumerate(self.index):
			# find in index
			# mylist must be sorted
			while a[1]+a[2]>num:
				# loop here because search phrase may be
				# multiple times in one verse, so we get all
				n = 1
				# This loop tells us if we go over verse boundaries
				while (idx+n<len(self.index) and \
					self.index[idx+n][1] < num+mylist[upto][1]):
					n += 1
	
				if(n>1):
					vk.Chapter(a[0][0])
					vk.Verse(a[0][1])
					ref1=vk.getText()
					vk.Chapter(self.index[idx+n-1][0][0])
					vk.Verse(self.index[idx+n-1][0][1])
					ref2=vk.getText()
					ret.append(ref1 +" - "+ ref2)

				else:
					vk.Chapter(a[0][0])
					vk.Verse(a[0][1])

					ref1=vk.getText()
					ret.append(ref1)
	
				upto += 1
				if(upto >= len(mylist)):
					return ret
				num = mylist[upto][0]
		
		dprint(ERROR, "Exceeded index length", mylist[upto])
		return ret

	def MultiSearch(self, wordlist, proximity, case_sensitive=False, \
	average_word=0, minimum_average=5, ignore_minimum=False, excludes=(), 
	try_all=False):

		# t is shorter to use than self.text
		t = self.text
		
		mylist = []
		
		#empty query, empty results...
		
		#compile regex - it is escaped and may be case insensitive
		#esc = re.escape(wordlist[0])
		# keep track of our bounds
		
		total_length = 0
		for regex, length in wordlist:
			total_length += length

		if(not average_word):
			average_word = total_length/len(wordlist)

		if(average_word < minimum_average and not ignore_minimum):
			average_word = minimum_average
		
		
		wordlist = [word for word, length in wordlist]
		
		relist = []
		if(not try_all):
			# find the first word in the text, and then search based on it
			# TODO: do all, and then match based on that?
			# seems to be slower though
			for a in wordlist[0].finditer(t):
				relist+=[a]
			del wordlist[0]
		else:
			relist2 = {}
			for r in wordlist:
				relist2[r] = list(r.finditer(t))
			min = (0, None)
			for comp, results in relist2.items():
				if(min[0]<len(results)):
					min = (comp, len(results))
			relist = relist2[min[0]]
			del relist2[min[0]]
			#relist = relist2.keys()
			#print relist

		len_t = len(t)
		len_words = 0#len(words)
		lastbounds = (0,0)
		
		for id, match in enumerate(relist):
			# if the next match of the master word
			# is in the range we have just matched,
			# go onto the next one
			# NOTE: This is probably undesirable behaviour
			# e.g. searching for foo bar in boink foo foo bar boink
			# will yield foo foo bar instead of foo bar
			if(match.start() < lastbounds[1]):
				continue
			
			# Make sure our boundaries are at word borders.
			# This is important, as otherwise we may match incorrectly
			lower = match.start()-proximity*average_word-len_words
			if(lower>0 and not t[lower]==" "):
				# why not get next space instead of previous?
				# might be quicker?
				lower = t.rfind(" ", 0, lower) 
			upper = match.end()+proximity*average_word+len_words
			if(upper<len_t and not t[upper]==" "):
				upper = t.find(" ", upper, len_t)

			if(lower < 0):lower=0
			if(upper>len_t): upper=len_t
			bounds = lower, upper
			
			textrange = t[bounds[0]: bounds[1]]
			#t[bounds[0]: bounds[1]]

			docontinue=False
			for exclude, length in excludes:
				if(exclude.search(textrange)):
					docontinue=True
					break

			if docontinue: continue

			inrange = True
			for comp in wordlist:
				if(not comp.search(textrange)):
					inrange = False
					break

			if not inrange:
				continue
			
			start = match.start()
			end = match.end()
			
			# make range as narrow as possible
			docontinue = False
			for comp in wordlist:
				#try back first
				backrange = self.text[bounds[0]: match.start()]
				forwardrange = self.text[match.end(): bounds[1]]
				#backind2 = t.rfind(word, bounds[0], match.start())
				last = None
				for j in comp.finditer(backrange):
					last = j
								
				if last: backind = last.start() + bounds[0]
				else: backind = -1
				#print backind, backind2
				#else:
				#	backind = text.rfind(word, bounds
				if backind < lastbounds[1]:
					backind = -1
	
				#if bounds[1]:
				#	forwardind2 = t.find(word, match.end(), bounds[1])
				#else:
				#	forwardind2 = t.find(word, match.end())
				forwardind = comp.search(forwardrange)
				if forwardind: forwardind = forwardind.end() + match.end()
				else: forwardind = -1
				#if(forwardind2 != -1): forwardind += len(word)
				#print forwardind, forwardind2
				
				#if we stray into the previous matches bounds, ignore it
				if(forwardind < lastbounds[1]):
					forwardind = -1
	
				if(forwardind == -1 and backind == -1):
					docontinue = True
					break
	
				if(forwardind == -1):
					ind = backind

				elif(backind == -1 or match.start() - backind > forwardind -
				match.end()):
					ind = forwardind
				else: ind = backind
				if(ind < start):
					start = ind
				if ind > end:
					end = ind
			if docontinue:
				continue
	
			lastbounds=(start, end)
			mylist.append((start, end - start))

		return mylist

def printx(x): 
	print x
	return True

class Index(object):
	def __init__(self, version, progress=printx, booktype=BookIndex):
		self.version=version
		self.booktype = booktype
		self.init(progress)

	def init(self, progress=lambda x:x):	
		"""Index.init - reindxes index"""
		self.books=[] # has to stay in order
		#self.index = [("NULL",0,0)] # reference, start, length
		#self.text = ""
		self.statistics = {}
		self.GenerateIndex(self.version, progress)

	def GenerateIndex(self, mod, progress = lambda x:x):
		"""Index.GenerateIndex - Collates book indexes"""
		#text = ""
		#global text
		#global index
		template = VerseTemplate("$text\n")
		biblemgr.temporary_state(biblemgr.plainstate)
		log = SW.Log.getSystemLog()
		old_log_level = log.getLogLevel()
		log.setLogLevel(0)
		
		#apply template
		if not biblemgr.bible.ModuleExists(mod):#SetModule(mod):
			raise Exception, "Module %s not found" % mod

		oldmod = biblemgr.bible.version
		
		
		try:
			biblemgr.bible.SetModule(mod, notify=False)
			mod = biblemgr.bible.mod

			biblemgr.bible.templatelist.push(template)
			offsets = [0]
			books = 0
			for i in range(1,3):
				offsets.append(books)
				books += vk.bookCount(i)
			for i in [1, 2]:
				for j in range(1, vk.bookCount(i)+1):
					bookname=vk.bookName(i,j)
					continuing = progress((bookname, 
									99*(j+offsets[i])/books))
					if not continuing:
						raise Cancelled
					
					self.books.append(self.booktype(self.version,i,j))

			if(self.booktype.gatherstatistics):
				self.GatherStatistics()
				
		finally:
			log.setLogLevel(old_log_level)
		
			biblemgr.restore_state()
			biblemgr.bible.templatelist.pop()
			
			biblemgr.bible.SetModule(oldmod, notify=False)
			

	def GatherStatistics(self):
		"""Index.GatherStatistics - Gathers statisitics including ranks,
		occurrences and wordlists for spellchecking"""
		#idx=collections.defaultdict(lambda:0)
		#for book in self.books:
		#	for a in book.text.lower().split(" "):
		#		idx[a] += 1

		#b=sorted(idx.iteritems(), key=lambda x:x[1], reverse=True)
		#self.statistics["occurrences"] = b

		#rank={}
		#for a1, a in enumerate(b):
		#	rank[a[0]]=a1

		#self.statistics["rank"]=rank
		#self.statistics["wordlist"] = rank.keys()
		wordlist = set()
		for book in self.books:
			wordlist.update(book.text.lower().split(" "))

		self.statistics["wordlist"] = wordlist

	def BookRange(self, searchrange):
		"""Index.BookRange - Finds all the BookIndexes in the current range

		Examples: "gen-mal" -> Old testament Books
		"matt-john, genesis" -> Genesis and Gospels
		"matt-twinkle" -> SearchException("Book 'twinkle' not found")"""
		
		def lookup_book(item):
			first = BookName(item)

			if not first:
				raise SearchException, "Book '%s' not found!" % item
	
			for index, book in enumerate(self.books):
				if BookName(book.bookname) == first:
					return index
	
			raise SearchException, "Book '%s' not found!" % first
		
		
		books=[]

		ranges = searchrange.split(",")

		for item in ranges:
			thisrange = item.split("-")
			if len(thisrange) > 2:
				raise SearchException("Only one dash allowed in '%s'" % item)	
			
			if("FOO" == thisrange[0].upper()):
				#EASTEREGG
				raise SearchException, "Would that be first or second foo?"

		
			f = lookup_book(thisrange[0])

			if len(thisrange) == 2:
				l = lookup_book(thisrange[1])

			else: 
				l = f

			if l < f: 
				l, f = f, l

			for number in range(f, l+1):
				if number not in books:
					books.append(number)

		books = [self.books[x] for x in sorted(books)]
		return books
	
	def Search(self, words, type=COMBINED, proximity=15, progress=lambda x:x, 
		searchrange=None, excludes=None, try_all=False):
		"""Index.Search - this function does all bible searching
		
		In:	words - words to search for
			type - 	One of:
						COMBINED: all three below
						REGEX: regex search
						PHRASE: phrase search, supports wildcards
						MULTIWORD: search for words within a given proximity
					and any of:
						CASESENSITIVE: does man==Man?
						ADVANCED: groups by matched text. Not MULTIWORD
			proximity - search radius for MULTIWORD
			progress - function for reporting search progress
			searchrange - see BookRange
			excludes - MULTIWORD only, words to exclude
		
		Out: results, regular expressions
		"""

		dprint(MESSAGE, "Search called with arguments", words, type,
			proximity, progress, searchrange, excludes)
		if biblemgr.bible.version != self.version:
			biblemgr.bible.SetModule(self.version)
		
		combined = type & COMBINED
		case_sensitive = type & CASESENSITIVE
		regex = type & REGEX
		phrase = type & PHRASE
		advanced = type & ADVANCED
		
		#if excludes:
		#	excludes, exsubbed = WildCard(excludes)
		#	if not exsubbed:
		#		excludes = removeformatting(excludes)

		# Find our searchrange
		if searchrange:
			books=self.BookRange(searchrange)

		else:
			books=self.books
		
		results=[]
		
		#process for phrase
		#if(phrase):
		#	#remove punctuation
		#	if not subbed: words = removeformatting(words)
		#	words = " ".join(map(lambda x: r"\b"+x+r"\b", words.split()))
		
		# Regular expression
		if(regex and not advanced):
			#esc = re.escape(words)
			flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE

			try:
				comp = re.compile(words, flags)		
			except re.error, e:
				raise SearchException(
					"There seems to be an error in your regular expression.\n"
					"The error message given was: %s" % e
				)
			
			
			for num, book in enumerate(books):
				continuing = progress((book.bookname, (100*num)/len(books)))
				if not continuing:
					break
				results += book.FindIndex(
					book.RegexSearch(comp,  case_sensitive)
				)

			progress(("Done", 100))
			return results, [comp]
		
		# Advance Phrase or Regex
		# as phrase has been processed, it is now a regex
		# ### UNSUPPORTED
		if(advanced):
			# TODO - searching for the* gives matches for thening, which should
			# be strengthening
			for num, book in enumerate(books):
				# get (start, end, match) pairs
				subresults = book.AdvancedRegex(words, case_sensitive)
				#if subresults: print subresults
				# Match start, end to text
				inds = book.FindIndex(map(lambda x: x[:2], subresults))
				#if inds: print inds
				text = map(lambda x: x[2], subresults)
				if(not case_sensitive):
					text = map(lambda x: x.lower(), text)
				
				results += zip(text, inds)
				continuing = progress((book.bookname, (100*num)/len(books)))
				if not continuing:
					break				
			
			# group by results
			# ["identifier": [results, more], "foo":[bar, boing, bip]]
			retval={}
			for a in results:
				if a[0] in retval:
					retval[a[0]].append(a[1])
				else:
					retval[a[0]]=[a[1]]
			progress(("Done", 100))

			return retval
		
		if excludes:
			excludes = excludes.split()
		else:
			excludes = []

		regexes = []
		excl_regexes = []
		if combined:
			words, excl, regexes, excl_regexes = self.split_words(words)
			excludes.extend(excl)

		elif phrase:
			words = [words]

		else:
			words = words.split()

		return self.multi_search(words, books, proximity, case_sensitive, 
			excludes, progress, regexes, excl_regexes)
		
	
	def process_word(self, phrase, flags):
		length = len(phrase)

		# Process wildcards (not for REGEX)
		subbed = False
		phrase, subbed = WildCard(phrase)

		# Check spelling (not for wildcarded or regex)
		if not subbed:
			phrase = removeformatting(phrase)
			#wordlist = phrase.split(" ")
			badwords = []
			for a in phrase.lower().split(" "):
				if (self.booktype.gatherstatistics and 
						a not in self.statistics["wordlist"]):
					badwords.append(a)

			if(badwords):
				raise SpellingException, badwords

		#remove punctuation
		#TODO remove formatting above
		if not subbed: phrase = removeformatting(phrase)
		phrase = r"\b%s\b" % phrase
		regex = re.compile(phrase, flags)

		return regex, length
		
	def multi_search(self, words, books, proximity, case_sensitive, 
			excludes, progress, regexes, excl_regexes):

		results = []
		flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE

		badwords = []
		wordlist = []

		for word in words:
			try:
				wordlist.append(self.process_word(word, flags) )

			except SpellingException, e:
				badwords.extend(e.wrongwords)

		if not wordlist and not regexes:
			if badwords:
				raise SpellingException(badwords)
		
			return [], []
		
		
		excludelist = []
		
		for word in excludes:
			try:
				excludelist.append(self.process_word(word, flags))

			except SpellingException, e:
				badwords.extend(e.wrongwords)

		if badwords:
			raise SpellingException(badwords)

		try:
			excludelist.extend((re.compile(e, flags), 0) for e in excl_regexes)
			wordlist.extend((re.compile(e, flags), 0) for e in regexes)
		except re.error, e:
			raise SearchException(
				"There seems to be an error in your regular expression.\n"
				"The error message given was: %s" % e
			)
				
		# Do multiword
		for num, book in enumerate(books):
			continuing = progress((book.bookname, (100*num)/len(books)))
			if not continuing:
				break			

			r = book.FindIndex(book.MultiSearch(wordlist[:], proximity, 
			case_sensitive=case_sensitive, excludes=excludelist, try_all=False))
 
			results += r
		
		progress(("Done", 100))
		return results, [regex for regex, length in wordlist]
	
	def split_words(self, words):
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
	
	def WriteIndex(self):
		search_utils.WriteIndex(self)
		

# pre compile our regular expressions
re_list = (
	"(?<=\d),(?=\d)", 
	"(?<=\w)'(?=\w)",
	"(?<=\w)-(?=\w)", 
	" +", 
	r"[^\w ]",
	"(?<!\d),",
	",(?!\d)",
	"(?<!\w)'",
	"'(?!\w)",
	"(?<!\w)-",
	"-(?!\w)",
	',\s*'	
)
l = "((?<=\d),(?=\d)|(?<=\w)'(?=\w)|(?<=\w)-(?=\w))"

r = {}
for a in re_list:
	r[a] = re.compile(a, flags=re.UNICODE)

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
	ret = r["[^\w ]"].sub("", ret)
	ret = r[" +"].sub(" ", ret)
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
	

def FindIndex(mylist, index):
	"""This function turns a sorted list of begin, end pairs and turns them
	into Bible References using the index"""
	upto = 0
	if(not mylist):
		return []
	num = mylist[upto][0]
	ret = []
	for idx, a in enumerate(index):
		# find in index
		# mylist must be sorted
		while a[1]+a[2]>num:
			# loop here because search phrase may be
			# multiple times in one verse, so we get all
			n = 1
			# This loop tells us if we go over verse boundaries
			while (idx+n<len(index) and index[idx+n][1] < num+mylist[upto][1]):
				n += 1

			if(n>1):
				ret.append(a[0]+" - "+index[idx+n-1][0])
			else:
				ret.append(a[0])

			upto += 1
			if(upto >= len(mylist)):
				return ret
			num = mylist[upto][0]
	return None
				
def GetVerse(ref, indexclass):
	text = indexclass.text
	index = indexclass.index
	if(ref.find("-")!=-1):
		first, last = ref.split(" - ")
		ref = first
	else:
		first = ref
		last = ref
	doall = False
	ret = ""
	for a in index:
		if(doall):
			ret += text[a[1]:a[1]+a[2]] + "| "
		if(a[0] == ref):
			if(first == last):
				return text[a[1]:a[1]+a[2]]
			else:
				if(ref == first):
					ret += text[a[1]:a[1]+a[2]] + "| "
					ref = last
					doall = True
				elif(ref == last):
					return ret


#def GatherStatistics(text):
#	idx={}
#	for a in text.split(" "):
#		txt = a.lower()
#		if(txt in idx):
#			idx[txt] += 1
#		else:
#			idx[txt] = 1
#	b=sorted(idx.iteritems(),cmp=lambda x, y:x[1]-y[1], reverse=True)
#	#yield b
#
#	rank={}
#	for a1, a in enumerate(b):
#		rank[a[0]]=a1
#	return rank#yield rank
#	distinctwords=lambda : len(b)
#	def occurences(word):
#		if word in idx:
#			return idx[word]
#		return 0
#		
#	d={}
#	for a in idx:
#		if idx[a] in d:
#			d[idx[a]] += 1
#		else:
#			d[idx[a]] = 1
#
#	e = sorted(d.iteritems(),cmp=lambda x, y:x[0]-y[0], reverse=False)
#	#yield e
#	numofwordswhich = lambda number: len(wordswhichoccurxtimes(number))
#	
#
#	def wordswhichoccurxtimes(number):
#		ret=[]
#		for c, a in enumerate(b):
#			if(a[1]==number):
#				ret+=[a[0]]
#		return ret
#		
def flatten(l):
	ret=[]
	lt=type([])
	for a in l:
		if(type(a)==lt):
			ret+=flatten(a)
		else:
			ret+=[a]
	return ret
#
def printverses(l, index):
	for a in flatten(l):
		print "%s: %s\n" % (a, GetVerse(a, index))

if __name__ == '__main__':
	esv=Index("ESV")
