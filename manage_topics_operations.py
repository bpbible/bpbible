PASSAGE_SELECTED = 1
TOPIC_SELECTED = 2

class ManageTopicsOperations(object):
	def __init__(self, context):
		self._context = context

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

	def move_passage(self, from_topic, passage, to_topic):
		from_topic.remove_passage(passage)
		to_topic.add_passage(passage)

	def copy_passage(self, from_topic, passage, to_topic):
		to_topic.add_passage(passage.clone())

	def set_topic_name(self, name):
		self._context.get_selected_topic().name = name

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
	... 	operations_manager_context.selected_topic = topic2
	... 	operations_manager.remove_subtopic()
	...
	>>> def _add_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.add_passage(passage)
	...
	>>> def _remove_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.remove_passage()
	...
	>>> def _move_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.remove_passage()
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

	#>>> _move_passage(topic2, passage1, topic1)
	Topic 'topic1 > topic2': remove passage observer called.
	Topic 'topic1': add passage observer called.
	#>>> topic1.passages
	[PassageEntry('Genesis 3:5', '')]
	#>>> topic2.passages
	[]
	#>>> _copy_passage(topic1, passage1, topic2)
	Topic 'topic1 > topic2': add passage observer called.
	#>>> passage1.comment = "Test comment (to check it was a genuine copy)"
	#>>> topic1.passages
	[PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]
	#>>> topic2.passages
	[PassageEntry('Genesis 3:5', '')]
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
