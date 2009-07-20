from swlib.pysw import VerseList
from util.observerlist import ObserverList
from verse_to_passage_entry_map import singleton_verse_to_passage_entry_map

_passage_entry_id_dict = {}

class PassageEntry(object):
	"""A passage entry contains a passage and a comment.

	The passage is a verse key, while the comment is a string that can be
	attached to comments.
	
	The passage entry is included in a passage entry list.
	"""
	__table__ = "passage"
	__fields_to_store__ = ["passage", "comment", "order_number", "parent"]

	def __init__(self, passage, comment=""):
		self.passage_changed_observers = ObserverList()
		self.comment_changed_observers = ObserverList()
		self._passage = None
		self._set_passage(passage)
		self._comment = comment
		self.parent = None

		global _passage_entry_id_dict
		_passage_entry_id_dict[self.get_id()] = self
		self.order_number = 0
		self.id = None
	
	def contains_verse(self, verse):
		if not self.passage:
			return False

		for verse_key in self.passage:
			if verse_key.isBoundSet():
				lower_bound = verse_key.LowerBound()
				upper_bound = verse_key.UpperBound()
			else:
				lower_bound = verse_key
				upper_bound = verse_key
			if (lower_bound.compare(verse) <= 0
					and upper_bound.compare(verse) >= 0):
				return True
	
	def get_passage(self):
		return self._passage
	
	def set_passage(self, passage, new_passage=False):
		"""Sets the passage for this passage entry.

		If the passage is a string, then it will be converted to a passage if
		possible.  If the string does not represent a valid passage,
		then an InvalidPassageError will be raised.
		"""
		old_passage = self._passage
		self._set_passage(passage)
		if self._passage != old_passage and not new_passage:
			self.passage_changed_observers(self._passage)
			singleton_verse_to_passage_entry_map.update_passage_entry(self, old_passage)
	
	def _set_passage(self, passage):
		"""Sets the passage without notifying that the passage has changed."""
		if isinstance(passage, basestring):
			passage = self._parse_passage_str(str(passage))
		self._passage = passage
	
	passage = property(get_passage, set_passage,
			doc="The passage (as a VerseList).")
	
	def get_comment(self):
		return self._comment
	
	def set_comment(self, comment):
		if self._comment != comment:
			self._comment = comment
			self.comment_changed_observers(comment)
	
	comment = property(get_comment, set_comment,
			doc="The comment on the passage entry.")
	
	def _parse_passage_str(self, passage):
		if not passage:
			return None

		passages = VerseList(passage)
		if len(passages) >= 1:
			return passages
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
		return str(self.passage)

	def __repr__(self):
		return "PassageEntry(%s, %s)" % (repr(str(self)), repr(self.comment))

	def clone(self):
		"""Makes a clean copy of this passage entry and returns it."""
		return PassageEntry(passage=str(self), comment=self.comment)
	
	def __eq__(self, other):
		try:
			return self.passage == other.passage \
					and self.comment == other.comment
			# For help in debugging.
			#import sys
			#sys.stderr.write("%s, passages equal: %s, comment equal: %s\n" % (self, self.passage == other.passage, self.comment == other.comment))
		except:
			return False

	def __cmp__(self, other):
		if self.passage is None or other.passage is None:
			return -1
		return cmp(self.passage[0], other.passage[0])

class PassageError(Exception):
	pass

class InvalidPassageError(PassageError):
	"""This error is raised if an invalid passage string is given."""

def lookup_passage_entry(id):
	"""Looks up the passage entry with the given ID.

	This is used by the passage tag to easily identify a given passage entry
	(since tags can only receive string parameters).
	"""
	global _passage_entry_id_dict
	return _passage_entry_id_dict[id]
