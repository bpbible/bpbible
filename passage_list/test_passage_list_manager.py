from swlib.pysw import VerseList, VK
import unittest
from passage_list import PassageList, PassageListManager

class TestPassageListManagerListener(unittest.TestCase):
	def setUp(self):
		self._manager = PassageListManager()
		self._num_times_observer_called = 0
		self._manager.add_subtopic_observers += self._passageListAppend
	
	def testAddSublistShouldCallObserver(self):
		self._manager.add_empty_subtopic("name")
		self._checkObserverHasBeenCalled()

	def _checkObserverHasBeenCalled(self):
		self.assertEqual(self._num_times_observer_called, 1)
	
	def _passageListAppend(self, passage_list):
		self._num_times_observer_called += 1

if __name__ == "__main__":
	unittest.main()

