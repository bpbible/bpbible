from search import query_parser
from swlib.pysw import SW, VerseList
import re
from util import classproperty
from util.debug import dprint, WARNING

class BaseField(object):
	field_name = None

	def __init__(self):
		self.matches = []
	
	def collect(self, number, text, start, end):
		self.matches.append("%s\x00%s %s" % (
				number, start, end
		))
	
	def finalize(self):
		return '\n'.join(self.matches)
	
	@classmethod
	def prepare(cls, input):
		return input
	
	@classproperty
	def field_to_use(cls):
		return cls.field_name
	
	def get_parser(self):
		"""Convenience method to avoid circular import at top level"""
		from search import process_text
		return process_text.ParseBase

class StrongsField(BaseField):
	field_name = "strongs"

	@classmethod	
	def prepare(cls, input):
		match = re.match("^([GH])(\d+)(\w*)$", input)
		if not match:
			from index import SearchException
			raise SearchException(
				_("Invalid strong's number %s.") % input
			)

		prefix, number, extra = match.group(1, 2, 3)
		number = int(number)
		if number > 9999:
			from index import SearchException
			raise SearchException(_("Invalid strong's number %s.") % input)

		return "%s%04d%s" % (prefix, int(number), extra)
	
	def finalize(self):
		return super(StrongsField, self).finalize().replace(
			self.get_parser().FIELD_SEPARATOR.decode("utf-8"),
			":"
		).replace(
			self.get_parser().DASH.decode("utf-8"),
			"-"
		)
		

	
class MorphField(BaseField):
	field_to_use = "strongs"
	field_name = "morph"

	@classmethod
	def prepare(cls, input):
		# if we are given a key
		# e.g. morph:robinson:VP-NA,
		# then use it verbatim
		# Otherwise, just put a : before to ensure that it is a morph term
		if ":" in input:
			key, value = input.split(":", 1)
		else:
			key = ""
			value = input
		

		#value = query_parser.expand_wildcards(value)

		# NOTE: we work here on the remarkably naive assumption that we don't
		# need to check that there is no morphology key which ends in this
		# morphology key. Otherwise, we would have to put a \b at the start,
		# which takes ~8 times longer.
		# If this ever becomes important, we can add a special start character
		# before morphs and use that instead of \b
		ret = r"%s:%s\b" % (key, value)
		return ret
			
class RefField(BaseField):
	field_name = "ref"
	
	def _unused_collect(self, number, text, start, end):
		self.matches.append((
			number, start, end
		))
	
	def finalize(self):
		return '\n'.join(self.matches).replace(
			self.get_parser().FIELD_SEPARATOR.decode("utf-8"),
			"."
		)
	
	@classmethod
	def prepare(cls, input):
		vl = VerseList(input, raiseError=True, userInput=True)
		if len(vl) != 1:
			dprint(
				WARNING, 
				"Multiple results in search ref: verselist. Taking first",
				vl
			)
		if vl[0][0].getBookName() != vl[0][-1].getBookName():
			from index import SearchException		
			raise SearchException(
				_("In finding references, the reference "
					"must all be in one book")
		)
		
		def get_chapter_verses(versekey):
			return versekey.verseCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
				versekey.Chapter()
			)
		
		def get_book_chapters(versekey):
			return versekey.chapterCount(
				ord(versekey.Testament()), 
				ord(versekey.Book()), 
			)			
		
		start, end = vl[0][0], vl[0][-1]
		osisref = start.getOSISRef()
		bookname = osisref[:osisref.find(".")]
		
		if start.Chapter() == 1 and start.Verse() == 1 and \
			end.Chapter() == get_book_chapters(end) and \
			end.Verse() == get_chapter_verses(end):
			
			return r'\b%s\b' % bookname

		items = []

		if start.Chapter() != end.Chapter():
			# do all the verses in the start chapter individually
			sc = start.Chapter()
			for verse in range(start.Verse(), get_chapter_verses(start)+1):
				items.append(r'(?:%d\.%d)' % (sc, verse))
			
			# do all the verses in the end chapter individually
			ec = end.Chapter()
			for verse in range(1, end.Verse()+1):
				items.append(r'(?:%d\.%d)' % (ec, verse))

			# but do each chapter in the middle all in one
			for chapter in range(start.Chapter()+1, end.Chapter()):
				items.append(r'(?:%d)' % (chapter))
		else:
			sc = start.Chapter()
			if start.Verse() == 1 and \
				end.Verse() == get_chapter_verses(end):
				items.append('(?:%d)' % (sc))
			else:
				for verse in range(start.Verse(), end.Verse()+1):
					items.append(
						'(?:%d\.%d)' % (sc, verse)
					)

		regex = r'\b%s\.(?:%s)\b' % (bookname, '|'.join(items))
		print regex

		return 	regex	

class KeyField(BaseField):
	field_name = "key"
	

	def finalize(self):
		return '\n'.join(self.matches)
#.replace(
#		)
	
all_fields = RefField, KeyField, StrongsField, MorphField 
