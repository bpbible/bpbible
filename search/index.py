#TODO check chr(e)tiens in acts 11:26 in frejnd - end of line
from backend.bibleinterface import biblemgr
from backend.verse_template import VerseTemplate
from util import search_utils
from util.search_utils import *
import util
from swlib.pysw import SW
from swlib import pysw
import re
from util.debug import *
from search.indexed_text import (
	IndexedText, VerseIndexedText, DictionaryIndexedText
)
from search.stemming import get_stemmer
from search.fields import all_fields


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

class BadBook(Exception):
	def __init__(self, index, errors):
		errors = [
			_("A problem was detected with this book while indexing it:")
		] + list(errors) + ['',
			_("Check whether there is a newer version of this book which "
			"might fix this problem.")
		]

		super(BadBook, self).__init__('\n'.join(errors))
		self.index = index
	

class Index(object):
	def __init__(self, version, progress=printx, booktype=VerseIndexedText):
		self.version = version
		self.booktype = booktype
		self.init(progress)
	
	@property
	def book(self):
		return biblemgr.get_module_book_wrapper(self.version)

	def init(self, progress=lambda x:x):	
		"""Index.init - reindxes index"""
		self.books=[] # has to stay in order
		self.statistics = {}
		self.GenerateIndex(self.version, progress)
		self.check_for_errors()

	def check_for_errors(self, raise_exception=True):
		errors = []
		has_xml_errors = False
		for item in self.books:
			if item.has_xml_errors:
				has_xml_errors = True

			for i in item.errors_on_collection:
				if i not in errors:
					errors.append(i)
			
		if errors:
			if raise_exception:
				raise BadBook(self, errors)
			else:
				return True

		elif has_xml_errors:
			dprint(WARNING, "Invalid XML found")
			return True

		return False
	
	def GenerateIndex(self, mod, progress = lambda x:x):
		"""Index.GenerateIndex - Collates book indexes"""
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
					bookname = vk.bookName(i,j)
					# two translates in case of dashes
					bookname_ui = pysw.locale.translate(
						pysw.locale.translate(
							bookname
						)
					).decode(pysw.locale_encoding)

					continuing = progress((bookname_ui, 
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
			#if word in stem_map and stemmed not in stem_map:
			#	print word
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
		
		
		books=[]

		ranges = searchrange.split(",")

		for item in ranges:
			thisrange = item.split("-")
			if("FOO" == thisrange[0].upper()):
				#EASTEREGG
				raise SearchException, "Would that be first or second foo?"

			for idx in range(len(thisrange)+1):
				# look for a split point
				# We go through every split point and see if it makes sense
				# with a dash there.
				b1 = ''.join(thisrange[:idx+1])
				b2 = ''.join(thisrange[idx+1:])
				
				bookidx_1 = pysw.find_bookidx(b1)
				bookidx_2 = pysw.find_bookidx(b2)
				
				# if neither are book names (both empty, or something) keep on
				if bookidx_1 is None and bookidx_2 is None:
					continue
				
				# one bookname didn't match at all - it wasn't just empty
				if (bookidx_1 is None and b1) or (bookidx_2 is None and b2):
					continue
				
				if bookidx_1 is None:
					f = bookidx_2
					l = f
				else:
					f = bookidx_1
					if bookidx_2:
						l = bookidx_2
					else:
						l = f

				break

			else:
				raise SearchException(
					_("Couldn't understand book search range '%s'") 
					% searchrange
				)	

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
			return [], False

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
				_("There seems to be an error in your regular expression.\n"
				"The error message given was: %s") % e
			)
		
		strongs = [[], []]
		for idx, values in enumerate((fields, excl_fields)):
			for (key, value) in values:
				for field in all_fields:
					if key == field.field_name:
						strongs[idx].append(
							(field.field_to_use, field.prepare(value))
						)
						break
				else:
					raise SearchException(
						_("You cannot search on the field %r") % key
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
		
		progress((_("Done"), 100))

		if not fields:
			maybe_incorrect_results = False
		else:
			maybe_incorrect_results = self.check_for_errors(raise_exception=False)
		return results, maybe_incorrect_results
	
	
	def WriteIndex(self, progress=util.noop):
		search_utils.WriteIndex(self, progress=progress)

class GenBookIndex(Index):
	def __init__(self, version, progress=lambda x:x, booktype=IndexedText):
		super(GenBookIndex, self).__init__(version, progress, booktype=booktype)

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
			topics = self.book.GetTopics()
			
			mod = self.book.mod

			self.book.templatelist.append(template)
			entry_size = 200
			for a in range(0, len(topics), entry_size):
				continuing = progress((topics[a], 
							95*a/len(topics)))

				
				self.books.append(self.booktype(self.version, 
					start=topics[a], entries=entry_size))
				
				if not continuing:
					raise Cancelled
					

			if self.booktype.gatherstatistics:
				progress(("index", 99))
				self.GatherStatistics()
				
		finally:
			log.setLogLevel(old_log_level)
		
			biblemgr.restore_state()
			self.book.templatelist.pop()
			
			self.book.SetModule(oldmod, notify=False)
		

class CommentaryIndex(Index):
	pass
		
if __name__ == '__main__':
	import doctest
	doctest.testmod()
