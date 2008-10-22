import Sword as SW
import os
import re
import sys
from util.debug import *
from util.unicode import to_str, to_unicode
from util import is_py2exe
from util import classproperty

def _test():
	from swlib import pysw
	import doctest	
	print doctest.testmod(pysw)

if __name__ == '__main__':
	_test()

	# don't go any further, or we will crash after creating a versekey after 
	# the second stringmgr we construct (__main__ and swlib.pysw each have a
	# stringmgr)
	sys.exit()

# constants
REG_ICASE = 1 << 1
SWMULTI = -2
SWPHRASE = -1
SWREGEX = 0

POS_TOP = 1
POS_BOTTOM = 2
POS_MAXVERSE = 3
POS_MAXCHAPTER = 4
POS_MAXBOOK = 5

TOP = SW.SW_POSITION(POS_TOP)
BOTTOM = SW.SW_POSITION(POS_BOTTOM)
MAXVERSE = SW.SW_POSITION(POS_MAXVERSE)
MAXCHAPTER = SW.SW_POSITION(POS_MAXCHAPTER)
MAXBOOK = SW.SW_POSITION(POS_MAXBOOK)

# do renaming of SW.SWMgr -> SW.Mgr
for a in dir(SW):
	if(a[:2]=="SW"):
		setattr(SW, a[2:], getattr(SW, a))


if is_py2exe():
	# py2exe may get paths wrong
	if os.path.dirname(sys.argv[0]):
		os.chdir(os.path.dirname(sys.argv[0]))

if hasattr(sys, "SW_dont_do_stringmgr"):
	dprint(WARNING, "Skipping StringMgr initialization")
else:
	# StringMgr handling
	class MyStringMgr(SW.PyStringMgr):
		def getUpper(self, buf):
			# TODO: a more advanced heuristic like bibletime's to check whether it
			# is utf8 or latin1
			encodings = "UTF-8", "cp1252"
			text = buf.c_str()
			#print `text`
			for enc in encodings:
				try:
					# do an uppercase on the unicode object, then re-encode it 
					# back to how it was.
					# then set the buffer to the new string
					buf.set(text.decode(enc).upper().encode(enc))
					return
	
				except UnicodeDecodeError:
					pass
	
			dprint(WARNING, "Couldn't convert text to uppercase", text)
			buf.set(text.upper())
			return
	
		def supportsUnicode(self):
			return True
			
	
	m = MyStringMgr()
	
	# we don't own this, the system string mgr holder does
	m.thisown = False
	SW.StringMgr.setSystemStringMgr(m)
	
	# *only* after we've set the system string mgr can we set the system 
	# locale mgr...
	locale_mgr = SW.LocaleMgr.getSystemLocaleMgr()
	locale_mgr.loadConfigDir("resources/locales.d")
	
	if locale_mgr.getLocale("bpbible"):
		locale_mgr.setDefaultLocaleName("bpbible")
	else:
		dprint(WARNING, "bpbible locale not found")


class VerseParsingError(Exception): pass
#INEFFICIENT (create a new key always)
def KeyExists(key):
	return not(ord(SW.VerseKey(key).Error()))

def set_vk_chapter_checked(self, chapter):
	chapters = self.chapterCount(ord(self.Testament()), ord(self.Book()))
	if 0 < chapter <= chapters:
		self.Chapter(chapter)
	else:
		raise VerseParsingError("There are only %d chapters in %s "
			"(given %d)" % (chapters,
			self.getBookName(), chapter))
	
def set_vk_verse_checked(self, verse):
	chapter = self.Chapter()
	verses = self.verseCount(
		ord(self.Testament()), 
		ord(self.Book()), 
		chapter
	)
	if 0 < verse <= verses:
		self.Verse(verse)
	else:
		raise VerseParsingError("There are only %d verses in %s %d "
			"(given %d)" % (verses,
			self.getBookName(), chapter, verse))

