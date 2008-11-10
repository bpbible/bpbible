from util.observerlist import ObserverList

PASSAGE_SELECTED = 1
TOPIC_SELECTED = 2

class ManageTopicsOperations(object):
	def __init__(self, context):
		self._context = context
		self._clipboard_data = None
		self._actions = []
		self._undone_actions = []
		self.undo_available_changed_observers = ObserverList()
		self.paste_available_changed_observers = ObserverList()

	def insert_item(self, item, type, index=None):
		parent_topic = self._context.get_selected_topic()
		self._perform_action(InsertAction(parent_topic, item, type, index))

	def move_current_passage(self, new_index):
		passage = self._context.get_selected_passage()
		self._perform_action(ReorderPassageAction(passage, new_index))

	# XXX: Deleting a topic doesn't remove its tags from the current window.
	def delete(self):
		item, type = self._context.get_selected_item()
		if not item:
			return

		self._perform_action(DeleteAction(item, type))

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
		self.paste_available_changed_observers()

	def paste(self):
		if not self._clipboard_data:
			return

		self.do_copy(self._clipboard_data.item,
				self._clipboard_data.type,
				self._context.get_selected_topic(),
				self._clipboard_data.keep_original)

		# It doesn't make sense to cut an object and then paste it in more
		# than one place, whereas it probably does make sense to copy it
		# and paste it in more than one place.
		if not self._clipboard_data.keep_original:
			self._clipboard_data = None
		self.paste_available_changed_observers()

	@property
	def can_paste(self):
		return self._clipboard_data is not None

	def do_copy(self, item, type, to_topic, keep_original):
		self._check_circularity(to_topic, item)
		if item.parent is to_topic:
			return

		self._perform_action(CopyAction(item, type, to_topic, keep_original))

	def undo(self):
		"""Undoes the most recently performed action."""
		if not self.can_undo:
			raise OperationNotAvailableError()
		recent_action = self._actions.pop()
		recent_action.undo_action()
		self._undone_actions.append(recent_action)
		self.undo_available_changed_observers()

	def redo(self):
		"""Redoes the most recently undone action."""
		if not self.can_redo:
			raise OperationNotAvailableError()
		undone_action = self._undone_actions.pop()
		undone_action.perform_action()
		self._actions.append(undone_action)
		self.undo_available_changed_observers()

	@property
	def can_undo(self):
		return bool(self._actions)

	@property
	def can_redo(self):
		return bool(self._undone_actions)

	def _perform_action(self, action):
		"""Performs the given action.
		
		The performed action is added to the list of performed actions, and
		can be undone later.
		"""
		action.perform_action()
		self._actions.append(action)
		self._undone_actions = []
		self.undo_available_changed_observers()

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

class Action(object):
	"""This class performs an action on a topic or passage.

	The action is stored so that it can later be undone.
	"""
	def __init__(self):
		self._action_performed = False

	def perform_action(self):
		"""Performs the action.

		Override _perform_action to make an action, since this does error
		checking.
		"""
		assert not self._action_performed
		self._action_performed = True
		self._perform_action()

	def _perform_action(self):
		"""Actually performs the action."""

	def undo_action(self):
		"""Undoes the action that has been done."""
		assert self._action_performed
		self._action_performed = False
		self._undo_action()

	def _undo_action(self):
		"""Actually undoes the action.

		Attempts to get an action to reverse the action and then performs
		that action.
		"""
		self._get_reverse_action().perform_action()

class CompositeAction(Action):
	"""This class performs and undoes a collection of individual actions.

	This can be used to implement actions on lists of items.
	It is also used to implement actions like copy and move in terms of
	primitives like insert and delete.
	"""
	def __init__(self, actions):
		super(CompositeAction, self).__init__()
		self._actions = actions

	def _perform_action(self):
		for action in self._actions:
			action.perform_action()

	def _undo_action(self):
		reversed_actions = self._actions[:]
		reversed_actions.reverse()
		for action in reversed_actions:
			action.undo_action()

class DeleteAction(Action):
	"""This action deletes a topic or passage."""
	def __init__(self, item, type):
		super(DeleteAction, self).__init__()
		self.item = item
		self.type = type

	def _perform_action(self):
		self.parent_topic = self.item.parent
		if self.type == PASSAGE_SELECTED:
			self.index = self.parent_topic.passages.index(self.item)
			self.parent_topic.remove_passage(self.item)
		else:
			self.index = self.parent_topic.subtopics.index(self.item)
			self.parent_topic.remove_subtopic(self.item)

	def _get_reverse_action(self):
		return InsertAction(self.parent_topic, self.item, self.type, self.index)

class InsertAction(Action):
	"""This action inserts a topic or passage at the given index of the given
	parent topic.
	"""
	def __init__(self, parent_topic, item, type, index):
		super(InsertAction, self).__init__()
		self.parent_topic = parent_topic
		self.item = item
		self.type = type
		self.index = index

	def _perform_action(self):
		if self.type == PASSAGE_SELECTED:
			self.parent_topic.insert_passage(self.item, self.index)
		else:
			# XXX: This doesn't use the supplied index.
			self.parent_topic.add_subtopic(self.item)

	def _get_reverse_action(self):
		return DeleteAction(self.item, self.type)

