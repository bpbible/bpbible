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
import util
from swlib.pysw import SW, BookName, VK, TOP
import os
import re
import string
import cPickle
from util.debug import *
from query_parser import removeformatting, separate_words
from query_parser import SpellingException
from indexed_text import IndexedText, VerseIndexedText, DictionaryIndexedText
from stemming import get_stemmer
from fields import all_fields


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
	"""This function removes duplicates and overlaps in search results.
	>>> RemoveDuplicates(["Romans 6:3", "Romans 6:3"])
	['Romans 6:3']
	>>> RemoveDuplicates(["Romans 6:3 - Romans 6:4", "Romans 6:4"])
	['Romans 6:3 - Romans 6:4']
	>>> RemoveDuplicates(["Romans 6:3", "Romans 6:3 - Romans 6:4", "Romans 6:4"])
	['Romans 6:3 - Romans 6:4']
	>>> RemoveDuplicates(["Romans 6:3", "Romans 6:4"])
	['Romans 6:3', 'Romans 6:4']
	>>> RemoveDuplicates(["Romans 6:2 - Romans 6:3", "Romans 6:3 - Romans 6:4"])
	['Romans 6:2 - Romans 6:3', 'Romans 6:3 - Romans 6:4']
	>>> RemoveDuplicates(["Romans 6:2 - Romans 6:3", "Romans 6:3", "Romans 6:3 - Romans 6:4"])
	['Romans 6:2 - Romans 6:3', 'Romans 6:3 - Romans 6:4']
	"""
	btext = [] #second list
	seen = set()
	verses = set() #list of verses included
	removals = set()

	for a in vlist:
		spl = a.split(" - ")
		#remove single verses from list if already included
		#ie Lev 12:10, Lev 12:10-11 -> Lev 12:10-11
		#but Lev 12:9-10, Lev 12:10-11 stays same
		if len(spl) == 2:
			if spl[0] in seen:
				removals.add(spl[0])
				#btext.remove(spl[0])

		if a not in seen:
			# if we have already been included, don't include again
			if not (len(spl) == 1 and a in verses):
				btext.append(a)
				seen.add(a)
			
			verses.update(spl)
	return [x for x in btext if x not in removals]


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
		letters = set()
		for book in self.books:
			letters.update(book.text)
			wordlist.update(book.text.lower().split())

		self.statistics["wordlist"] = wordlist

		# remove whitespace
		letters.discard(u"\n")
		letters.discard(u" ")
		self.statistics["letters"] = letters

		stemmer = get_stemmer(self.book.mod)
		stem_map = {}
		for word, stemmed in zip(wordlist, stemmer.stemWords(wordlist)):
			if word in stem_map and stemmed not in stem_map:
				print word
			if stemmed in stem_map:
				stem_map[stemmed].append(word)

			else:
				stem_map[stemmed] = [word]

		self.statistics["stem_map"] = stem_map

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
	
	def Search(self, regexes, excl_regexes, fields, excl_fields,
		type=COMBINED, proximity=15, is_word_proximity=True, 
		progress=lambda x:x, searchrange=None):
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
		
		Out: results, regular expressions
		"""

		if self.book.version != self.version:
			self.book.SetModule(self.version)
		
		combined = type & COMBINED
		case_sensitive = type & CASESENSITIVE
		assert combined, "Combined or regex is currently obligatory!!!"
		
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
		
		if not regexes and not fields:
			# we can't search for just a negative at the moment
			# so -/a/ isn't a valid search
			return []

		return self.multi_search(
			regexes, excl_regexes, fields, excl_fields, books, proximity, 
			is_word_proximity, flags, progress
		)
		
	
	def multi_search(self, regexes, excl_regexes, fields, excl_fields, books, 
		proximity, is_word_proximity, flags, progress):

		results = []

		try:
			excludelist = [(re.compile(e, flags), 0) for e in excl_regexes]
			wordlist = [(re.compile(e, flags), 0) for e in regexes]
		except re.error, e:
			raise SearchException(
				"There seems to be an error in your regular expression.\n"
				"The error message given was: %s" % e
			)
		
		strongs = [[], []]
		for idx, values in enumerate((fields, excl_fields)):
			for (key, value) in values:
				for field in all_fields:
					if key == field.field_name:
						strongs[idx].append(
							(key, field.prepare(value))
						)
						break
				else:
					raise SearchException(
						"You cannot search on the field %r" % key
					)
				
		# Do multiword
		for num, book in enumerate(books):
			continuing = progress((book.bookname, (100*num)/len(books)))
			if not continuing:
				break			

			matches = book.multi_search(wordlist[:], proximity,
				is_word_proximity=is_word_proximity, excludes=excludelist,
				strongs=strongs[0][:], excluded_strongs=strongs[1])

			results += book.find_index(matches)
		
		progress(("Done", 100))
		return results
	
	
	def WriteIndex(self, progress=util.noop):
		search_utils.WriteIndex(self, progress=progress)

class GenBookIndex(Index):
	def __init__(self, version, progress=lambda x:x, booktype=IndexedText):
		super(GenBookIndex, self).__init__(version, progress, booktype=booktype)
	
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
			
			self.book.SetModule(oldmod, notify=False)
		
class DictionaryIndex(GenBookIndex):
	def __init__(self, version, progress=lambda x:x, 
		booktype=DictionaryIndexedText):
		super(DictionaryIndex, self).__init__(version, progress, 
			booktype=booktype)
	
	@property
	def book(self):
		return biblemgr.dictionary

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
			topics = self.book.GetTopics()
			self.book.SetModule(mod, notify=False)
			mod = self.book.mod

			self.book.templatelist.append(template)
			entry_size = 200
			for a in range(0, len(topics), entry_size):
				continuing = progress((topics[a], 
							99*a/len(topics)))

				
				self.books.append(self.booktype(self.version, 
					start=topics[a], entries=entry_size))
				
				if not continuing:
					raise Cancelled
					

			if self.booktype.gatherstatistics:
				self.GatherStatistics()
				
		finally:
			log.setLogLevel(old_log_level)
		
			biblemgr.restore_state()
			self.book.templatelist.pop()
			
			self.book.SetModule(oldmod, notify=False)
		

class CommentaryIndex(Index):
	@property
	def book(self):
		return biblemgr.commentary
		
if __name__ == '__main__':
	import doctest
	doctest.testmod()