class VK(SW.VerseKey):#, object):
	"""VK - a wrapper around VerseKey
	
	A VK is a list of consecutive verses. Created like this:

	VK("Genesis 3:5")
	VK(("Genesis 3:5", "Genesis 3:8"))
	
	Modify like this:
	vk.text="Genesis 3:5'
	vk += 1

	>>> from swlib import pysw
	>>> pysw.VK("Genesis 3:5")
	VK('Genesis 3:5')
	>>> pysw.VK(("Genesis 3:5", "Genesis 3:8"))
	VK('Genesis 3:5-Genesis 3:8')
	>>> vk = pysw.VK("Genesis 3:5")
	>>> vk += 1
	>>> vk
	VK('Genesis 3:6')
	>>> vk.text = "Matt 5:3"
	>>> vk
	VK('Matthew 5:3')
	>>> vk = pysw.VK(("Genesis 3:5", "Genesis 3:8"))
	>>> vk == pysw.VerseList("genesis 3:5 - 8")[0]
	True
	>>> vk == None
	False
	>>> vk
	VK('Genesis 3:5-Genesis 3:8')
	>>> for item in vk:
	...     print item
	...     assert item != vk
	...
	Genesis 3:5
	Genesis 3:6
	Genesis 3:7
	Genesis 3:8
	"""

	def __init__(self, key=()):
		if isinstance(key, basestring):
			#if not KeyExists(key):
			#	raise VerseParsingError, key
			SW.VerseKey.__init__(self, to_str(key))
			if self.Error():
				raise VerseParsingError, key
			return
			
		if isinstance(key, SW.Key):
			SW.VerseKey.__init__(self, key)
			return

		if len(key)==2:
			#isinstance(key, tuple):
			top, bottom=key
			if not KeyExists(top):
				raise VerseParsingError, top
		
			if not KeyExists(bottom):
				raise VerseParsingError, bottom

		SW.VerseKey.__init__(self, *key)

	@classproperty
	def books(self): return books

	def __cmp___(self, other): return self.compare(other)
	def __lt__( self, other): return self.compare(other)<0
	def __le__( self, other): return self.compare(other)<1
	def __gt__( self, other): return self.compare(other)>0
	def __ge__( self, other): return self.compare(other)>-1
	def __eq__(self, other):
		if other is None:
			return False

		if self.isBoundSet() != other.isBoundSet():
			return False

		if not self.isBoundSet():
			return self.equals(other)

		return (self.LowerBound().equals(other.LowerBound())
				and self.UpperBound().equals(other.UpperBound()))

	def __ne__(self, other):
		return not self == other

	# TODO: __nonzero__?
	def __str__(self): return to_unicode(self.getRangeText())
	def __repr__(self): return "VK('%s')" % to_unicode(self.getRangeText())

	def __iadd__(self, amount): 
		if amount < 0:
			return self.__isub__(-amount)
		self.increment(amount)
		return self
	
	def __isub__(self, amount):
		self.decrement(amount)
		return self
	
	def get_text(self):
		return self.__str__()
	
	def set_text(self, value):
		if(isinstance(value, basestring)):
			if not KeyExists(value):
				raise VerseParsingError, value
			self.ClearBounds()
				
			self.setText(to_str(value))
		else:
			top, bottom=value
			if not KeyExists(top):
				raise VerseParsingError, top
		
			if not KeyExists(bottom):
				raise VerseParsingError, bottom

			self.ClearBounds()
			self.UpperBound(bottom)
			self.LowerBound(top)
	
	text = property(get_text, set_text)
	
	def set_text_checked(self, value):
		assert isinstance(value, basestring)
		an = self.AutoNormalize(0)
		try:
			self.setText(value)
			check_vk_bounds(self)

		finally:
			self.AutoNormalize(an)

	def __len__(self):
		if self.isBoundSet():
			self.setPosition(TOP)
			length=0
			while not self.Error():
				length+=1
				self+=1
			return length
		#else
		return 1


		if self.isBoundSet():
			#find out number of chapters
			upper=self.UpperBound()
			lower=self.LowerBound()
			if(upper>lower):
				lower, upper = upper, lower
			num=self.UpperBound().NewIndex()-self.LowerBound().NewIndex()+1
			#subtract one for each book, chapter and testament in the middle:
			if(upper.Chapter()==lower.Chapter()):
				return num
			num -= lower.Chapter() - upper.Chapter()
			if(upper.Book()==lower.Book()):
				return num
			if(upper.Testament()==lower.Testament()):
				num-=lower.Book()-upper.Book()
				uc=upper.getChapterCount(upper.Testament(), upper.Book())
				lc=upper.getChapterCount(lower.Testament(), lower.Book())
		return 1

	def __iter__(self):
		#class iterator(object):
		#	def __iter__(self):return self
		#	def next(self):
				
		if(not self.isBoundSet()):
			yield self
			raise StopIteration
		self.setPosition(TOP)
		while not self.Error():
			vk = VK()
			vk.Headings(self.Headings())
			vk.setText(self.getText())
			yield vk

			self+=1

	def __getitem__(self, key):
		if not self.isBoundSet():
			if key == 0 or key == -1:
				return self
			raise IndexError, key
		if key < 0:
			self.setPosition(BOTTOM)
			for a in range(-key-1):
				self-=1
			if self.Error():
				raise IndexError, key
			return VK(self.getText())

		self.setPosition(TOP)
		for a in range(key):
			self+=1#key
		if self.Error():
			raise IndexError, key
		return VK(self.getText())

	def __reduce__(self):
		if self.isBoundSet():
			args = (self.LowerBound().getText(), self.UpperBound().getText())
		else:
			args = self.getText()
		return VK, (args,)
		
	def approxlen(self):
		"""The approximate length of this versekey.
		
		Faster than len. One extra for every chapter, book and testament 
		difference."""
		return self.UpperBound().NewIndex()-self.LowerBound().NewIndex()+1
	
	def _get(self, item):
		vk = VK()
		vk.this = item.this
		return vk

	#def UpperBound(self, to=None):
	#	if to is not None:
	#		return self._get(self.UpperBound(to))
	#	return self._get(self.UpperBound())
	#
	#def UpperBound(self, to=None):
	#	if to is not None:
	#		return self._get(self.UpperBound(to))
	#	return self._get(self.UpperBound())
		
		
	def clone(self): return VK(self)
	def Error(self): 
		return ord(SW.VerseKey.Error(self))
	
	def set_chapter(self, value):
		self.Chapter(value)
	
	def get_chapter(self):
		return self.Chapter()

	chapter = property(get_chapter, set_chapter)
	
	set_chapter_checked = set_vk_chapter_checked
	set_verse_checked = set_vk_verse_checked

		
			
	

	# horrible swig magic...
	__swig_setmethods__	 = {"text":set_text, "chapter":set_chapter}
	__swig_getmethods__	 = {"text":get_text, "chapter":get_chapter}
	for _s in [SW.VerseKey]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
	__setattr__ = lambda self, name, value: SW._swig_setattr(self, VK, name, value)
	__swig_getmethods__ = {}
	for _s in [SW.VerseKey]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
	__getattr__ = lambda self, name: SW._swig_getattr(self, VK, name)
	
	
	
