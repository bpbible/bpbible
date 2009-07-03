class VerseToPassageEntryMap(object):
	def __init__(self):
		self._map = {}

	def update_passage_entry(self, passage_entry, old_passage):
		if old_passage is not None:
			self._remove_passage(passage_entry, old_passage)
		self.add_passage_entry(passage_entry)

	def add_passage_entry(self, passage_entry):
		# If the passage is not connected to a topic or its parent topic has
		# not yet been connected to a topic then it should not be added.
		# This prevents duplicate entries when a list of passages is created
		# and then added to the main passage manager (like in saved search results).
		if passage_entry.parent is None or passage_entry.parent.parent is None:
			return

		for verse_key in passage_entry.passage:
			for verse in verse_key:
				verse_key_text = self._verse_key_text(verse)
				if verse_key_text not in self._map:
					self._map[verse_key_text] = []
				self._map[verse_key_text].append(passage_entry)

	def remove_passage_entry(self, passage_entry):
		self._remove_passage(passage_entry, passage_entry.passage)

	def _remove_passage(self, passage_entry, passage):
		for verse_key in passage:
			for verse in verse_key:
				verse_key_text = self._verse_key_text(verse)
				try:
					self._map[verse_key_text].remove(passage_entry)
				except ValueError:
					pass

	def clear(self):
		self._map = {}

	def get_passage_entries_for_verse_key(self, verse_key):
		return self._map.get(self._verse_key_text(verse_key), [])

	def _verse_key_text(self, verse_key):
		return verse_key.getShortText()

# XXX: Like the SQLite manager, this should not be a singleton.  It's just
# too much trouble to make it otherwise at the moment.
singleton_verse_to_passage_entry_map = VerseToPassageEntryMap()
