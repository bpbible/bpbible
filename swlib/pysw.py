import Sword as SW
import os
import re
import sys
import string
from util.debug import *
from util.unicode import to_str, to_unicode
from util import classproperty
from util.observerlist import ObserverList

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

LIB_1512_COMPAT = SW.Version().currentVersion > SW.Version("1.5.11")
SW_HAS_MDB = hasattr(SW.Mgr, "loadMDBDir")
print "SVN; SWORD 1.5.12 compatible" if LIB_1512_COMPAT else "1.5.11 compatible"

locale_dir = "locales/locales.d" + ("/SWORD_1512" if LIB_1512_COMPAT else "")

# Check if we are ICU - bindings don't generate static getter here, so we can
# use the underlying getter
isICU = SW._Sword.SWMgr_isICU_get()
if isICU or hasattr(sys, "SW_dont_do_stringmgr"):
	if isICU: 
		have_set_locale_dir = False
	else:
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
	have_set_locale_dir = False
	try:
		### TODO: remove this pre-1.6.0 hack sometime
		SW.StringMgr.setSystemStringMgr(m, locale_dir)
		have_set_locale_dir = True
	except TypeError, e:
		#if LIB_1512_COMPAT:
		#	print "Don't we have those patches???", e

		SW.StringMgr.setSystemStringMgr(m)
	
# *only* after we've set the system string mgr can we set the system 
# locale mgr...
if not have_set_locale_dir:
	locale_mgr = SW.LocaleMgr(locale_dir)
	locale_mgr.thisown = False
	SW.LocaleMgr.setSystemLocaleMgr(locale_mgr)
	have_set_locale_dir = True

#if locale_mgr.getLocale("bpbible"):
#	locale_mgr.setDefaultLocaleName("bpbible")
#else:
#	dprint(WARNING, "bpbible locale not found")
try:
	vk = SW.VerseKey()
	vk.ParseVerseList("", "", False, False)
	LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS = True
	
except (TypeError, NotImplementedError), e:
	if LIB_1512_COMPAT:
		print "Extended ParseVerseList not supported???", e
	LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS = False
		
del vk


class VerseParsingError(Exception): 
	def __str__(self):
		return self.message

def KeyExists(key_text, base_key=None):
	if base_key is None:
		base_key = u_vk
	
	SW.VerseKey.setText(base_key, key_text.encode(base_key.encoding))
	return not base_key.Error()