def check_vk_bounds(vk):	
	"""Check that a given VK was in bounds. Autonormalize should be turned off
	before calling this method"""
	#print vk.getText()
	#if vk.isBoundSet():
	#	check_vk_bounds(vk.UpperBound())
	#	check_vk_bounds(vk.LowerBound())
	#	return
		
	testament, book = ord(vk.Testament()), ord(vk.Book())
	chapters = vk.chapterCount(testament, book)
	chapter = vk.Chapter()

	if chapter > chapters:
		raise VerseParsingError("There are only %d chapters in %s "
			"(given %d)" % (
				chapters, vk.bookName(testament, book), chapter
			)
		)

	verse = vk.Verse()
	verses = vk.verseCount(testament, book, chapter)
	
	if verse > verses:
		raise VerseParsingError("There are only %d verses in %s %s "
			"(given %d)" % (
				verses, vk.bookName(testament, book), chapter, verse
			)
		)
	

#	def ParseVerseList(self, range, context="", expand=True):
#		"""Return a VerseList made from the range"""
#		result=SW.VerseKey.ParseVerseList(self, range, context, expand)
#		return VerseList(result)

class VerseList(list): 
	"""A list of VK's

	Construct like this:
	VerseList([VK("Genesis 3:1"), VK("Genesis 3:3")])
	VerseList("3:10-12", "Matthew")
	VerseList(SW.ListKey()) """
	REPLACEMENTS = [
		# Mat. 4v6 -> Mat. 4:6
		(r"""
		(\d) # any digit
		\s*  # some optional whitespace
		v    # the letter v
		\s*  # more optional whitespace 
		(\d) # and then another digit""", r"\1:\2"),

		# Mat. 4 6 -> Mat. 4:6
		(r"""
		(?P<word>(			# match a word without numbers or underscore
			(?=[^\d_])		# following letter is not a digit
			\w				# but is alphanumeric
		)+)
		\s*					# and then possibly whitespace
		(?P<chapter>\d+)	# digits
		\s+					# some whitespace
		(?P<verse>\d+)		# and more digits
		""", "\g<word> \g<chapter>:\g<verse>")
	]
	replacements = [(re.compile(f, flags=re.VERBOSE|re.UNICODE), t) 
						for f, t in REPLACEMENTS]
	

	def __init__(self, args=None, context="", expand=True, raiseError=False):
		converted = False

		if(isinstance(args, (list, tuple))):
			args2 = []
			for a in args:
				if(isinstance(a, SW.VerseKey)):
					args2.append(a)
				else:
					args2.append(VK(a))
			list.__init__(self, args2)
			return

		if isinstance(args, basestring):
			orig_args = args
			for matcher, replacement in self.replacements:
				args = matcher.sub(replacement, args)
			
			args = to_str(args)
			context = to_str(context)
			s = args

			if not raiseError:
				args = vk.ParseVerseList(args, context, expand)

			else:
				an = vk.AutoNormalize(0)
				try:
					args = vk.ParseVerseList(args, context, expand)
					self.TestForError(s, context, orig_args)
				finally:
					vk.AutoNormalize(an)
					

		if(isinstance(args, SW.ListKey)):
			self.RefreshVKs(args, raiseError=raiseError)

		else:
			raise TypeError, `args`
			

		for a in self:
			if a[-1]==VK("rev 22:21"):
				dprint(WARNING, "Possibly incorrect string. Result is", self)


	def TestForError(self, args, context, orig_args):
		"""Check whether a given referencelist looks good
		
		>>> from swlib import pysw
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Matt en 3:15", "5", "Matt en 3:15")
		Traceback (most recent call last):
		  File "<stdin>", line 1, in <module>
		  File "swlib\pysw.py", line 301, in TestForError
		    raise VerseParsingError, "Invalid Reference: %s" % args
		VerseParsingError: Invalid Reference: Matt en 3:15
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Test", "5", "Test")
		Traceback (most recent call last):
		  File "<stdin>", line 1, in <module>
		  File "swlib\pysw.py", line 301, in TestForError
		    raise VerseParsingError, "Invalid Reference: %s" % args
		VerseParsingError: Invalid Reference: Test
		
		
		"""
		# not a very nice way, I'm afraid :(
		# expected osisref: <reference osisRef="Gen.3.5">gen 3:5</reference>
		#<reference osisRef="Gen.3.1-Gen.3.24">gen 3</reference>
		# wrong osisrefs: x
		# <reference osisRef="Gen.3.5-Rev.22.21">gen 3:5 -</reference> foobar'
		my_re = r'\s*(<reference osisRef=[^>]*>[^>]*</reference>((;|,)?\s*))+$'
		osis_ref = VK.convertToOSIS(args, SW.Key(context))
		match = re.match(my_re, osis_ref)
		if not match:
			raise VerseParsingError, "Invalid Reference: %s" % orig_args

	def RefreshVKs(self, lk, raiseError=False):
		"""Turns a listkey into a VerseList"""
		#TODO: error
		l=[]
		#clear list
		del self[:]
		while lk.Error()=='\x00':
			l.append(lk.GetElement(len(l)))
	
		for a in l:
			if(not a):
				continue
			v=SW.VerseKey.castTo(a)
			if not v:
				#1 verse only
				if not raiseError:
					v=VK(a.getText())
				else:
					v = VK()
					v.AutoNormalize(False)
					v.set_text_checked(a.getText())
					v.AutoNormalize(True)
					

			else:
				check_vk_bounds(v)
				v=VK(v)
			self.append(v)
			
	
	def __iadd__(self, amount):
		if(isinstance(amount, VerseList)):
			list.__iadd__(self, amount)
			return self
		if(not isinstance(amount, VK)):
			amount=VK(amount)
		
		list.__iadd__(self, [amount])
		return self
	
	def __add__(self, amount):
		if(isinstance(amount, VerseList)):
			return VerseList(list.__add__(self, amount))
		if(not isinstance(amount, VK)):
			amount=VK(amount)
		return VerseList(list.__add__(self, [amount]))
	
	def keyallowed(self, value):
		if not isinstance(value, VK):
			value=VK(value)
		return value

	def append(self, value): 
		return list.append(self, self.keyallowed(value))

	def __setitem__(self, name, value):
		return list.__setitem__(self, name, self.keyallowed(value))
	
	def getRangeText(self):	
		return "; ".join(item.text for item in self)

	def VerseInRange(self, verse):#, range, context="", vklist=None):
		#if not(vklist): #lastrange and range==lastrange):
		#	vklist=GetVKs(range, context)
		try:
			vk=VK(verse)
		except VerseParsingError, e:
			return False
		for a in self: #vklist:
			if(vk>=a[0] and vk<=a[-1]):
				return True
		return False


	def GetBestRange(self, short=False):#text, context=""):
		"""
		>>> from swlib.pysw import GetBestRange
		>>> GetBestRange("Gen 3:16")
		'Genesis 3:16'
		>>> GetBestRange("Gen 3:3-5")
		'Genesis 3:3-5'
		>>> GetBestRange("Gen 3:16-gen 4:5")
		'Genesis 3:16-4:5'
		>>> GetBestRange("Gen 3-ex5:3")
		'Genesis 3:1-Exodus 5:3'
		>>> GetBestRange("Gen 3-5")
		'Genesis 3-5'
		>>> GetBestRange("Gen 3-matt 5")
		'Genesis 3-Matthew 5'
		>>> GetBestRange("Gen 3:3-5", abbrev=True)
		'Gen 3:3-5'
		>>> GetBestRange("Gen 3-Matt 5", abbrev=True)
		'Gen 3-Matt 5'
		>>> GetBestRange("Psa 58:0-1") # a bit of a dodgy case
		'Psalms 57:11-58:1'
		>>> GetBestRange("Matthew 24v27-30,44")
		'Matthew 24:27-30,44'
		>>> GetBestRange("Matthew 24 27")
		'Matthew 24:27'
		>>> GetBestRange("Matthew 24:27 28")
		'Matthew 24:27,28'
		>>> GetBestRange("Genesis 2 ")
		'Genesis 2'
		>>> GetBestRange("Genesis 2:3 ")
		'Genesis 2:3'
		>>> GetBestRange("Genesis 2 3")
		'Genesis 2:3'
		>>> GetBestRange("Matthew 5:3")
		'Matthew 5:3'
		>>> GetBestRange("Matthew 5")
		'Matthew 5'
		>>> GetBestRange("Genesis 3:5-9, 13-15;17")
		'Genesis 3:5-9,13-15,17'
		>>> GetBestRange("Genesis 3:5,8, 13:15")
		'Genesis 3:5,8;13:15'
		>>> GetBestRange("Gen 3:15-18, 23;Matt 5:3-8")
		'Genesis 3:15-18,23;Matthew 5:3-8'
		>>> GetBestRange("Jude")
		'Jude 1'
		>>> GetBestRange("Mark 15:23")
		'Mark 15:23'
		>>> GetBestRange("Jude 1:5")
		'Jude 1:5'
		>>> GetBestRange("Gen 3:23,24")
		'Genesis 3:23,24'
		>>> GetBestRange("Gen 3:23,24;1,5")
		'Genesis 3:23,24,1,5'
		>>> GetBestRange("Gen 4:5, Exodus 23:1")
		'Genesis 4:5;Exodus 23:1'
		>>> GetBestRange("Gen, Exodus")
		'Genesis 1-50;Exodus 1-40'
		>>> # need Genesis to make it a chapter ref
		... # TODO this could be Genesis 4,5
		... GetBestRange("Gen 4,5") 
		'Genesis 4;Genesis 5'
		>>> # need Genesis to make it a chapter ref	
		... # TODO this might be done as Genesis 4:1, ch 5?
		... # TODO this is interpreted by SWORD as verse 5, not chapter 5
		... GetBestRange("Gen 4:1,Genesis 5")
		'Genesis 4:1,Genesis 5'
		>>> GetBestRange("1 Chr 2:5-2 Chr 3:9")
		'1 Chronicles 2:5-2 Chronicles 3:9'
		>>> GetBestRange("v5")
		'Revelation 1:5'
		>>> GetBestRange("Gen.4.5")
		'Genesis 4:5'
		"""
		
		def getdetails(versekey):
			if short: 
				book = versekey.getBookAbbrev()
			else: 
				book = versekey.getBookName()

			chapter = versekey.Chapter()
			verse = versekey.Verse()

			chapter_verses = versekey.verseCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
				chapter
			)

			return book, chapter, verse, chapter_verses

		#take details of first and last of each VK
		l2 = [[getdetails(vk) for vk in (item[0], item[-1])] for item in self]
				
		# book, chapter, verse
		lastbook, lastchapter, lastverse = None, None, None
		range = ""

		for item in l2:
			((book1, chapter1, verse1, verse_count1), 
			 (book2, chapter2, verse2, verse_count2)) = item

			# check whether we have a chapter range
			# this means that the first verse is verse 1 and the second one is
			# the last in the chapter
			if (verse1, verse2) == (1, verse_count2):
				if not range:
					separator=""
				
				else:
					separator=";"

				range += separator

				if (book1, chapter1) != (book2, chapter2):
					range += "%s %d-" % (book1, chapter1)
				
					if book1 != book2:
						range += "%s %d" % (book2, chapter2)
					else:
						range += "%d" % (chapter2)
					
				else:
					range += "%s %d" % (book2, chapter2)
				
				lastbook, lastchapter, lastverse = book2, chapter2, verse2
				continue
				
					
			for idx, (book, chapter, verse, _) in enumerate(item):
				if (book, chapter, verse) == (lastbook, lastchapter, lastverse):
					break

				# if we don't have a range, no separator
				if not range:
					separator = ""
				
				# if we are the second item in a pair, use a -
				elif idx:
					separator = "-"

				# use comma to separate when in the same chapter				
				elif (book, chapter) == (lastbook, lastchapter):
					separator = ","
				
				else:
					separator = ";"
				
				range += separator

				if book != lastbook:
					range += "%s %d:%d" % (book, chapter, verse)

				elif chapter != lastchapter:
					range += "%d:%d" % (chapter, verse)

				elif verse != lastverse:
					range += "%d" % (verse)

				lastbook, lastchapter, lastverse = book, chapter, verse
			
		return range			

	
	def getListKey(self):
		lk=SW.ListKey()
		#add verses
		map(lk.add, self)
		return lk

	def sorted(self):
		"""Sort the list into Biblical order and returns a new VerseList
		
		>>> from swlib import pysw
		>>> pysw.VerseList("Gen 3:3-5").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5')])
		>>> pysw.VerseList("Gen 3:3-5;Matt 15:10").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		>>> pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10").sorted()
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Jonah 4:5-Micah 1:12'), VK('Matthew 15:10')])
		>>> vl = pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10")
		>>> vl.sorted() is vl
		False
		"""
		lk=self.getListKey()
		lk.sort()
		return VerseList(lk)
	
	def sort(self):
		"""
		>>> from swlib import pysw
		>>> vl = pysw.VerseList("Jonah3:15-23;Gen 3:3-5;Matt 15:10")
		>>> vl
		VerseList([VK('Jonah 4:5-Micah 1:12'), VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		>>> vl.sort()
		>>> vl
		VerseList([VK('Genesis 3:3-Genesis 3:5'), VK('Jonah 4:5-Micah 1:12'), VK('Matthew 15:10')])
		"""
	
		lk=self.getListKey()
		lk.sort()
		self.RefreshVKs(lk)

	def __repr__(self):
		"""
		>>> from swlib import pysw
		>>> vl = pysw.VerseList("Jonah3:1-3;4:5,Gen 3:3-5;Matt 15:10")
		>>> vl
		VerseList([VK('Jonah 3:1-Jonah 3:3'), VK('Jonah 4:5'), VK('Genesis 3:3-Genesis 3:5'), VK('Matthew 15:10')])
		
		"""
	
		return "VerseList([%s])" % ", ".join(map(repr, self))

	def __str__(self): return self.GetBestRange() #Text()

	def clone(self): return VerseList(self)

