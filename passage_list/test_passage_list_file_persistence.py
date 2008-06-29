import os
import unittest
from swlib.pysw import VK, VerseList
from passage_entry import PassageEntry
from passage_list import PassageList, PassageListManager, load_from_file, \
		load_default_passage_lists, InvalidPassageListError

FILENAME = "test_passage_list.p"

class TestPassageListFilePersistence(unittest.TestCase):
	def setUp(self):
		self._verse_list1 = VerseList("gen 2:3 - 5, 3:4, 5:2")
		self._verse_list2 = VerseList("ex 2:2, 3:5, 7 - 9")
		self._verse_list3 = VerseList("lev 2:3 - 5, 7")
		self._verse_list4 = VerseList("num 3:1, 4 - 5")
		self._verse_list5 = VerseList("deut 3:7")
		self._list = PassageList.create_from_verse_list("abc", self._verse_list1)
		self._list2 = PassageList.create_from_verse_list("def", self._verse_list2)
		self._list3 = PassageList.create_from_verse_list("ghi", self._verse_list3)
		self._list4 = PassageList.create_from_verse_list("jkl", self._verse_list4)
		self._list5 = PassageList.create_from_verse_list("mno",
				self._verse_list5)
		self._list2.add_subtopic(self._list4)
		self._list.add_subtopic(self._list2)
		self._list.add_subtopic(self._list3)
		self._manager = PassageListManager(FILENAME)
		self._manager.add_subtopic(self._list)
		self._manager.add_subtopic(self._list5)
		self._manager.add_passage(PassageEntry("gen 2:3 - 5", "comment"))
		_remove_file(FILENAME)
		self._manager.save()
	
	def testStoredListShouldBeIdenticalOnLoad(self):
		"""Checks that the list that is stored and loaded is the same."""
		stored_list = load_from_file(FILENAME)
		self.assertEquals(self._manager, stored_list)
	
	def testStoredListShouldHaveCorrectParents(self):
		"""Checks that the list that is stored and loaded is the same."""
		stored_list = load_from_file(FILENAME)
		self._checkParents(stored_list)
	
	def testStoredListShouldBeIdenticalOnLoadWithDefault(self):
		"""Checks that the list is the same when loaded with defaults."""
		stored_list = load_default_passage_lists(FILENAME)
		self.assertEquals(self._manager, stored_list)

	def testStoredListShouldBeAbleToBeSaved(self):
		stored_list = load_from_file(FILENAME)
		stored_list.save()
		stored_list = load_from_file(FILENAME)
		self.assertEquals(self._manager, stored_list)

	def testShouldSupportInitialPassageListFormat(self):
		stored_list = load_from_file("initial_passage_list.p")
		self.assertEquals(self._manager, stored_list)
		self._checkParents(stored_list)

	def _checkParents(self, list):
		"""Check that all the parents in the given list are correct."""
		for subtopic in list.subtopics:
			self.assert_(subtopic.parent is list)
			self._checkParents(subtopic)

class TestLoadFromInvalidFile(unittest.TestCase):
	def setUp(self):
		_remove_file(FILENAME)
	
	def testLoadFromFileShouldRaiseException(self):
		self.assertRaises(InvalidPassageListError, load_from_file, FILENAME)
	
	def testLoadFromFileWithDefaultShouldGiveEmptySubTopics(self):
		manager = load_default_passage_lists(FILENAME)
		self.assertEquals(len(manager.subtopics), 0)
	
	def testLoadFromFileWithDefaultShouldAllowSaving(self):
		manager = load_default_passage_lists(FILENAME)
		manager.save()
		self.assertEquals(manager, load_from_file(FILENAME))

def _remove_file(filename):
	try:
		os.remove(filename)
	except OSError:
		pass

if __name__ == "__main__":
	unittest.main()
