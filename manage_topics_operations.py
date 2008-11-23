from util.observerlist import ObserverList
from passage_list import (BasePassageList, PassageList, PassageEntry,
		InvalidPassageError, MultiplePassagesError)

class ManageTopicsOperations(object):
	def __init__(self, passage_list_manager, context):
		self._context = context
		self._passage_list_manager = passage_list_manager
		self._clipboard_data = None
		self._actions = []
		self._undone_actions = []
		self.undo_available_changed_observers = ObserverList()
		self.paste_available_changed_observers = ObserverList()
		self._merge_next_edit_action = False

	def insert_item(self, item, index=None):
		parent_topic = self._context.get_selected_topic()
		item = self._context.get_wrapper(item)
		self._perform_action(InsertAction(parent_topic, item, index))

	def add_new_topic(self, creation_function=None):
		parent_topic = self._context.get_selected_topic()
		action = AddNewTopicAction(parent_topic, creation_function)
		self._perform_action(action, merge_next_edit_action=True)
		return action.topic

	def move_current_passage(self, new_index):
		passage = self._context.get_selected_passage()
		passage = self._context.get_wrapper(passage)
		self._perform_action(ReorderPassageAction(passage, new_index))
		self._passage_list_manager.save()

	# XXX: Deleting a topic doesn't remove its tags from the current window.
	def delete(self):
		item = self._context.get_new_selected_item()
		if not item:
			return

		self._perform_action(DeleteAction(item))

	def set_topic_name(self, topic, name):
		self.set_topic_details(topic, name, topic.description)

	def set_topic_details(self, topic, name, description):
		self._perform_action(SetTopicDetailsAction(
				self._passage_list_manager, topic, name, description
			))

	def set_passage_details(self, passage_entry, passage, comment, allow_undo=True):
		self._perform_action(SetPassageDetailsAction(
				self._passage_list_manager, passage_entry, passage, comment
			), allow_undo=allow_undo)

	def cut(self):
		self._setup_clipboard(keep_original=False)

	def copy(self):
		self._setup_clipboard(keep_original=True)

	def _setup_clipboard(self, keep_original):
		item = self._context.get_new_selected_item()
		if not item:
			return

		self._clipboard_data = ClipboardData(
				item, keep_original=keep_original)
		self.paste_available_changed_observers()

	def paste(self):
		if not self._clipboard_data:
			return

		self.do_copy(self._clipboard_data.item,
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

	def do_copy(self, item, to_topic, keep_original):
		"""Performs the actual copy operation as an action.

		If a topic is copied to one of its children, a CircularDataException
		will be thrown.
		"""
		item = self._context.get_wrapper(item)
		if item.is_child_topic(to_topic):
			raise CircularDataException()

		if item.parent is to_topic:
			return

		self._perform_action(CopyAction(item, to_topic, keep_original))

	def undo(self):
		"""Undoes the most recently performed action."""
		if not self.can_undo:
			raise OperationNotAvailableError()
		recent_action = self._actions.pop()
		recent_action.undo_action()
		self._passage_list_manager.save()
		self._undone_actions.append(recent_action)
		self.undo_available_changed_observers()

	def redo(self):
		"""Redoes the most recently undone action."""
		if not self.can_redo:
			raise OperationNotAvailableError()
		undone_action = self._undone_actions.pop()
		undone_action.perform_action()
		self._passage_list_manager.save()
		self._actions.append(undone_action)
		self.undo_available_changed_observers()

	@property
	def can_undo(self):
		return bool(self._actions)

	@property
	def can_redo(self):
		return bool(self._undone_actions)

	def _perform_action(self, action, merge_next_edit_action=False, allow_undo=True):
		"""Performs the given action.
		
		The performed action is added to the list of performed actions, and
		can be undone later.
		"""
		action.perform_action()
		self._passage_list_manager.save()
		merge_action = (self._merge_next_edit_action
				and isinstance(action, SetTopicDetailsAction))
		if not merge_action and allow_undo:
			self._actions.append(action)
			self._undone_actions = []
			self.undo_available_changed_observers()
		self._merge_next_edit_action = merge_next_edit_action

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
	def __init__(self, item):
		super(DeleteAction, self).__init__()
		self.item = item

	def _perform_action(self):
		self.parent_topic = self.item.parent
		self.index = self.item.find_index()
		self.item.remove_from_parent()

	def _get_reverse_action(self):
		return InsertAction(self.parent_topic, self.item, self.index)

class InsertAction(Action):
	"""This action inserts a topic or passage at the given index of the given
	parent topic.
	"""
	def __init__(self, parent_topic, item, index):
		super(InsertAction, self).__init__()
		self.parent_topic = parent_topic
		self.item = item
		self.index = index

	def _perform_action(self):
		self.item.insert_into_topic(self.parent_topic, self.index)

	def _get_reverse_action(self):
		return DeleteAction(self.item)

class AddNewTopicAction(Action):
	def __init__(self, parent_topic, creation_function):
		super(AddNewTopicAction, self).__init__()
		self.parent_topic = parent_topic
		if creation_function is None:
			creation_function = lambda: PassageList(
					name="New Topic", description=""
				)
		self.topic = creation_function()

	def _perform_action(self):
		self.parent_topic.add_subtopic(self.topic)

	def _get_reverse_action(self):
		return DeleteAction(_get_wrapper(self.topic))

class SetPassageDetailsAction(Action):
	def __init__(self, manager, passage_entry, passage, comment):
		super(SetPassageDetailsAction, self).__init__()
		self.passage_entry = passage_entry
		self.passage = passage
		self.comment = comment
		self.manager = manager

	def _perform_action(self):
		self.old_passage = self.passage_entry.passage
		self.old_comment = self.passage_entry.comment
		exception = None
		try:
			self.passage_entry.passage = self.passage
		except (InvalidPassageError, MultiplePassagesError), e:
			exception = e
		self.passage_entry.comment = self.comment
		self.manager.save_item(self.passage_entry)
		if exception is not None:
			raise exception

	def _get_reverse_action(self):
		return SetPassageDetailsAction(self.manager, self.passage_entry, self.old_passage, self.old_comment)

class SetTopicDetailsAction(Action):
	def __init__(self, manager, topic, name, description):
		super(SetTopicDetailsAction, self).__init__()
		self.topic = topic
		self.name = name
		self.description = description
		self.manager = manager

	def _perform_action(self):
		self.old_name = self.topic.name
		self.old_description = self.topic.name
		self.topic.name = self.name
		self.topic.description = self.description
		self.manager.save_item(self.topic)

	def _get_reverse_action(self):
		return SetTopicDetailsAction(self.manager, self.topic, self.old_name, self.old_description)

class CopyAction(CompositeAction):
	"""This action copies or moves a passage to a new topic."""
	def __init__(self, item, to_topic, keep_original):
		actions = []
		if keep_original:
			item = item.clone()
		else:
			actions.append(DeleteAction(item))
		actions.append(InsertAction(to_topic, item, index=None))
		super(CopyAction, self).__init__(actions)

class ReorderPassageAction(CompositeAction):
	"""This action moves a passage to a different index in the current topic."""
	def __init__(self, passage, new_index):
		topic = passage.parent
		super(ReorderPassageAction, self).__init__([
				DeleteAction(passage),
				InsertAction(topic, passage, new_index)
			])

class ClipboardData(object):
	"""This class manages the item that is currently in the clipboard."""
	def __init__(self, item, keep_original):
		self.item = item
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
	>>> __builtins__['_'] = lambda x: x
	>>> from passage_list import get_primary_passage_list_manager
	>>> import os
	>>> filename = "passages_test.sqlite"
	>>> try:
	... 	os.remove(filename)
	... except OSError:
	... 	pass
	...
	>>> manager = get_primary_passage_list_manager(filename)
	>>> _add_topic_observers(manager)
	>>> manager.subtopics
	[]
	>>> manager.passages
	[]
	>>> topic1 = _test_create_topic("topic1")
	>>> topic2 = _test_create_topic("topic2")
	>>> topic3 = _test_create_topic("topic3")
	>>> passage1 = _test_create_passage("gen 3:5")
	>>> passage2 = _test_create_passage("gen 5:5")
	>>> operations_manager_context = DummyOperationsManagerContext()
	>>> operations_manager = ManageTopicsOperations(manager, context=operations_manager_context)
	>>> manager = get_primary_passage_list_manager(filename)
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
	... 	operations_manager_context.set_selected_topic(topic1)
	... 	operations_manager.insert_item(topic2)
	...
	>>> def _remove_subtopic(topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_topic(topic)
	... 	operations_manager.delete()
	...
	>>> def _add_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_topic(topic)
	... 	operations_manager.insert_item(passage)
	...
	>>> def _remove_passage(topic, passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_passage(passage)
	... 	operations_manager.delete()
	...
	>>> def _move_passage(passage, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_passage(passage)
	... 	operations_manager.cut()
	... 	operations_manager_context.set_selected_topic(target_topic)
	... 	operations_manager.paste()
	...
	>>> def _move_current_passage(passage, new_index, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_passage(passage)
	... 	operations_manager.move_current_passage(new_index)
	...
	>>> def _move_topic(topic, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_topic(topic)
	... 	operations_manager.cut()
	... 	operations_manager_context.set_selected_topic(target_topic)
	... 	operations_manager.paste()
	...
	>>> def _copy_topic(topic, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_topic(topic)
	... 	operations_manager.copy()
	... 	operations_manager_context.set_selected_topic(target_topic)
	... 	operations_manager.paste()
	...
	>>> def _add_new_topic(parent_topic, creation_function=None, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_topic(parent_topic)
	... 	return operations_manager.add_new_topic(creation_function)
	...
	>>> def _copy_passage(passage, target_topic, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager_context.set_selected_passage(passage)
	... 	operations_manager.copy()
	... 	operations_manager_context.set_selected_topic(target_topic)
	... 	operations_manager.paste()
	...
	>>> def _set_topic_name(topic, name, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager.set_topic_name(topic, name)
	...
	>>> def _set_topic_details(topic, name, description, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager.set_topic_details(topic, name, description)
	...
	>>> def _set_passage_details(passage_entry, passage, comment, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager.set_passage_details(passage_entry, passage, comment)
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
	>>> new_topic.name = "topic3"
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
	>>> new_topic.subtopics[0].passages[0].comment = ""
	>>> new_topic.subtopics[0].subtopics[0]
	<PassageList 'topic2'>
	>>> new_topic.subtopics[0].subtopics[0].name = "xyz"
	>>> new_topic.subtopics[0].subtopics[0]
	<PassageList 'xyz'>
	>>> new_topic.subtopics[0].subtopics[0].name = "topic2"
	>>> topic2.name
	'topic2'
	>>> topic3.subtopics
	[]

	>>> _set_passage_details(passage2, str(passage2), '')
	>>> passage2.comment
	''
	>>> new_topic = PassageList.create_from_verse_list("Test", ["gen %s" % number for number in range(1, 51)])
	>>> _add_subtopic(manager, new_topic)
	Topic 'None': add subtopic observer called.
	>>> len(new_topic.passages)
	50
	>>> manager.subtopics
	[<PassageList 'topic1'>, <PassageList 'topic3'>, <PassageList 'Test'>]

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
	Passage 'Genesis 3:5': comment changed observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', 'Test comment (to check it was a genuine copy)')]
	>>> topic2.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> passage1.comment = ""
	Passage 'Genesis 3:5': comment changed observer called.

	Check moving to the same topic does nothing.
	>>> _move_passage(topic1.passages[0], topic1)
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', '')]
	>>> _add_passage(topic1, passage2)
	Topic 'topic1': add passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 3:5', ''), PassageEntry('Genesis 5:5', '')]
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
	[PassageEntry('Genesis 5:5', ''), PassageEntry('Genesis 3:5', '')]

	Check that you can't redo an action after undoing and doing a different
	action.
	>>> _remove_passage(topic1, topic1.passages[0])
	Topic 'topic1': remove passage observer called.
	>>> operations_manager.undo()
	Topic 'topic1': add passage observer called.
	>>> operations_manager.can_redo
	True
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', ''), PassageEntry('Genesis 3:5', '')]
	>>> _remove_passage(topic1, topic1.passages[1])
	Topic 'topic1': remove passage observer called.
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', '')]
	>>> operations_manager.can_redo
	False

	>>> _set_topic_details(topic1, "topic1", "New description.")
	Topic 'topic1': description changed observer called.
	>>> topic1.name
	'topic1'
	>>> topic1.description
	'New description.'
	>>> _set_topic_name(topic1, "topic1 (new name)")
	Topic 'topic1 (new name)': name changed observer called.

	>>> _set_passage_details(passage2, "Gen 5:5", "comment")
	Passage 'Genesis 5:5': comment changed observer called.
	>>> operations_manager.undo()
	Passage 'Genesis 5:5': comment changed observer called.
	>>> operations_manager.redo()
	Passage 'Genesis 5:5': comment changed observer called.
	>>> str(passage2)
	'Genesis 5:5'
	>>> passage2.comment
	'comment'
	>>> _set_passage_details(passage2, "Gen 9:5", "new comment")
	Passage 'Genesis 9:5': passage changed observer called.
	Passage 'Genesis 9:5': comment changed observer called.
	>>> str(passage2)
	'Genesis 9:5'
	>>> passage2.comment
	'new comment'

	Check setting an invalid passage will throw an exception, but will
	also set the comment correctly.
	>>> _set_passage_details(passage2, "garbled verse 9:5", "newer comment")
	Traceback (most recent call last):
	  File ...
	InvalidPassageError
	>>> str(passage2)
	'Genesis 9:5'
	>>> passage2.comment
	'newer comment'

	Check creating a new topic.  This must create a default topic, but then
	combine it with the next edit item action if necessary so that undo
	undoes the new topic action, not the "edit the new topic that was
	created" action.
	>>> new_topic = _add_new_topic(topic1)
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> _set_topic_details(new_topic, "New Topic Name", "description")
	>>> new_topic.name
	'New Topic Name'
	>>> new_topic.description
	'description'
	>>> operations_manager.undo()
	Topic 'topic1 (new name)': remove subtopic observer called.
	>>> operations_manager.redo()
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> topic1.subtopics
	[<PassageList 'topic2'>, <PassageList 'New Topic Name'>]

	Test that the creation function works.
	>>> new_topic = _add_new_topic(topic1, lambda: PassageList(name="abc", description="description"))
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> new_topic.name
	'abc'
	>>> new_topic.description
	'description'
	>>> _remove_subtopic(new_topic)
	Topic 'topic1 (new name)': remove subtopic observer called.
	>>> _remove_subtopic(manager.subtopics[1])
	Topic 'None': remove subtopic observer called.
	>>> manager.save()
	>>> manager.close()
	>>> from passage_list import sqlite
	>>> loaded_manager = sqlite.load_manager(filename)
	>>> loaded_manager.subtopics
	[<PassageList u'topic1 (new name)'>, <PassageList u'Test'>]
	>>> manager.subtopics
	[<PassageList 'topic1 (new name)'>, <PassageList 'Test'>]

	>>> loaded_manager == manager
	True
	
	>>> loaded_manager.close()

	>>> filename2 = "passages_test2.sqlite"
	>>> try:
	... 	os.remove(filename2)
	... except OSError, e:
	... 	pass
	...
	>>> manager = get_primary_passage_list_manager(filename2)
	>>> manager.subtopics
	[]
	>>> manager.passages
	[]
	>>> operations_manager._passage_list_manager = manager
	>>> from passage_list import PassageList
	>>> topic1 = PassageList("topic1")
	>>> _add_subtopic(manager, topic1)
	>>> topic2 = PassageList("topic2")
	>>> _add_subtopic(topic1, topic2)
	>>> passage1 = PassageEntry("gen 3:3 - 7")
	>>> passage2 = PassageEntry("gen 3:7 - 21")
	>>> _add_passage(topic1, passage1)
	>>> _add_passage(topic1, passage2)
	>>> _remove_passage(topic1, passage1)
	>>> _set_topic_details(topic1, "New Topic Name", "description")
	>>> _set_passage_details(passage1, "Genesis 3:3", "description")
	
	>>> _copy_topic(topic2, manager)
	>>> _remove_subtopic(topic2)

	>>> _copy_topic(topic1, manager.subtopics[1])

	>>> _remove_subtopic(topic1)

	>>> operations_manager.undo()
	>>> manager.close()
	>>> loaded_manager = sqlite.load_manager(filename2)

	>>> manager == loaded_manager
	True
	"""
	import manage_topics_operations, doctest	
	print doctest.testmod(manage_topics_operations)

from passage_list import PassageList, PassageEntry

class BaseOperationsContext(object):
	def get_selected_topic(self):
		raise NotImplementedError()

	def get_selected_passage(self):
		raise NotImplementedError()

	def is_passage_selected(self):
		raise NotImplementedError()

	def get_new_selected_item(self):
		if self.is_passage_selected():
			item = self.get_selected_passage()
		else:
			item = self.get_selected_topic()
		return self.get_wrapper(item)

	def get_wrapper(self, item):
		return _get_wrapper(item)

def _get_wrapper(item):
	if not item:
		return None

	if isinstance(item, PassageEntry):
		return PassageWrapper(item)
	elif isinstance(item, BasePassageList):
		return TopicWrapper(item)
	else:
		return item

class PassageWrapper(object):
	def __init__(self, passage):
		self._passage = passage
		self.wrapped = passage

	def get_name(self):
		return str(self._passage)

	def set_name(self, passage):
		self._passage.passage = passage

	name = property(get_name, set_name)

	def get_description(self):
		return self._passage.comment

	def set_description(self, comment):
		self._passage.comment = comment

	description = property(get_description, set_description)

	@property
	def parent(self):
		return self._passage.parent

	def insert_into_topic(self, parent_topic, index):
		parent_topic.insert_passage(self._passage, index)

	def is_child_topic(self, topic):
		return False

	def find_index(self):
		return self._passage.parent.passages.index(self._passage)

	def remove_from_parent(self):
		self._passage.parent.remove_passage(self._passage)

	def clone(self):
		return PassageWrapper(self._passage.clone())

class TopicWrapper(object):
	def __init__(self, topic):
		self._topic = topic
		self.wrapped = topic

	def get_name(self):
		return self._topic.name

	def set_name(self, name):
		self._topic.name = name

	name = property(get_name, set_name)

	def get_description(self):
		return self._topic.description

	def set_description(self, description):
		self._topic.description = description

	description = property(get_description, set_description)

	@property
	def parent(self):
		return self._topic.parent

	def insert_into_topic(self, parent_topic, index):
		parent_topic.insert_subtopic(self._topic, index)

	def is_child_topic(self, topic):
		"""Checks if the given topic is a child of this topic.

		If this is the case, then we can't copy to the given topic.
		"""
		topic_parent = topic
		while topic_parent is not None:
			if topic_parent is self._topic:
				return True
			topic_parent = topic_parent.parent
		return False

	def find_index(self):
		return self._topic.parent.subtopics.index(self._topic)

	def remove_from_parent(self):
		self._topic.parent.remove_subtopic(self._topic)

	def clone(self):
		return TopicWrapper(self._topic.clone())

class DummyOperationsManagerContext(BaseOperationsContext):
	"""Provides a dummy context, to be used in testing."""
	def __init__(self):
		self.selected_topic = None
		self.selected_passage = None
		self._is_passage_selected = False

	get_selected_topic = lambda self: self.selected_topic
	get_selected_passage = lambda self: self.selected_passage

	def set_selected_topic(self, topic):
		self.selected_topic = topic
		self._is_passage_selected = False

	def set_selected_passage(self, passage):
		self.selected_passage = passage
		self._is_passage_selected = True

	def is_passage_selected(self):
		return self._is_passage_selected

	@property
	def parent(self):
		return self._passage.parent

def _test_create_topic(name="", description="", create_function=None):
	if create_function is None:
		create_function = lambda: PassageList(name, description)
	topic = create_function()
	_add_topic_observers(topic)
	return topic

def _add_topic_observers(topic):
	topic.add_passage_observers += _topic_observer("add passage", topic)
	topic.remove_passage_observers += _topic_observer("remove passage", topic)
	topic.add_subtopic_observers += _topic_observer("add subtopic", topic)
	topic.remove_subtopic_observers += _topic_observer("remove subtopic", topic)
	topic.name_changed_observers += _topic_observer("name changed", topic)
	topic.description_changed_observers += _topic_observer("description changed", topic)

def _test_create_passage(passage="", comment=""):
	passage = PassageEntry(passage, comment)
	passage.passage_changed_observers += _passage_observer("passage changed", passage)
	passage.comment_changed_observers += _passage_observer("comment changed", passage)
	return passage

def _topic_observer(operation, topic):
	def __observer(*args, **kwargs):
		print "Topic '%s': %s observer called." % (topic.full_name, operation)
	return __observer

def _passage_observer(operation, passage):
	def __observer(*args, **kwargs):
		print "Passage '%s': %s observer called." % (passage, operation)
	return __observer

if __name__ == "__main__":
	_test()
