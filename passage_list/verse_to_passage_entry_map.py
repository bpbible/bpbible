from util.observerlist import ObserverList

class VerseToPassageEntryMap(object):
	def __init__(self):
		self._map = {}
		self.add_verses_observers = ObserverList()
		self.remove_verses_observers = ObserverList()
		self.disable_observers = False

	def update_passage_entry(self, passage_entry, old_passage):
		old_passage_set = set(self._passage_to_list(old_passage))
		new_passage_set = set(self._passage_to_list(passage_entry.passage))
		added_verses = new_passage_set - old_passage_set
		removed_verses = old_passage_set - new_passage_set
		if removed_verses:
			self._remove_verses(passage_entry, removed_verses)
		if added_verses:
			self._add_verses(passage_entry, added_verses)

	def add_passage_entry(self, passage_entry):
		# If the passage is not connected to a topic or its parent topic has
		# not yet been connected to a topic then it should not be added.
		# This prevents duplicate entries when a list of passages is created
		# and then added to the main passage manager (like in saved search results).
		if passage_entry.parent is None or passage_entry.parent.parent is None:
			return

		self._add_verses(passage_entry, self._passage_to_list(passage_entry.passage))

	def _add_verses(self, passage_entry, added_verses):
		if passage_entry.parent is None or passage_entry.parent.parent is None:
			return

		for verse_key_text in added_verses:
			if verse_key_text not in self._map:
				self._map[verse_key_text] = []
			self._map[verse_key_text].append(passage_entry)

		if not self.disable_observers:
			self.add_verses_observers(passage_entry, added_verses)

	def remove_passage_entry(self, passage_entry):
		self._remove_verses(passage_entry, self._passage_to_list(passage_entry.passage))

	def _remove_verses(self, passage_entry, removed_verses):
		for verse_key_text in removed_verses:
			self._map[verse_key_text].remove(passage_entry)

		if not self.disable_observers:
			self.remove_verses_observers(passage_entry, removed_verses)

	def _passage_to_list(self, passage):
		if passage is None:
			return []

		verse_key_list = []
		for verse_key in passage:
			for verse in verse_key:
				verse_key_list.append(self._verse_key_text(verse))
		return verse_key_list

	def clear(self):
		self._map = {}

	def get_passage_entries_for_verse_key(self, verse_key):
		return self._map.get(self._verse_key_text(verse_key), [])

	def _verse_key_text(self, verse_key):
		return verse_key.getShortText()

# XXX: Like the SQLite manager, this should not be a singleton.  It's just
# too much trouble to make it otherwise at the moment.
singleton_verse_to_passage_entry_map = VerseToPassageEntryMap()