class BookData(object):
	def __init__(self, bookname, testament, booknumber):
		self.chapters=[]
		self.bookname=bookname
		self.testament=testament
		self.booknumber=booknumber
	
	def __repr__(self):
		return "<BookData: %s>" % self.bookname

	def __str__(self):
		return self.bookname

	def __getitem__(self, item):
		return self.chapters[item]

	def __len__(self):
		return len(self.chapters)
	
	def __iter__(self):
		for item in range(len(self.chapters)):
			yield ChapterData(
				item+1, 
				vk.verseCount(self.testament, self.booknumber, item + 1),
			)

class ChapterData(object):
	"""A class so that we can tell it is chapter data"""
	def __init__(self, chapter_number, chapter_length):
		self.chapter_number = chapter_number
		self.chapter_length = chapter_length

	def __iter__(self):
		return iter(xrange(1, self.chapter_length+1))
	
	def __len__(self):
		return self.chapter_length
	
	def __str__(self):
		return "%s" % self.chapter_number

books = []
vk = VK()
vk.Book(1)

while not vk.Error():
	t = ord(vk.Testament())
	b = ord(vk.Book())
	n = vk.bookName(t, b)
	books.append(BookData(n, t, b))
	vk.Book(ord(vk.Book()) + 1)

for book in books:
	for chapter in range(vk.chapterCount(book.testament, book.booknumber)):
		book.chapters.append(
			ChapterData(chapter+1, 
				vk.verseCount(book.testament, book.booknumber, chapter+1)
			)
		)
