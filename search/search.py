#TODO check chr(e)tiens in acts 11:26 in frejnd - end of line
#import psyco
#psyco.log()
#psyco.full()
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate
from util.string_util import ReplaceUnicode, KillTags, remove_amps
from util.unicode import get_to_unicode
from util import search_utils
from util.search_utils import *
from swlib.pysw import SW, BookName, VK, TOP
import os
import re
import string
import cPickle
from util.debug import *
from query_parser import WildCard, removeformatting, split_words, process_word
from query_parser import SpellingException
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

			self.book.templatelist.append(template)
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
					
					self.books.append(self.booktype(self.version, bookname))

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
		searchrange=None, excludes=None):
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
		assert not advanced, "Advanced isn't supported at the moment"
		
		# Find our searchrange
		if searchrange:
			books=self.BookRange(searchrange)

		else:
			books=self.books
		
		results=[]
		
		flags = re.IGNORECASE * (not case_sensitive) | re.UNICODE | re.MULTILINE
		
		# Regular expression
		if regex:

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

				results += book.find_index(book.regex_search(comp))

			progress(("Done", 100))
			return results, [comp]
		
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

		return self.multi_search(words, books, proximity, flags,
			excludes, progress, regexes, excl_regexes)
		
	
	def multi_search(self, words, books, proximity, flags, 
			excludes, progress, regexes, excl_regexes):

		results = []

		badwords = []
		wordlist = []
		
		if self.booktype.gatherstatistics:
			index_word_list = self.statistics["wordlist"]
		else:
			index_word_list = None

		for word in words:
			try:
				wordlist.append(process_word(word, flags, index_word_list))

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

			matches = book.multi_search(wordlist[:], proximity, 
				excludes=excludelist)
			
			results += book.find_index(matches)
		
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

			self.book.templatelist.append(template)
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
