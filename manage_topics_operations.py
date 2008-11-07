PASSAGE_SELECTED = 1
TOPIC_SELECTED = 2

class ManageTopicsOperations(object):
	def __init__(self, context):
		self._context = context
		self._clipboard_data = None

	def add_subtopic(self, subtopic):
		self._context.get_selected_topic().add_subtopic(subtopic)

	def remove_subtopic(self):
		subtopic = self._context.get_selected_topic()
		subtopic.parent.remove_subtopic(subtopic)

	def add_passage(self, passage):
		self._context.get_selected_topic().add_passage(passage)

	def remove_passage(self):
		self._context.get_selected_topic().remove_passage(
				self._context.get_selected_passage()
			)

	# XXX: Deleting a topic doesn't remove its tags from the current window.
	def delete(self):
		item, type = self._context.get_selected_item()
		if not item:
			return

		if type == PASSAGE_SELECTED:
			self.remove_passage()
		else:
			self.remove_subtopic()

	def cut(self):
		self._setup_clipboard(keep_original=False)

	def copy(self):
		self._setup_clipboard(keep_original=True)

	def _setup_clipboard(self, keep_original):
		item, type = self._context.get_selected_item()
		if not item:
			return

		self._clipboard_data = ClipboardData(
				item, type, keep_original=keep_original)

	def paste(self):
		if not self._clipboard_data:
			return

		self.do_copy(self._clipboard_data.item,
				self._clipboard_data.type,
				self._context.get_selected_topic(),
				self._clipboard_data.keep_original)

	def do_copy(self, item, type, to_topic, keep_original):
		from_topic = item.parent
		self._check_circularity(to_topic, item)
		if from_topic is to_topic:
			return

		if keep_original:
			item = item.clone()
		if type == PASSAGE_SELECTED:
			if not keep_original:
				from_topic.remove_passage(item)
			to_topic.add_passage(item)
		else:
			if not keep_original:
				from_topic.remove_subtopic(item)
			to_topic.add_subtopic(item)

	def _check_circularity(self, to_topic, item):
		if type == PASSAGE_SELECTED:
			return
		topic_parent = to_topic
		while topic_parent is not None:
			if topic_parent is item:
				raise CircularDataException()
			topic_parent = topic_parent.parent

	def set_topic_name(self, name):
		self._context.get_selected_topic().name = name

class ClipboardData(object):
	"""This class manages the item that is currently in the clipboard."""
	def __init__(self, item, type, keep_original):
		self.item = item
		self.type = type
		self.keep_original = keep_original

class CircularDataException(Exception):
	"""This exception is raised when the topic manager detects circular data,
	typically because the user has attempted to copy or move a topic to one
	of its children.
	"""