del book
del chapter

class TK(SW.TreeKeyIdx):
	"""A tree key. As this is module specific, create it from an existing tree
	key retrieved from the module"""

	def __init__(self, tk, module=None):
		# result of tk.clone() is unowned
		tk2 = SW.TreeKeyIdx.castTo(tk.clone())

		# use the same swig pointer as the other, then kill the other
		self.this = tk2.this
		del tk2

		# we own this now
		self.thisown = True
		
		self.tk = self
		self.module = module
		if module is None and hasattr(tk, "module"):
			self.module = tk.module
		
		assert self.module, "Moduleless tree key :("

	def check_changed(self):
		pass

	def __iter__(self):
		self.check_changed()
		cls = type(self)
		tk = cls(self.tk)
		if(tk.firstChild()):
			yield cls(tk)
			while(tk.nextSibling()):
				yield cls(tk)

	def __repr__(self):
		self.check_changed()
	
		return "<%s(%s)>" % (type(self).__name__, 
			to_unicode(self.getText(), self.module))
	
	def __str__(self):
		self.check_changed()
	
		return to_unicode(self.getLocalName(), self.module)
	
	def __getitem__(self, key):
		self.check_changed()
	
		return [a for a in self][key]

	def breadcrumb(self, include_home=None, delimiter=" > "):
		self.check_changed()
	
		breadcrumb = [unicode(self)]
		bref = TK(self)
		while bref.parent():
			breadcrumb.append(unicode(bref))

		if include_home:
			breadcrumb[-1] = include_home
		else:
			del breadcrumb[-1]

		return delimiter.join(breadcrumb[::-1])
	
	def get_text(self):
		self.check_changed()
	
		return to_unicode(self.getText(), self.module)

	def set_text(self, value):
		self.setText(to_str(value, self.module))
	
	# horrible swig magic...
	__swig_setmethods__	 = {"text":set_text}
	__swig_getmethods__	 = {"text":get_text}
	for _s in [SW.TreeKeyIdx]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
	__setattr__ = lambda self, name, value: SW._swig_setattr(self, TK, name, value)
	__swig_getmethods__ = {}
	for _s in [SW.TreeKeyIdx]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
	__getattr__ = lambda self, name: SW._swig_getattr(self, TK, name)
	
	text = property(get_text, set_text)


