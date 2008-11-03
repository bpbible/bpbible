import process_text
from swlib.pysw import SW, VerseList
import re

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

class StrongsField(BaseField):
	field_name = "strongs"

	@classmethod	
	def prepare(cls, input):
		match = re.match("^([GH])(\d+)(\w*)$", input)
		if not match:
			from search import SearchException
			raise SearchException(
				_("Invalid strong's number %s.") % input
			)

		prefix, number, extra = match.group(1, 2, 3)
		number = int(number)
		if number > 9999:
			from search import SearchException
			raise SearchException(_("Invalid strong's number %s.") % input)

		return "%s%04d%s" % (prefix, int(number), extra)
	

class RefField(BaseField):
	field_name = "ref"
	
	def _unused_collect(self, number, text, start, end):
		self.matches.append((
			number, start, end
		))
	
	def finalize(self):
		return '\n'.join(self.matches).replace(
			process_text.ParseOSIS.FIELD_SEPARATOR.decode("utf-8"),
			"."
		)
	
	@classmethod
	def prepare(cls, input):
		vl = VerseList(input, raiseError=True)
		assert len(vl) == 1
		if vl[0][0].getBookName() != vl[0][-1].getBookName():
			from search import SearchException		
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
	
all_fields = RefField, KeyField, StrongsField, 
