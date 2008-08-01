#TODO check chr(e)tiens in acts 11:26 in frejnd - end of line
#import psyco
#psyco.log()
#psyco.full()
from backend.bibleinterface import biblemgr
from util.util import ReplaceUnicode, KillTags, VerseTemplate, remove_amps
from util.unicode import get_to_unicode
from util import search_utils
from util.search_utils import *
from swlib.pysw import SW, BookName, VK, TOP
import os
import re
import string
import cPickle
from util.debug import *
import process_osis
from query_parser import WildCard, removeformatting, split_words
from indexed_text import IndexedText, VerseIndexedText


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


vk = SW.VerseKey()

def printx(x): 
	print x
	return True

class BookIndex(object):
	"""Place holder to tell people to rebuild indexes.
	This should be removed before the 0.4 release"""
	def __setstate__(self, state):
		raise Exception("You need to rebuild your index")

class Index(object):
	def __init__(self, version, progress=printx, booktype=VerseIndexedText):
		self.version = version
		self.booktype = booktype
		self.init(progress)
	
	@property
	def book(self):
		return biblemgr.bible

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
		if not self.book.ModuleExists(mod):#SetModule(mod):
			raise Exception, "Module %s not found" % mod

		oldmod = self.book.version
		
		
		try:
			self.book.SetModule(mod, notify=False)
			mod = self.book.mod

			self.book.templatelist.push(template)
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
			self.book.templatelist.pop()
			
			self.book.SetModule(oldmod, notify=False)
			

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
			wordlist.update(book.text.lower().split())

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

		if self.book.version != self.version:
			self.book.SetModule(self.version)
		
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
			flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE | \
					re.MULTILINE

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
			words, excl, regexes, excl_regexes = split_words(words)
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
		phrase = phrase.replace(" ", r"\s+")
		phrase = r"\b%s\b" % phrase
		regex = re.compile(phrase, flags)

		return regex, length
		
	def multi_search(self, words, books, proximity, case_sensitive, 
			excludes, progress, regexes, excl_regexes):

		results = []
		flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE | \
					re.MULTILINE
		

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
	
	
	def WriteIndex(self):
		search_utils.WriteIndex(self)

class GenBookIndex(Index):
	def __init__(self, version, booktype=IndexedText):
		super(GenBookIndex, self).__init__(version, booktype=booktype)
	
	@property
	def book(self):
		return biblemgr.genbook

	def GenerateIndex(self, mod, progress = lambda x:x):
		"""Index.GenerateIndex - Collates book indexes"""
		template = VerseTemplate("$text\n")
		biblemgr.temporary_state(biblemgr.plainstate)
		log = SW.Log.getSystemLog()
		old_log_level = log.getLogLevel()
		log.setLogLevel(0)
		
		#apply template
		if not self.book.ModuleExists(mod):
			raise Exception, "Module %s not found" % mod

		oldmod = self.book.version
		
		
		try:
			self.book.SetModule(mod, notify=False)
			mod = self.book.mod

			self.book.templatelist.push(template)
			self.books.append(self.booktype(self.version))

			if self.booktype.gatherstatistics:
				self.GatherStatistics()
				
		finally:
			log.setLogLevel(old_log_level)
		
			biblemgr.restore_state()
			self.book.templatelist.pop()
			
			biblemgr.genbook.SetModule(oldmod, notify=False)
		
class DictionaryIndex(GenBookIndex):
	@property
	def book(self):
		return biblemgr.dictionary

class CommentaryIndex(Index):
	@property
	def book(self):
		return biblemgr.commentary
		
if __name__ == '__main__':
	esv=Index("ESV")