class CopyAction(CompositeAction):
	"""This action copies or moves a passage to a new topic."""
	def __init__(self, item, type, to_topic, keep_original):
		actions = []
		if keep_original:
			item = item.clone()
		else:
			actions.append(DeleteAction(item, type))
		actions.append(InsertAction(to_topic, item, type, index=None))
		super(CopyAction, self).__init__(actions)

class ReorderPassageAction(CompositeAction):
	"""This action moves a passage to a different index in the current topic."""
	def __init__(self, passage, new_index):
		topic = passage.parent
		super(ReorderPassageAction, self).__init__([
				DeleteAction(passage, PASSAGE_SELECTED),
				InsertAction(topic, passage, PASSAGE_SELECTED, new_index)
			])

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

class OperationNotAvailableError(Exception):
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
	>>> passage2 = _test_create_passage("gen 5:5")
	>>> operations_manager_context = DummyOperationsManagerContext()
	>>> operations_manager = ManageTopicsOperations(context=operations_manager_context)
	>>> operations_manager.can_undo
	False
	>>> operations_manager.can_redo
	False
	>>> operations_manager.undo()
	Traceback (most recent call last):
	  File ...
	OperationNotAvailableError
	>>> operations_manager.redo()
	Traceback (most recent call last):
	  File ...
	OperationNotAvailableError

	>>> operations_manager.can_paste
	False

	>>> def _add_subtopic(topic1, topic2, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic1
	... 	operations_manager.insert_item(topic2, TOPIC_SELECTED)
	...
	>>> def _remove_subtopic(topic2, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.is_passage_selected = False
	... 	operations_manager_context.selected_topic = topic2
	... 	operations_manager.delete()
	...
	>>> def _add_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_topic = topic
	... 	operations_manager.insert_item(passage, PASSAGE_SELECTED)
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
	>>> def _move_current_passage(passage, new_index, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.selected_passage = passage
	... 	operations_manager_context.selected_topic = passage.parent
	... 	operations_manager.move_current_passage(new_index)
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
	>>> operations_manager.undo()
	Topic 'None': remove subtopic observer called.
	>>> operations_manager.can_undo
	False
	>>> operations_manager.can_redo
	True
	>>> operations_manager.redo()
	Topic 'None': add subtopic observer called.
	>>> operations_manager.can_undo
	True
	>>> operations_manager.can_redo
	False
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
	>>> operations_manager.undo()
	Topic 'topic1': add subtopic observer called.
	>>> operations_manager.redo()
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
	>>> operations_manager.undo()
	Topic 'topic1': remove passage observer called.
	Topic 'topic1 > topic2': add passage observer called.
	>>> operations_manager.redo()
	Topic 'topic1 > topic2': remove passage observer called.
	Topic 'topic1': add passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> topic2.passages
	[]
	>>> passage1.parent
	<PassageList 'topic1'>

	Make sure that moving works, and that it doesn't allow you to paste after
	a move (though it does allow pasting after a copy).
	>>> _move_topic(topic3, topic2)
	Topic 'None': remove subtopic observer called.
	Topic 'topic1 > topic2': add subtopic observer called.
	>>> operations_manager.can_paste
	False
	>>> operations_manager.cut()
	>>> operations_manager.can_paste
	True
	>>> topic2.subtopics
	[<PassageList 'topic3'>]

	>>> _copy_topic(topic3, manager)
	Topic 'None': add subtopic observer called.
	>>> operations_manager.can_paste
	True
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
	>>> operations_manager.undo()
	Topic 'topic1 > topic2': remove passage observer called.
	>>> operations_manager.redo()
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
	>>> _add_passage(topic1, passage2)
	Topic 'topic1': add passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)'), PassageEntry('Genesis 5:5', '')]
	>>> _move_current_passage(passage2, 0)
	Topic 'topic1': remove passage observer called.
	Topic 'topic1': add passage observer called.
	>>> operations_manager.undo()
	Topic 'topic1': remove passage observer called.
	Topic 'topic1': add passage observer called.
	>>> operations_manager.redo()
	Topic 'topic1': remove passage observer called.
	Topic 'topic1': add passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', ''), PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]

	Check that you can't redo an action after undoing and doing a different
	action.
	>>> _remove_passage(topic1, topic1.passages[0])
	Topic 'topic1': remove passage observer called.
	>>> operations_manager.undo()
	Topic 'topic1': add passage observer called.
	>>> operations_manager.can_redo
	True
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', ''), PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]
	>>> _remove_passage(topic1, topic1.passages[1])
	Topic 'topic1': remove passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', '')]
	>>> operations_manager.can_redo
	False

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