class ImmutableTK(TK):
	"""A TK which is immutable - it can't/shouldn't be changed.

	Don't assign this to a module permanently - i.e. with Persist turned on,
	or it may be changed by something moving the module position.

	This will raise errors if it detects a change."""
	def __init__(self, *args, **kwargs):
		super(ImmutableTK, self).__init__(*args, **kwargs)
		self.immutable = self.getText()

	def check_changed(self):
		if self.immutable != self.getText():
			raise TypeError, "Detected mutating ImmutableTK"

	def error(self, *args, **kwargs):
		raise TypeError, "This is immutable"
	
	increment = setText = set_text = root = error

# -- Utility functions
def GetVerseTuple(string, context=""):
	#TODO check valid
	text = vk.ParseVerseList(to_str(string), to_str(context), True).getText()
	# Normalize result
	vk.setText(text)
	return (vk.NewIndex(), vk.getText())
	
def GetVerseStr(verse, context = "", raiseError=False):
	"""Returns a standardized verse string"""
	if not verse:
		if raiseError:
			raise VerseParsingError, "Invalid empty reference"
			
		return ""
		#assert verse

	# Parse List (This is for context)
	verse_split = verse.split(";")[0].split(",")[0]

	vklist = VerseList(verse_split, context, expand=False,
		raiseError=raiseError)
	if not vklist: 
		if raiseError:
			raise VerseParsingError, u"Invalid Reference: %s" % verse
		else:
			return ""
	
	vk = vklist[0]
	#text = vk.ParseVerseList(str(string), context, True).getText()
	# Normalize result
	#vk.setText(text)
	return vk[0].text