def set_vk_chapter_checked(self, chapter):
	chapters = self.chapterCount(ord(self.Testament()), ord(self.Book()))
	if 0 < chapter <= chapters:
		self.Chapter(chapter)
	else:
		raise VerseParsingError(process_digits(
			_("There are only %(chapters)d chapters "
			"in %(book)s (given %(given)d)") % dict(
				chapters=chapters, book=self.getBookName(), 
				given=chapter
			), userOutput=True)
		)
	
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
		raise VerseParsingError(process_digits(
			_("There are only %(verses)d verses in "
			"%(book)s %(chapter)s (given %(given)d)") % dict(
				verses=verses, book=self.getBookName(),
				chapter=chapter, given=verse
			), userOutput=True)
		)

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

	encoding = "ascii"
	def __init__(self, key=(), raiseError=True, headings=False):
		assert isinstance(raiseError, bool), "raiseError wasn't bool"
		if headings:
			SW.VerseKey.__init__(self)
			self.Headings(1)
			
			if isinstance(key, str):
				self.text = key

			elif isinstance(key, tuple):
				min, max = key
				tmp_lk = self.ParseVerseList(min)
				if tmp_lk.Count():
					k = tmp_lk.GetElement(0)
					vk = SW.VerseKey.castTo(k)
					if not vk:
						print "WARNING: not vk"
						self.LowerBound(k.getText())
					else:
						self.LowerBound_VK(vk)

				tmp_lk = self.ParseVerseList(max, min, True)
				if tmp_lk.Count():
					k = tmp_lk.GetElement(0)					
					vk = SW.VerseKey.castTo(k)
					if not vk:
						print "WARNING: not vk"
						self.UpperBound(k.getText())
						
					else:
						if vk.isBoundSet():
							self.UpperBound_VK(vk.UpperBound())
						else:
							self.UpperBound_VK(vk)

				self.setPosition(TOP)
				
			else:
				assert isinstance(key, SW.VerseKey)
				self.copyFrom(key)
			return

		if isinstance(key, basestring):
			#if not KeyExists(key):
			#	raise VerseParsingError, key
			#print key
			SW.VerseKey.__init__(self, key.encode(self.encoding))
			#print "TESTING", key
			if raiseError and self.Error():
				#print "RAISING ERROR"
				raise VerseParsingError, key
			return
			
		if isinstance(key, SW.Key):
			SW.VerseKey.__init__(self, key)
			
			return

		if len(key)==2:
			#isinstance(key, tuple):
			top, bottom=key
			if raiseError:
				if not KeyExists(top):
					raise VerseParsingError, top
				if not KeyExists(bottom):
					raise VerseParsingError, bottom

		SW.VerseKey.__init__(self, *key)

	@classproperty
	def books(cls): return books

	@property
	def v_books(self):
		if LIB_1512_COMPAT:
			v11n = self.getVersificationSystem()
			return get_books(v11n)[0]

		return localized_books	

	def __cmp__(self, other): return self.compare(other)
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
	def __repr__(self): return "%s('%s')" % (self.__class__.__name__, to_unicode(self.getRangeText()))

	def __iadd__(self, amount): 
		if amount < 0:
			return self.__isub__(-amount)
		self.increment(amount)
		return self
	
	def __isub__(self, amount):
		self.decrement(amount)
		return self
	
	if not LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS:
		def ParseVerseList(self, a, b="", c=False, d=False):
			return SW.VerseKey.ParseVerseList(self, a, b, c)
				

	def get_text(self):
		return self.__str__()
	
	def set_text(self, value, raiseError=True):
		if(isinstance(value, basestring)):
			self.ClearBounds()

			if raiseError and not KeyExists(value, self):
				raise VerseParsingError, value
				
			self.setText(value.encode(self.encoding))
		else:
			self.ClearBounds()
			
			top, bottom = value
			if raiseError:
				if not KeyExists(top, self):
					raise VerseParsingError, top
		
				if not KeyExists(bottom, self):
					raise VerseParsingError, bottom

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
				uc=upper.chapterCount(upper.Testament(), upper.Book())
				lc=upper.chapterCount(lower.Testament(), lower.Book())
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
			vk.setText(SW.VerseKey.getText(self))
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
			return self.__class__(self.getText())

		self.setPosition(TOP)
		for a in range(key):
			self+=1#key
		if self.Error():
			raise IndexError, key
		return self.__class__(self.getText())

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

	UpperBound_VK = SW.VerseKey.UpperBound
	LowerBound_VK = SW.VerseKey.LowerBound

	def LowerBound_VK_1511(self, key):
		SW.VerseKey.LowerBound(self, key.getText())

	def UpperBound_VK_1511(self, key):
		SW.VerseKey.UpperBound(self, key.getText())

	def UpperBound_1512(self, to=None):
		if to is None:
			return VK(super(VK, self).UpperBound())
		
		super(VK, self).UpperBound(SW.VerseKey(to))
		
	def LowerBound_1512(self, to=None):
		if to is None:
			return VK(super(VK, self).LowerBound())
		
		super(VK, self).LowerBound(SW.VerseKey(to))
	
	if LIB_1512_COMPAT:
		LowerBound = LowerBound_1512
		UpperBound = UpperBound_1512
	else:
		LowerBound_VK = LowerBound_VK_1511
		UpperBound_VK = UpperBound_VK_1511
		
		
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
		if value != 0 or self.Headings() == '\x01':
			self.Chapter(value)
			return

		b = ord(self.Book())-1
		t = ord(self.Testament())
		if b == 0 and t >= 1:
			self.Testament(t-1)
			b = self.bookCount(t-1)

		self.Book(b)

		err = self.Error()
		if err: 
			# do it again to set the error
			self.Book(b)
			return

		self.Chapter(self.chapterCount(ord(self.Testament()), b))
	
	def get_chapter(self):
		return self.Chapter()

	chapter = property(get_chapter, set_chapter)
	
	set_chapter_checked = set_vk_chapter_checked
	set_verse_checked = set_vk_verse_checked
	
	def chapter_str(self):
		return str(self.Chapter())

	def get_book_chapter(self):
		return u"%s %s" % (self.getBookName(), self.chapter_str())

	# horrible swig magic...
	__swig_setmethods__	 = {"text":set_text, "chapter":set_chapter}
	__swig_getmethods__	 = {"text":get_text, "chapter":get_chapter}
	for _s in [SW.VerseKey]: __swig_setmethods__.update(getattr(_s,'__swig_setmethods__',{}))
	__setattr__ = lambda self, name, value: SW._swig_setattr(self, VK, name, value)
	__swig_getmethods__ = {}
	for _s in [SW.VerseKey]: __swig_getmethods__.update(getattr(_s,'__swig_getmethods__',{}))
	__getattr__ = lambda self, name: SW._swig_getattr(self, VK, name)

