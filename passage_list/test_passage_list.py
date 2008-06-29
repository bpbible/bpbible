from swlib.pysw import VK, VerseList
import unittest
from passage_list import PassageList, PassageListManager, lookup_passage_list
from passage_entry import PassageEntry

class TestPassageListConstruction(unittest.TestCase):
	def setUp(self):
		self._list = PassageList("topic")
	
	def testShouldHaveValidName(self):
		self.assertEqual(self._list.name, "topic")
	
	def testShouldContainNoPassages(self):
		self.assertEqual(len(self._list.passages), 0)
	
	def testShouldContainNoSubTopics(self):
		self.assertEqual(len(self._list.subtopics), 0)
	
	def testShouldHaveEmptyDescription(self):
		self.assertEqual(self._list.description, "")

	def testListGlobalLookup(self):
		passage_list = lookup_passage_list(self._list.get_id())
		self.assert_(passage_list is self._list)

class TestCreationFromVerseList(unittest.TestCase):
	def setUp(self):
		self._list = PassageList.create_from_verse_list("name",
				VerseList(["gen 2:3", "gen 2:5", "gen 2:7"]), "description")
	
	def testPassageLength(self):
		self.assertEquals(len(self._list.passages), 3)
	
	def testValuesAreRight(self):
		self.assertEquals(self._list.passages[0].passage, VK("gen 2:3"))
		self.assertEquals(self._list.passages[2].passage, VK("gen 2:7"))
	
	def testTestDescriptionShouldBeSet(self):
		self.assertEquals(self._list.description, "description")

class TestAddEmptySubTopic(unittest.TestCase):
	def setUp(self):
		self._list = PassageList("topic")
		self._list.add_empty_subtopic("Name", "Description")
		self._added_subtopic = self._list.subtopics[0]
	
	def testShouldHaveOneSubTopic(self):
		self.assertEqual(len(self._list.subtopics), 1)
	
	def testAddedSubTopicShouldBeEmpty(self):
		self.assertEqual(len(self._added_subtopic.subtopics), 0)
		self.assertEqual(len(self._added_subtopic.passages), 0)

	def testAddedSubTopicShouldHaveCorrectDetails(self):
		self.assertEqual(self._added_subtopic.name, "Name")
		self.assertEqual(self._added_subtopic.description, "Description")

class TestVerseContainment(unittest.TestCase):
	def setUp(self):
		_setupPassageLists(self)
	
	def testVersesInMainTopicShouldBeContainedDirectly(self):
		self.assert_(self._list.contains_verse(VK("gen 3:4")))
	
	def testVersesInSubtopicsShouldNotBeContainedDirectly(self):
		self.assert_(not self._list.contains_verse(VK("ex 2:2")))
		self.assert_(not self._list.contains_verse(VK("num 2:5")))
	
	def testVersesInSubtopicsShouldBeContainedRecursively(self):
		self.assert_(self._list.contains_verse(VK("ex 2:2"), recursive=True))
		self.assert_(self._list.contains_verse(VK("num 3:5"), recursive=True))
	
	def testVersesInVerseRangeShouldBeContained(self):
		self.assert_(self._list.contains_verse(VK("gen 2:5")))
		self.assert_(self._list.contains_verse(VK("gen 2:4")))
	
	def testVersesNotInVerseRangeShouldNotBeContained(self):
		self.assert_(not self._list.contains_verse(VK("deut 3:5")))
		self.assert_(not self._list.contains_verse(VK("deut 3:5"), recursive=True))

class TestPassageListPassageListener(unittest.TestCase):
	def setUp(self):
		self._passage_list = PassageList("topic")
		self._num_times_observer_called = 0
		self._passage_list.add_passage_observers += self._addPassage
	
	def testAddPassageShouldCallObserver(self):
		self._passage_list.add_passage(PassageEntry(None))
		self._checkObserverHasBeenCalled()

	def _checkObserverHasBeenCalled(self):
		self.assertEqual(self._num_times_observer_called, 1)
	
	def _addPassage(self, passage):
		self._num_times_observer_called += 1

class TestPassageListSubTopicListener(unittest.TestCase):
	def setUp(self):
		self._passage_list = PassageList("topic")
		self._num_times_observer_called = 0
		self._passage_list.add_subtopic_observers += self._addSubTopic
	
	def testAddSubTopicShouldCallListener(self):
		self._passage_list.add_subtopic(PassageList("a"))
		self._checkObserverHasBeenCalled()
	
	def testAddEmptySubListShouldCallListener(self):
		self._passage_list.add_empty_subtopic("topic", "description")
		self._checkObserverHasBeenCalled()

	def _checkObserverHasBeenCalled(self):
		self.assertEqual(self._num_times_observer_called, 1)
	
	def _addSubTopic(self, subtopic):
		self._num_times_observer_called += 1

class TestPassageListParentDetails(unittest.TestCase):
	def setUp(self):
		_setupPassageLists(self)
	
	def testSubTopicShouldHaveValidTopicTrail(self):
		self.assertEquals(self._list4.topic_trail, ("abc", "def", "jkl"))
	
	def testSubTopicShouldHaveValidFullName(self):
		self.assertEquals(self._list4.full_name, "abc > def > jkl")

	def testSubTopicShouldHaveValidPath(self):
		self.assertEquals(self._list4.path, [0, 0, 0])

	def testCanFollowPaths(self):
		self.assert_(self._manager.find_topic_by_path(self._list4.path) is self._list4)
		self.assert_(self._manager.find_topic_by_path(self._list2.path) is self._list2)
		self.assert_(self._manager.find_topic_by_path(self._manager.path) is self._manager)

	def testManagerHasEmptyPath(self):
		self.assertEquals(self._manager.path, [])

	def testSubTopicShouldHaveCorrectParent(self):
		self.assert_(self._list2.parent is self._list)
		self.assert_(self._list4.parent is self._list2)

def _setupPassageLists(test):
	"""Sets up the passage lists for the given test."""
	test._verse_list1 = VerseList([VK(("gen 2:3", "gen 2:5")), "gen 3:4", "gen 5:2"])
	test._verse_list2 = VerseList(["ex 2:2", "ex 3:5", VK(("ex 3:7", "ex 3:9"))])
	test._verse_list3 = VerseList([VK(("lev 2:3", "lev 2:5")), "lev 2:7"])
	test._verse_list4 = VerseList(["num 3:1", VK(("num 3:4", "num 3:5"))])
	test._list = PassageList.create_from_verse_list("abc", test._verse_list1)
	test._list2 = PassageList.create_from_verse_list("def", test._verse_list2)
	test._list3 = PassageList.create_from_verse_list("ghi", test._verse_list3)
	test._list4 = PassageList.create_from_verse_list("jkl", test._verse_list4)
	test._list2.add_subtopic(test._list4)
	test._list.add_subtopic(test._list2)
	test._list.add_subtopic(test._list3)
	test._manager = PassageListManager()
	test._manager.add_subtopic(test._list)

if __name__ == "__main__":
	unittest.main()