def GetBookChapter(string, context = ""):
	chapter = vk.ParseVerseList(to_str(string), to_str(context), True).getText()
	index = chapter.find(":")
	
	if index != -1:
		chapter = chapter[:index]
	return chapter
	

def BookName(text):
	vk.setText(to_str(text))
	if vk.Error(): return None
	return vk.getBookName()

def GetVKs(range, context=""):
	lk=vk.ParseVerseList(to_str(range), to_str(context), True)
	l=[]
	l2=[]
	while lk.Error()=='\x00':
		l.append(lk.GetElement(len(l)))

	for key in l:
		if not key:
			continue
		
		vk = VK.castTo(key)

		if not vk:
			#1 verse only
			v=[VK(key.getText())]
		else:
			#range
			v=[VK(vk.LowerBound()), VK(vk.UpperBound())]

		l2.append(v)

	return l2


def GetBestRange(text, context="", abbrev=False, raiseError=False):
	vl = VerseList(text, context=context, raiseError=raiseError)
	return vl.GetBestRange(abbrev)

#Matt 17:21, 19:21-20:16 21:12-17
#vklist=[]
#lastrange=""
def VerseInRange(verse, range, context="", vklist=None):
	if not(vklist):#lastrange and range==lastrange):
		vklist=GetVKs(range, context)
	vk=VK(verse)
	for a in vklist:
		if(len(a)==1):
			if(vk.equals(a[0])): return True
		elif(vk.compare(a[0])>-1 and vk.compare(a[1])<1):	
			return True 
	return False

class Searcher(SW.Searcher):
	def __init__(self, book, userdata = None):
		SW.Searcher.__init__(self, book.mod)
		self.mod = book.mod
		self.callback = None
		self.userdata = userdata
		self.vk = VK()
		self.vk.thisown = False

	def PercentFunction(self, number):
		if(self.callback):
			continuing = self.callback(number, self.userdata)
			if not continuing:
				self.TerminateSearch()
	
	def Search(self, string, options=0, scopestr=None, case_sensitive=False):
		self.mod.setKey(self.vk)

		scope = None
		if(scopestr):
			# TODO: this is VerseKey specific
			scope = self.vk.ParseVerseList(to_str(scopestr), "", True)

		verseslist = self.doSearch(string, options, 
			(not case_sensitive)*REG_ICASE, scope)

		strings = verseslist.getRangeText()

		if not strings: 
			return []
		
		# TODO: ;'s don't cut it - in the ISBE, they are often used		
		return strings.split("; ")