class EncodedVK(VK):

	def getInternalVK(self):
		return VK(self)

	def getBookAbbrev(self):
		return super(EncodedVK, self).getBookAbbrev().decode(self.encoding)
	
	def getBookName(self):
		return super(EncodedVK, self).getBookName().decode(self.encoding)

	def LowerBound(self, text=None):
		if text is None:
			return super(EncodedVK, self).LowerBound()

		super(EncodedVK, self).LowerBound(text.encode(self.encoding))
	
	def UpperBound(self, text=None):
		if text is None:
			return super(EncodedVK, self).UpperBound()

		super(EncodedVK, self).UpperBound(text.encode(self.encoding))
	
	def getText(self):
		return super(EncodedVK, self).getText().decode(self.encoding)
	
	def getRangeText(self):
		return super(EncodedVK, self).getRangeText().decode(self.encoding)
		
		
class LocalizedVK(EncodedVK):
	def chapter_str(self):
		return process_digits(str(self.Chapter()), userOutput=True)
	
	def get_book_chapter(self):
		if LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS:
			if self.getChapterMax() == 1:
				return u"%s" % (self.getBookName())

		return super(LocalizedVK, self).get_book_chapter()

	def getText(self):
		if LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS:
			if self.getChapterMax() == 1:
				return u"%s %d" % (self.getBookName(), 
					process_digits(
						self.Verse(),
						userOutput=True
					))

		return process_digits(
			u"%s %d:%d" % (self.getBookName(), 
				self.Chapter(),
				self.Verse(),
			),
				userOutput=True
			)
		
class UserVK(LocalizedVK):
	def __init__(self, arg=None, locale=None):
		if isinstance(arg, SW.Key):
			super(UserVK, self).__init__(arg)
			arg = None

		else:
			super(UserVK, self).__init__()

		if locale is None:
			locale = locale_lang
		self.setLocale(locale)
		self.encoding = locale_encoding
		
		if arg is not None:
			self.set_text(arg)

	def getBookAbbrev(self):
		return AbbrevVK(self).getBookName()#.decode(self.encoding)	
	
	def getBookName(self):
		return process_dash_hack(
			super(UserVK, self).getBookName(), locale_dash_hack
		)
		
		
	def getRangeText(self):
		print "Warning - don't use getRangeText here"
		return process_dash_hack(
			super(UserVK, self).getRangeText(), locale_dash_hack
		)
	
	def __str__(self): return self.getRangeText()
	def __repr__(self): 
		return u"%s(%s)" % (
			unicode(self.__class__.__name__), 
			repr(self.getRangeText())
		)
	
		
	
	@classproperty
	def books(cls): 
		return localized_books

	@property
	def v_books(self):
		if LIB_1512_COMPAT:
			v11n = self.getVersificationSystem()
			return get_books(v11n)[1]

		return localized_books

class BPBibleLocaleVK(UserVK):
	def __init__(self, arg=None):
		super(BPBibleLocaleVK, self).__init__(arg, locale="bpbible")