def _test():
	"""
	>>> from passage_list import PassageListManager
	>>> manager = _test_create_topic(create_function=PassageListManager)
	>>> topic1 = _test_create_topic("topic1")
	>>> topic2 = _test_create_topic("topic2")
	>>> topic3 = _test_create_topic("topic3")
	>>> passage1 = _test_create_passage("gen 3:5")
	>>> operations_manager_context = DummyOperationsManagerContext()
	>>> operations_manager = ManageTopicsOperations(context=operations_manager_context)
	>>> def _add_subtopic(topic1, topic2, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic1
	... 	operations_manager.add_subtopic(topic2)
	...
	>>> def _remove_subtopic(topic2, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = False
	... 	operations_manager_context.selected_topic = topic2
	... 	operations_manager.delete()
	...
	>>> def _add_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.add_passage(passage)
	...
	>>> def _remove_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = True
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.delete()
	...
	>>> def _move_passage(passage, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = True
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = None
	... 	operations_manager.cut()
	... 	operations_manager_context.selected_topic = target_topic
	... 	operations_manager.paste()
	...
	>>> def _move_topic(topic, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = False
	... 	operations_manager_context.selected_passage = None
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.cut()
	... 	operations_manager_context.selected_topic = target_topic
	... 	operations_manager.paste()
	...
	>>> def _copy_topic(topic, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = False
	... 	operations_manager_context.selected_passage = None
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.copy()
	... 	operations_manager_context.selected_topic = target_topic
	... 	operations_manager.paste()
	...
	>>> def _copy_passage(passage, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = True
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = None
	... 	operations_manager.copy()
	... 	operations_manager_context.selected_topic = target_topic
	... 	operations_manager.paste()
	...
	>>> def _set_topic_name(topic, name, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.set_topic_name(name)
	...
	>>> _add_subtopic(manager, topic1)
	Topic 'None': add subtopic observer called.
	>>> _add_subtopic(topic1, topic2)
	Topic 'topic1': add subtopic observer called.
	>>> _add_passage(topic2, passage1)
	Topic 'topic1 > topic2': add passage observer called.
	>>> topic2.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> _remove_passage(topic2, passage1)
	Topic 'topic1 > topic2': remove passage observer called.
	>>> topic2.passages
	[]
	>>> _remove_subtopic(topic2)
	Topic 'topic1': remove subtopic observer called.
	>>> _add_subtopic(manager, topic3)
	Topic 'None': add subtopic observer called.
	>>> _add_subtopic(topic1, topic2)
	Topic 'topic1': add subtopic observer called.
	>>> _add_passage(topic2, passage1)
	Topic 'topic1 > topic2': add passage observer called.

	Check that removing works when no subtopics or passages are selected.
	>>> _remove_subtopic(None)
	>>> _remove_passage(topic2, None)

	>>> _move_passage(passage1, topic1)
	Topic 'topic1 > topic2': remove passage observer called.
	Topic 'topic1': add passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> topic2.passages
	[]
	>>> passage1.parent
	<PassageList 'topic1'>

	>>> _move_topic(topic3, topic2)
	Topic 'None': remove subtopic observer called.
	Topic 'topic1 > topic2': add subtopic observer called.
	>>> topic2.subtopics
	[<PassageList 'topic3'>]

	>>> _copy_topic(topic3, manager)
	Topic 'None': add subtopic observer called.
	>>> manager.subtopics
	[<PassageList 'topic1'>, <PassageList 'topic3'>]
	>>> new_topic = manager.subtopics[1]
	>>> new_topic.name = "topic3 (test to see it was a genuine copy)"
	>>> topic3.name
	'topic3'
	>>> _copy_topic(topic1, new_topic)
	>>> new_topic.subtopics
	[<PassageList 'topic1'>]
	>>> new_topic.subtopics[0].passages
	[PassageEntry('Genesis 3:5', '')]
	>>> new_topic.subtopics[0].passages[0].comment = "test comment"
	>>> new_topic.subtopics[0].passages
	[PassageEntry('Genesis 3:5', 'test comment')]
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> new_topic.subtopics[0].subtopics[0]
	<PassageList 'topic2'>
	>>> new_topic.subtopics[0].subtopics[0].name = "xyz"
	>>> new_topic.subtopics[0].subtopics[0]
	<PassageList 'xyz'>
	>>> topic2.name
	'topic2'
	>>> topic3.subtopics
	[]

	Check copying or moving a topic into one of its children fails.
	>>> _copy_topic(topic1, topic3)
	Traceback (most recent call last):
	  File ...
	CircularDataException
	>>> _move_topic(topic1, topic3)
	Traceback (most recent call last):
	  File ...
	CircularDataException

	>>> _copy_passage(passage1, topic2)
	Topic 'topic1 > topic2': add passage observer called.
	>>> passage1.comment = "Test comment (to check it was a genuine copy)"
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]
	>>> topic2.passages
	[PassageEntry('Genesis 3:5', '')]

	Check moving to the same topic does nothing.
	>>> _move_passage(topic1.passages[0], topic1)
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]

	>>> _set_topic_name(topic1, "topic1 (new name)")
	Topic 'topic1 (new name)': name changed observer called.
	"""
	import manage_topics_operations, doctest	
	print doctest.testmod(manage_topics_operations)

from passage_list import PassageList, PassageEntry

class DummyOperationsManagerContext(object):
	"""Provides a dummy context, to be used in testing."""
	def __init__(self):
		self.selected_topic = None
		self.selected_passage = None
		self.is_passage_selected = False

	get_selected_topic = lambda self: self.selected_topic
	get_selected_passage = lambda self: self.selected_passage

	def get_selected_item(self):
		if self.is_passage_selected:
			return (self.selected_passage, PASSAGE_SELECTED)
		else:
			return (self.selected_topic, TOPIC_SELECTED)

def _test_create_topic(name="", description="", create_function=None):
	if create_function is None:
		create_function = lambda: PassageList(name, description)
	topic = create_function()
	topic.add_passage_observers += _topic_observer("add passage", topic)
	topic.remove_passage_observers += _topic_observer("remove passage", topic)
	topic.add_subtopic_observers += _topic_observer("add subtopic", topic)
	topic.remove_subtopic_observers += _topic_observer("remove subtopic", topic)
	topic.name_changed_observers += _topic_observer("name changed", topic)
	return topic

_test_create_passage = PassageEntry

def _topic_observer(operation, topic):
	def __observer(*args, **kwargs):
		print "Topic '%s': %s observer called." % (topic.full_name, operation)
	return __observer

if __name__ == "__main__":
	_test()
