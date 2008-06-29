from swlib.pysw import VK
import unittest
from passage_entry import PassageEntry, InvalidPassageError, \
		MultiplePassagesError, lookup_passage_entry

class TestPassageEntry(unittest.TestCase):
	def setUp(self):
		self._key = VK("gen 2:2")
		self._range = VK(("gen 3:5", "gen 3:10"))
		self._passage_entry = PassageEntry(self._key)
		self._passage_entry2 = PassageEntry(self._range)

	def testConstructorShouldSetPassageCorrectly(self):
		self.assertEqual(self._passage_entry.passage, self._key)
	
	def testConstructorShouldCreateEmptyComment(self):
		self.assertEqual(self._passage_entry.comment, "")
	
	def testPassageCanBeSetFromStringInConstructor(self):
		passage_entry = PassageEntry("gen 2:3 - 5")
		self.assertEqual(str(passage_entry), "Genesis 2:3 - 5")

	def testConstructorShouldAllowSettingComment(self):
		self._passage_entry = PassageEntry(self._key, "some comment")
		self.assertEqual(self._passage_entry.comment, "some comment")
	
	def testContainsVerseWorksWithSingleVerse(self):
		self.assert_(self._passage_entry.contains_verse(VK("gen 2:2")))
		self.assert_(not self._passage_entry.contains_verse(VK("gen 2:1")))
	
	def testContainsVerseWorksWithRange(self):
		self.assert_(self._passage_entry2.contains_verse(VK("gen 3:5")))
		self.assert_(self._passage_entry2.contains_verse(VK("gen 3:6")))
		self.assert_(self._passage_entry2.contains_verse(VK("gen 3:9")))
		self.assert_(self._passage_entry2.contains_verse(VK("gen 3:10")))
		self.assert_(not self._passage_entry2.contains_verse(VK("gen 3:4")))
		self.assert_(not self._passage_entry2.contains_verse(VK("gen 3:11")))
	
	def testStringMethodWorksOnVerses(self):
		self.assertEqual(str(self._passage_entry), "Genesis 2:2")
	
	def testStringMethodWorksOnRanges(self):
		self.assertEqual(str(self._passage_entry2), "Genesis 3:5 - 10")
	
	def testStringMethodWorksOnEmptyPassage(self):
		self.assertEqual(str(PassageEntry(None)), "")
	
	def testPassageCanBeSetFromString(self):
		self._passage_entry.passage = "exodus 4:4"
		self.assertEquals(str(self._passage_entry), "Exodus 4:4")
	
	def testPassageRangeCanBeSetFromString(self):
		self._passage_entry.passage = "exodus 4:4 - 5:7"
		self.assertEquals(str(self._passage_entry), "Exodus 4:4 - 5:7")

	def testPassageCannotBeSetFromInvalidString(self):
		self.assertRaises(InvalidPassageError,
				self._setPassage, "invalid reference")

	def testPassageCannotBeSetFromStringWithMultiplePassages(self):
		self.assertRaises(MultiplePassagesError,
				self._setPassage, "gen 3:5 - 7, 9, 11")

	def testPassageGlobalLookup(self):
		passage_entry = lookup_passage_entry(self._passage_entry.get_id())
		self.assert_(passage_entry is self._passage_entry)
	
	def _setPassage(self, passage):
		self._passage_entry.passage = passage

class TestPassageEntryListener(unittest.TestCase):
	def setUp(self):
		self._passage_entry = PassageEntry("gen 2:2 - 4")
		self._num_times_observer_called = 0
		self._passage_entry.observers += self._passageEntryChanged

	def testChangingPassageShouldNotify(self):
		self._passage_entry.passage = "gen 2:2"
		self._checkHasChanged()

	def testChangingCommentShouldNotify(self):
		self._passage_entry.comment = "comment"
		self._checkHasChanged()

	def testSettingSamePassageShouldNotNotify(self):
		self._passage_entry.passage = "gen 2:2 - 4"
		self._checkHasNotChanged()

	def testSettingSameCommentShouldNotNotify(self):
		self._passage_entry.comment = ""
		self._checkHasNotChanged()

	def _checkHasChanged(self):
		self.assertEqual(self._num_times_observer_called, 1)

	def _checkHasNotChanged(self):
		self.assertEqual(self._num_times_observer_called, 0)
	
	def _passageEntryChanged(self):
		self._num_times_observer_called += 1

if __name__ == "__main__":
	unittest.main()