class AbbrevVK(LocalizedVK):
	def __init__(self, arg=None):
		if isinstance(arg, SW.Key):
			super(AbbrevVK, self).__init__(arg)
			arg = None

		else:
			super(AbbrevVK, self).__init__()

		self.setLocale(abbrev_locale_lang)
		self.encoding = abbrev_locale_encoding
		
		if arg is not None:
			self.set_text(arg)

	def getBookName(self):
		return process_dash_hack(
			super(AbbrevVK, self).getBookName(), abbrev_locale_dash_hack
		)
	
	def getRangeText(self):
		return process_dash_hack(
			super(AbbrevVK, self).getRangeText(), abbrev_locale_dash_hack
		)
		
		

def check_vk_bounds(vk):	
	"""Check that a given VK was in bounds. Autonormalize should be turned off
	before calling this method"""
	#if vk.isBoundSet():
	#	check_vk_bounds(vk.UpperBound())
	#	check_vk_bounds(vk.LowerBound())
	#	return
		
	testament, book = ord(vk.Testament()), ord(vk.Book())
	chapters = vk.chapterCount(testament, book)
	chapter = vk.Chapter()

	if chapter > chapters:
		raise VerseParsingError(process_digits(
			_("There are only %(chapters)d chapters "
			"in %(book)s (given %(given)d)") % dict(
				chapters=chapters, book=vk.getBookName(), given=chapter
			), userOutput=True)
		)

	verse = vk.Verse()
	verses = vk.verseCount(testament, book, chapter)
	
	if verse > verses:
		raise VerseParsingError(process_digits(
			_("There are only %(verses)d verses in "
			"%(book)s %(chapter)s (given %(given)d)") % dict(
				verses=verses, book=vk.getBookName(), 
				chapter=chapter, given=verse
			), userOutput=True)
		)
	

#	def ParseVerseList(self, range, context="", expand=True):
#		"""Return a VerseList made from the range"""
#		result=SW.VerseKey.ParseVerseList(self, range, context, expand)
#		return VerseList(result)

