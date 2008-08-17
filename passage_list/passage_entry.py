from swlib.pysw import VerseList
from util.observerlist import ObserverList

_passage_entry_id_dict = {}

class PassageEntry(object):
	"""A passage entry contains a passage and a comment.

	The passage is a verse key, while the comment is a string that can be
	attached to comments.
	
	The passage entry is included in a passage entry list.
	"""
	def __init__(self, passage, comment=""):
		self._set_passage(passage)
		self._comment = comment
		self.observers = ObserverList()

		global _passage_entry_id_dict
		_passage_entry_id_dict[self.get_id()] = self
	
	def contains_verse(self, verse):
		if self.passage.isBoundSet():
			lower_bound = self.passage.LowerBound()
			upper_bound = self.passage.UpperBound()
		else:
			lower_bound = self.passage
			upper_bound = self.passage
		return lower_bound.compare(verse) <= 0 \
				and upper_bound.compare(verse) >= 0
	
	def get_passage(self):
		return self._passage
	
	def set_passage(self, passage):
		"""Sets the passage for this passage entry.

		If the passage is a string, then it will be converted to a passage if
		possible.  If the string contains multiple passages, then a
		MultiplePassagesError will be raised.  If the string does not
		represent a valid passage, then an InvalidPassageError will be raised.
		"""
		old_passage = self._passage
		self._set_passage(passage)
		if self._passage != old_passage:
			self._notify()
	
	def _set_passage(self, passage):
		"""Sets the passage without notifying that the passage has changed."""
		if isinstance(passage, basestring):
			passage = self._parse_passage_str(str(passage))
		self._passage = passage
	
	passage = property(get_passage, set_passage,
			doc="The passage (as a VK).")
	
	def get_comment(self):
		return self._comment
	
	def set_comment(self, comment):
		if self._comment != comment:
			self._comment = comment
			self._notify()
	
	def _notify(self):
		self.observers()
	
	comment = property(get_comment, set_comment,
			doc="The comment on the passage entry.")
	
	def _parse_passage_str(self, passage):
		passages = VerseList(passage)
		if len(passages) == 1:
			return passages[0]
		elif len(passages) > 1:
			raise MultiplePassagesError
		else:
			raise InvalidPassageError

	def get_id(self):
		"""Gets a unique identifier for this passage entry.

		This can be used to identify the passage entry and look it up using
		lookup_passage_entry, which is used in creating tags for the HTML
		window.
		"""
		return id(self)
	
	def __str__(self):
		if self.passage is None:
			return ""
		elif self.passage.isBoundSet():
			return self._get_range_text()
		else:
			return self.passage.getText()

	def __repr__(self):
		return "PassageEntry(%s, %s)" % (repr(str(self)), repr(self.comment))
	
	def _get_range_text(self):
		lower_bound = self.passage.LowerBound()
		upper_bound = self.passage.UpperBound()
		begin_str = self.passage.LowerBound().getText()

		if lower_bound.Book() != upper_bound.Book():
			end_str = "%s %d:%d" % (upper_bound.getBookName(),
				upper_bound.Chapter(), upper_bound.Verse())
		elif lower_bound.Chapter() != upper_bound.Chapter():
			end_str = "%d:%d" % (upper_bound.Chapter(), upper_bound.Verse())
		else:
			end_str = str(upper_bound.Verse())
		return "%s - %s" % (begin_str, end_str)

	def clone(self):
		"""Makes a clean copy of this passage entry and returns it."""
		return PassageEntry(passage=str(self), comment=self.comment)
	
	def __eq__(self, other):
		try:
			return self.passage == other.passage \
					and self.comment == other.comment
		except:
			return False

	def __reduce__(self):
		return PassageEntry, (self.passage, self.comment)

class PassageError(Exception):
	pass

class InvalidPassageError(PassageError):
	"""This error is raised if an invalid passage string is given."""

class MultiplePassagesError(PassageError):
	"""This error is raised if the passage string contains multiple passages."""

def lookup_passage_entry(id):
	"""Looks up the passage entry with the given ID.

	This is used by the passage tag to easily identify a given passage entry
	(since tags can only receive string parameters).
	"""
	global _passage_entry_id_dict
	return _passage_entry_id_dict[id]