rev_22_21 = VK("rev 22:21")
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
		""", "\g<word> \g<chapter>:\g<verse>"),
		
		# Matt 4: 6 -> Matt 4:6
		(r":\s+", ":"),

		# Hakim-Hakim 3:5-9 -> HakimHakim
		(r"""
		([^\s\d:.,;])
		-
		([^\s\d:.,;])""", r"\1\2"),
	]
	replacements = [(re.compile(f, flags=re.VERBOSE|re.UNICODE), t) 
						for f, t in REPLACEMENTS]
	

	def __init__(self, args=None, context="", expand=True, raiseError=False,
				userInput=False, headings=False, use_bpbible_locale=False):
		converted = False

		if(isinstance(args, (list, tuple))):
			assert not userInput
			args2 = []
			for a in args:
				if(isinstance(a, SW.VerseKey)):
					args2.append(a)
				else:
					args2.append(VK(a))
			list.__init__(self, args2)
			return

		locale_changed = False
		if isinstance(args, basestring):
			orig_args = args
			if userInput:
				for matcher, replacement in self.replacements:
					args = matcher.sub(replacement, args)

				args = process_digits(args, userInput=True)
			
			args = to_str(args)
			context = to_str(context)
			s = args

			if use_bpbible_locale:
				vk = b_vk
				locale = "bpbible"

			elif userInput:
				vk = u_vk
				locale = locale_lang
				
			else:
				vk = i_vk
				locale = locale_mgr.getDefaultLocaleName()

			old_headings = vk.Headings(headings)

			try:
	
				# make sure we have this set correctly
				# TestForError uses this, 
				# as does ParseVerseList with expand on
				old = locale_mgr.getDefaultLocaleName()
				if old != locale:
					locale_mgr.setDefaultLocaleName(locale)
					locale_changed = True
				
				if not raiseError:
					args = vk.ParseVerseList(args, context, expand, userInput)

				else:
					an = vk.AutoNormalize(0)
					try:
						args = vk.ParseVerseList(args, context, expand, userInput)
						self.TestForError(s, context, orig_args)
					finally:
						vk.AutoNormalize(an)

			finally:
				vk.Headings(old_headings)

				if locale_changed:
					if old != locale:
						locale_mgr.setDefaultLocaleName(old)
						

		if(isinstance(args, SW.ListKey)):
			self.RefreshVKs(args, raiseError=raiseError, userInput=userInput,
				headings=headings)

		else:
			raise TypeError, `args`

		for a in self:
			if a[-1]== rev_22_21:
				#dprint(WARNING, "Possibly incorrect string. Result is", self)
				pass


	def TestForError(self, args, context, orig_args):
		"""Check whether a given referencelist looks good.
		The default locale must be the locale for this VerseList
		
		>>> from swlib import pysw
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> pysw.VerseList("Gen 3:3-5").TestForError("Gen 3:15", "3", "Gen 3:15")
		>>> import __builtin__
		>>> __builtin__._ = lambda x: x # don't let it smash _ - we need it
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
			raise VerseParsingError(_(u"Invalid Reference: %s") % orig_args)

	def RefreshVKs(self, lk, raiseError=False,userInput=False, headings=True):
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
			if not v or not v.isBoundSet():
				#print "HERE"
				#1 verse only
				key = get_a_key(userInput)
				
				if headings:
					old = key.Headings(1)


				t = a.getText()
				#print t, `key.Headings()`
				if "-" in t:
					t = t.replace("-", "")

				if not raiseError:
					key.set_text(t.decode(key.encoding), raiseError=False)
				else:
					key.AutoNormalize(False)
					key.set_text_checked(t)
					key.AutoNormalize(True)

				v = VK(key, raiseError=False, headings=headings)
				v.setLocale("en_US")
				
				if headings:
					key.Headings(old)
					

			else:
				if raiseError:
					check_vk_bounds(v)

				if userInput:
					v.setLocale("en_US")
					low = v.LowerBound()
					
					# bug in SWORD svn, call above for v should have set this
					low.setLocale("en_US")
					low_text = low.getText()

					up = v.UpperBound()
					up_text = up.getText()
					
					# we need to do this carefully
					# if we just copy across the bounds get mussed when they
					# have dashes. We don't want this happening, so set the
					# bounds separately.
					# Use VerseKey's getText so we don't worry about unicode
					v = VK((low_text, up_text), raiseError=False)
				
				else:
					# if we stay inside, just use a straight copy
					v = VK(v, raiseError=False)
					
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


	def GetBestRange(self, short=False, userOutput=False):#text, context=""):
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
		... # TODO: is this correct? 
		... #should we need headings on for this to work?
		'Psalms 58:0-1'
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
		>>> GetBestRange("Jude 5")
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
		>>> GetBestRange("1 Chr 2:5-2 Chr 3:9", userOutput=True)
		u'1 Chronicles 2:5-2 Chronicles 3:9'
		>>> GetBestRange("1 Chr 2:5-2 Chr 3:9")
		'I Chronicles 2:5-II Chronicles 3:9'
		>>> GetBestRange("v5", userOutput=True)
		u'Revelation 1:5'
		>>> GetBestRange("Gen.4.5")
		'Genesis 4:5'
		"""

		single_chapter_books = LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS and userOutput
		
		def getdetails(versekey):
			if userOutput:
				# translate twice so that we get our -'s in
				# the first translate puts it into user locale
				# the second translate puts dashes in
				if short:
					book = abbrev_locale.translate(
						abbrev_locale.translate(
							versekey.getBookName()
						)
					).decode(abbrev_locale_encoding)
				else:
					book = locale.translate(
						locale.translate(
							versekey.getBookName()
						)
					).decode(locale_encoding)
			else:
				if short: 
					book = versekey.getBookAbbrev()
				else: 
					book = versekey.getBookName()

			chapter = versekey.Chapter()
			verse = versekey.Verse()
			userChapter, userVerse = str(chapter), str(verse)

			if userOutput:
				userChapter = process_digits(userChapter, userOutput=True)
				userVerse = process_digits(userVerse, userOutput=True)
			

			chapter_verses = versekey.verseCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
				chapter
			)
			
			book_chapters = versekey.chapterCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
			)

			return book, chapter, verse, chapter_verses, book_chapters, userChapter, userVerse

		def get_bounds_details(vk):
			if vk.isBoundSet():
				return getdetails(vk.LowerBound()), getdetails(vk.UpperBound())

			d = getdetails(vk)
			return d, d

		# book, chapter, verse
		lastbook, lastchapter, lastverse = None, None, None
		range = ""

		for vk in self:
			item = get_bounds_details(vk)
			# take details of first and last for each VK
			((book1, chapter1, verse1, verse_count1, chapter_count1, uc1, uv1), 
			 (book2, chapter2, verse2, verse_count2, chapter_count2, uc2, uv2)) = item

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
					if single_chapter_books and chapter_count1 == 1:
						range += "%s-" % book1
					else:
						range += "%s %s-" % (book1, uc1)
				
					if book1 != book2:
						if single_chapter_books and chapter_count2 == 1:
							range += "%s" % book2
						else:
							range += "%s %s" % (book2, uc2)
					else:
						range += "%s" % (uc2)
					
				else:
					if single_chapter_books and chapter_count2 == 1:
						range += "%s" % book2
					else:
						range += "%s %s" % (book2, uc2)
				
				lastbook, lastchapter, lastverse = book2, chapter2, verse2
				continue
				
					
			for idx, (book, chapter, verse, _, chapters, uc, uv) in enumerate(item):
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

				done = False
				if single_chapter_books and chapters == 1:
					if book != lastbook:
						range += "%s %s" % (book, uv)
						done = True

					assert chapter == 1 and (done or lastchapter in (1, None)), \
						"Changed chapter but not book when only one chapter?!?"

					if not done:
						range += "%s" % uv
						done = True

				elif book != lastbook:
					range += "%s %s:%s" % (book, uc, uv)

				elif chapter != lastchapter:
					range += "%s:%s" % (uc, uv)

				else: # verse != lastverse:
					range += "%s" % (uv)

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
	
		return u"VerseList([%s])" % u", ".join(repr(item) for item in self)

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
	
	#@property
	#def ChapterData(self):
	#	return ChapterData
	
	def __iter__(self):
		for item in range(len(self.chapters)):
			yield ChapterData(
				item+1, 
				i_vk.verseCount(self.testament, self.booknumber, item + 1),
			)

class LocalizedBookData(BookData):
	def __str__(self):
		return process_dash_hack(
			locale.translate(self.bookname).decode(locale_encoding), 
			locale_dash_hack
		)
	
	def __iter__(self):
		if LIB_SUPPORTS_SINGLE_CHAPTER_BOOKS and len(self.chapters) == 1:
			l = LocalizedChapterData(
				1, 
				i_vk.verseCount(self.testament, self.booknumber, 1),
			)

			for a in l:
				yield a
			
			return
		
			
		for item in range(len(self.chapters)):
			yield LocalizedChapterData(
				item+1, 
				i_vk.verseCount(self.testament, self.booknumber, item + 1),
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

class LocalizedChapterData(ChapterData):
	def __str__(self):
		return process_digits(str(self.chapter_number), userOutput=True)

	def __iter__(self):
		for a in xrange(1, self.chapter_length+1):
			yield process_digits(str(a), userOutput=True)


def get_books(v11n):
	if v11n in v11n_books:
		return v11n_books[v11n]

	books = []
	localized_books = []

	vk = VK()
	if LIB_1512_COMPAT:
		vk.setVersificationSystem(v11n)

	vk.Book(1)

	while not vk.Error():
		t = ord(vk.Testament())
		b = ord(vk.Book())
		n = vk.getBookName()
		books.append(BookData(n, t, b))
		localized_books.append(LocalizedBookData(n, t, b))
		
		vk.Book(ord(vk.Book()) + 1)
	
	for book, localized_book in zip(books, localized_books):
		for chapter in range(vk.chapterCount(book.testament, book.booknumber)):
			c = ChapterData(chapter+1, 
					vk.verseCount(book.testament, book.booknumber, chapter+1)
			)
	
			book.chapters.append(c)
			localized_book.chapters.append(c)
	
	v11n_books[v11n] = books, localized_books
	return v11n_books[v11n]

i_vk = VK()
v11n_books = {}
books, localized_books = get_books("KJV")

SW.abbrev.__len__ = SW.abbrev.getAbbrevCount
SW.abbrev.__getitem__ = SW.abbrev.getAbbrevData
SW.abbrev.__cmp__ = lambda a, b: cmp(a.ab, b)

def find_bookidx(name):
	if not name: return None
	import bisect
	name = name.replace("-", "").upper().strip().encode(locale_encoding)
	abbrevs = locale.getBookAbbrevs()
	d = bisect.bisect_left(abbrevs, name)
	while d < len(abbrevs) and abbrevs[d].ab.startswith(name):
		if LIB_1512_COMPAT:
			# if the locale has additional versification translations, move
			# along until we find a good one
			e = i_vk.getBookNumberByOSISName(abbrevs[d].osis)
			if e != -1:
				return e - 1
			
			d += 1
		else:
			return abbrevs[d].book - 1
	
	return None
	

locale_changed = ObserverList()

def get_dash_hack(locale):
	lookup = {}
	for testament in range(2):#locale.getNumBookGroupings()):
		for book in range(i_vk.bookCount(testament)):
			book_name = locale.translate(i_vk.bookName(testament, book))
			with_dash = locale.translate(book_name).decode(locale_encoding)
			if with_dash != book_name.decode(locale_encoding):
				lookup[book_name.decode(locale_encoding)] = with_dash
	
	return lookup
		
def get_locale(lang, additional=None):
	locale = locale_mgr.getLocale(lang)
	if not locale:
		locale = SW.Locale("")
	
	if additional:
		locale.augment(additional)

	if not locale.getName() or locale.getName() == "en_US":
		return False, SW.Locale(""), "UTF-8"
	
	assert locale.getEncoding() == "UTF-8", "Only UTF-8 locales supported"
	return True, locale, locale.getEncoding()

def change_locale(lang, abbrev_lang, additional=None):
	global locale, locale_lang, locale_encoding, locale_dash_hack
	global abbrev_locale, abbrev_locale_lang, abbrev_locale_encoding
	global abbrev_locale_dash_hack
	global locale_digits
	locale_lang = lang	
	worked, locale, locale_encoding = get_locale(lang, additional=additional)
	locale_digits = None
	if not worked:
		dprint(WARNING, "Couldn't find locale %r" % lang,
		[x.c_str() for x in locale_mgr.getAvailableLocales()])
		locale_dash_hack = {}
	
	else:
		assert locale_encoding, dir(locale)
		locale_dash_hack = get_dash_hack(locale)
		digits = locale.translate(string.digits).decode(locale_encoding)
		if digits != string.digits:
			assert len(digits) == 10, "digits string wasn't 10 digits long"
			internal_to_external = dict(zip(string.digits, digits))
			external_to_internal = dict(zip(digits, string.digits))
			def make_replacer(mapping):
				matcher = re.compile("[%s]" % ''.join(mapping.keys()))
				def replace_digit(match):
					return mapping[match.group(0)]

				def replace(s):
					return matcher.sub(replace_digit, s)

				return replace

			locale_digits = dict(
				internal_to_external=make_replacer(internal_to_external),
				external_to_internal=make_replacer(external_to_internal),
				digits=digits,
			)
	
	w, abbrev_locale, abbrev_locale_encoding = get_locale(abbrev_lang)
	if w:
		abbrev_locale_lang = abbrev_lang
		abbrev_locale_dash_hack = get_dash_hack(abbrev_locale)
	
	else:
		dprint(WARNING, "Couldn't find abbreviation locale %r" % abbrev_lang,
		[x.c_str() for x in locale_mgr.getAvailableLocales()])
		abbrev_locale_lang = locale_lang
		abbrev_locale_dash_hack = {}
		abbrev_locale = locale
		abbrev_locale_encoding = locale_encoding
		
	locale_changed(locale, lang, abbrev_locale, abbrev_lang)

change_locale("bpbible", "abbr")

u_vk = UserVK()
b_vk = BPBibleLocaleVK()
a_vk = AbbrevVK()


def change_vk_locale(locale, lang, abbrev_locale, abbrev_lang):
	if locale:
		u_vk.setLocale(lang)
		u_vk.encoding = locale_encoding

	if abbrev_locale:
		a_vk.setLocale(abbrev_lang)
		a_vk.encoding = abbrev_locale_encoding

locale_changed += change_vk_locale

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
		tk = TK(self.tk)
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
			raise TypeError(
				"Detected mutating ImmutableTK (from %r to %r)" %
				(self.immutable, self.getText()))

	def error(self, *args, **kwargs):
		raise TypeError, "This is immutable"
	
	def Persist(self, value=None):
		assert value is None, "Don't change this key's persist"
		return super(ImmutableTK, self).Persist()
	increment = setText = set_text = root = firstChild = error
	nextSibling = previousSibling = parent = error
	Index = error
	__delattr__ = error
	__iadd__ = error
	__isub__ = error
	append = error
	appendChild = assureKeyPath = castTo = error
	clearBound = copyFrom = create = decrement = error
	firstChild = error
	increment = insertBefore = error
	nextSibling = parent = previousSibling = remove = root = save = error
	setLocalName = setOffset = setPosition = setText = setUserData = error
	set_text = error
	

# -- Utility functions
def GetVerseStr(verse, context = "", raiseError=False, 
	userInput=False, userOutput=False):
	"""Returns a standardized verse string"""
	if not verse:
		if raiseError:
			raise VerseParsingError, _("Invalid empty reference")
			
		return ""
		#assert verse

	# Parse List (This is for context)
	verse_split = verse.split(";")[0].split(",")[0]

	vklist = VerseList(verse_split, context, expand=False,
		raiseError=raiseError, userInput=userInput)
	if not vklist: 
		if raiseError:
			raise VerseParsingError, _(u"Invalid Reference: %s") % verse

		else:
			return ""
	
	vk = vklist[0]

	if userInput != userOutput:
		assert userInput
		return VK(vk[0]).text
		
	return vk[0].text

def process_digits(text, userInput=False, userOutput=False):
	assert userInput ^ userOutput, "Specify one of userInput and userOutput"
	if not locale_digits:
		return text

	if userInput:
		return locale_digits["external_to_internal"](text)
	else:		
		return locale_digits["internal_to_external"](text)

		
def process_dash_hack(text, lookup):
	text = process_digits(text, userOutput=True)
	for item, value in lookup.items():
		text = text.replace(item, value)
	
	return text
		
def abbrev_to_user(key):
	return VK(key).text

def internal_to_user(key):
	return UserVK(VK(key)).getText()
	
def get_a_key(userInput):
	if userInput:
		return u_vk
	else:
		return i_vk

def GetBookChapter(string, context=""):
	chapter = i_vk.ParseVerseList(
		to_str(string), to_str(context), True
	).getText()#.decode(locale_encoding)
	index = chapter.find(":")
	
	if index != -1:
		chapter = chapter[:index]
	return chapter
	

def BookName(text):
	#TODO: u_vk or i_vk?
	u_vk.setText(to_str(text))
	if u_vk.Error(): return None
	return u_vk.getBookName()

def GetBestRange(text, context="", abbrev=False, raiseError=False,
		userInput=False, userOutput=False, headings=False,
		use_bpbible_locale=False):
	vl = VerseList(text, context=context, raiseError=raiseError,
		userInput=userInput, headings=headings,
		use_bpbible_locale=use_bpbible_locale)
	return vl.GetBestRange(abbrev, userOutput=userOutput)

class Searcher(SW.Searcher):
	def __init__(self, book, userdata = None):
		SW.Searcher.__init__(self, book.mod)
		self.mod = book.mod
		self.callback = None
		self.userdata = userdata

	def PercentFunction(self, number):
		if(self.callback):
			continuing = self.callback(number, self.userdata)
			if not continuing:
				self.TerminateSearch()
	
	def Search(self, string, options=0, scopestr=None, case_sensitive=False):
		scope = None
		assert scopestr is None

		list = self.doSearch(string, options, 
			(not case_sensitive)*REG_ICASE, scope)

		results = []
		for item in range(list.Count()):
			results.append(list.GetElement(item))
		
		return [x.getText() for x in results]
	
class VerseKeySearcher(Searcher):
	def __init__(self, book, userdata = None):
		super(VerseKeySearcher, self).__init__(book, userdata)
		self.vk = VK()
		self.vk.thisown = False

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

# allow reloading
sys.SW_dont_do_stringmgr = True
