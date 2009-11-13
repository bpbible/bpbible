from util.observerlist import ObserverList
from passage_list import (BasePassageList, PassageList, PassageEntry,
		InvalidPassageError)
import sys

class ManageTopicsOperations(object):
	def __init__(self, passage_list_manager, context):
		self._context = context
		self._passage_list_manager = passage_list_manager
		self._clipboard_data = None
		self._actions = []
		self._undone_actions = []
		self.undo_available_changed_observers = ObserverList()
		self.paste_available_changed_observers = ObserverList()

	def insert_item(self, item, index=None, parent_topic=None):
		if parent_topic is None:
			parent_topic = self._context.get_selected_topic()
		item = self._context.get_wrapper(item)
		self._perform_action(InsertAction(parent_topic, item, index))

	def add_new_topic(self, creation_function=None):
		parent_topic = self._context.get_selected_topic()
		action = AddNewTopicAction(parent_topic, creation_function)
		self._perform_action(action)
		return action.topic

	def move_current_passage(self, new_index):
		passages = self._context.get_selected_passage()
		if not passages:
			return

		topic_passages = passages[0].parent.passages

		actions = []
		for passage in passages:
			if topic_passages.index(passage) <= new_index:
				new_index -= 1
			actions.append(ReorderPassageAction(_get_wrapper(passage), new_index))
			new_index += 1
		self._perform_action(CompositeAction(actions))
		self._passage_list_manager.save()

	# XXX: Deleting a topic doesn't remove its tags from the current window.
	def delete(self):
		item = self._context.get_new_selected_item()
		if not item:
			return

		self._perform_action(DeleteAction, action_item=item)

	def set_tag_look(self, topic, tag_look, tag_colour, combine_action=False):
		self.set_topic_details(
				topic, topic.name, topic.description, topic.order_passages_by,
				topic.display_tag, tag_look, tag_colour, combine_action=combine_action
			)

	def set_display_tag(self, topic, display_tag, combine_action=False):
		self.set_topic_details(
				topic, topic.name, topic.description, topic.order_passages_by,
				display_tag, topic.tag_look, topic.tag_colour, combine_action=combine_action
			)

	def set_order_passages_by(self, topic, order_passages_by, combine_action=False):
		self.set_topic_details(
				topic, topic.name, topic.description, order_passages_by,
				topic.display_tag, topic.tag_look, topic.tag_colour, combine_action=combine_action
			)

	def set_topic_name(self, topic, name, combine_action=False):
		self.set_topic_details(topic, name, topic.description, combine_action=combine_action)

	def set_topic_details(self, topic, name, description, order_passages_by=None, display_tag=None, tag_look="", tag_colour="", combine_action=False):
		if display_tag is None:
			display_tag = topic.display_tag
		if order_passages_by is None:
			order_passages_by = topic.order_passages_by
		if tag_look == "":
			# we compare with a default of "" not None, as None is a valid value
			tag_look = topic.tag_look
			tag_colour = topic.tag_colour
		self._perform_action(SetTopicDetailsAction(
				self._passage_list_manager, topic, name, description, order_passages_by, display_tag, tag_look, tag_colour
			), combine_action=combine_action)

	def set_passage_details(self, passage_entry, passage, comment, allow_undo=True, combine_action=False):
		self._perform_action(SetPassageDetailsAction(
				self._passage_list_manager, passage_entry, passage, comment
			), allow_undo=allow_undo, combine_action=combine_action)

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
		if not item:
			return

		item = self._context.get_wrapper(item)
		try:
			if item.is_child_topic(to_topic):
				raise CircularDataException()
		# Lists of passages do not have a method is_child_topic.
		except AttributeError:
			pass

		if isinstance(item, list):
			parent = item[0].parent
		else:
			parent = item.parent

		if parent is to_topic:
			return

		self._perform_action(
				lambda actual_item: CopyAction(actual_item, to_topic, keep_original),
				action_item=item,
			)

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

	def _perform_action(self, action, action_item=None, allow_undo=True, combine_action=False):
		"""Performs the given action.
		
		The performed action is added to the list of performed actions, and
		can be undone later.
		If the action is callable, then it will be called with the item.
		This is useful for building up a list of items in actual_item and
		creating a composite action.
		"""
		if callable(action):
			if isinstance(action_item, list):
				action = CompositeAction([action(item) for item in action_item])
			else:
				action = action(action_item)
		action.perform_action()
		self._passage_list_manager.save()
		if combine_action:
			assert self._actions
			self._actions[-1].combine_action(action)
			allow_undo = False

		if allow_undo:
			self._actions.append(action)
			self._undone_actions = []
			self.undo_available_changed_observers()

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

	def combine_action(self, action):
		"""Combines the given action with this action.
		
		Note that this just ignores the action.
		"""

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

	def combine_action(self, action):
		if not isinstance(action, SetPassageDetailsAction):
			return

		self.passage = action.passage
		self.comment = action.comment

	def _perform_action(self):
		self.old_passage = self.passage_entry.passage
		self.old_comment = self.passage_entry.comment
		exception = None
		try:
			self.passage_entry.passage = self.passage
		except InvalidPassageError, e:
			exception = e
		self.passage_entry.comment = self.comment
		self.manager.save_item(self.passage_entry)
		if exception is not None:
			raise exception

	def _get_reverse_action(self):
		return SetPassageDetailsAction(self.manager, self.passage_entry, self.old_passage, self.old_comment)

class SetTopicDetailsAction(Action):
	def __init__(self, manager, topic, name, description, order_passages_by, display_tag, tag_look, tag_colour):
		super(SetTopicDetailsAction, self).__init__()
		self.topic = topic
		self.name = name
		self.description = description
		self.order_passages_by = order_passages_by
		self.display_tag = display_tag
		self.tag_look = tag_look
		self.tag_colour = tag_colour
		self.manager = manager

	def combine_action(self, action):
		if not isinstance(action, SetTopicDetailsAction):
			return

		self.name = action.name
		self.description = action.description

	def _perform_action(self):
		self.old_name = self.topic.name
		self.old_description = self.topic.description
		self.old_display_tag = self.topic.display_tag
		self.old_tag_look = self.topic.tag_look
		self.old_tag_colour = self.topic.tag_colour
		self.old_order_passages_by = self.topic.order_passages_by
		self.topic.name = self.name
		self.topic.description = self.description
		self.topic.order_passages_by = self.order_passages_by
		self.topic.display_tag = self.display_tag
		self.topic.tag_look = self.tag_look
		self.topic.tag_colour = self.tag_colour
		self.manager.save_item(self.topic)

	def _get_reverse_action(self):
		return SetTopicDetailsAction(
				self.manager, self.topic,
				self.old_name, self.old_description, self.old_order_passages_by, self.old_display_tag,
				self.old_tag_look, self.old_tag_colour
			)

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
	>>> from swlib.pysw import VerseList
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
	>>> def _remove_passage(passage, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
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
	>>> def _set_topic_details(topic, name, description, combine_action=False, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager.set_topic_details(topic, name, description, combine_action=combine_action)
	...
	>>> def _set_passage_details(passage_entry, passage, comment, combine_action=False, operations_manager_context=operations_manager_context, operations_manager=operations_manager):
	... 	operations_manager.set_passage_details(passage_entry, passage, comment, combine_action=combine_action)
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
	>>> _remove_passage(passage1)
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
	>>> _remove_passage(None)

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
	>>> _move_current_passage([passage2], 0)
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
	>>> _remove_passage(topic1.passages[0])
	Topic 'topic1': remove passage observer called.
	>>> operations_manager.undo()
	Topic 'topic1': add passage observer called.
	>>> operations_manager.can_redo
	True
	>>> topic1.passages
	[PassageEntry('Genesis 5:5', ''), PassageEntry('Genesis 3:5', '')]
	>>> _remove_passage(topic1.passages[1])
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
	>>> topic1.display_tag
	True
	>>> operations_manager.set_display_tag(topic1, False)
	>>> topic1.display_tag
	False
	>>> operations_manager.undo()
	>>> topic1.display_tag
	True

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
	>>> _check_get_all_passage_entries_for_verse(manager, manager)

	Check creating a new topic.  This must create a default topic, but then
	combine it with the next edit item action if necessary so that undo
	undoes the new topic action, not the "edit the new topic that was
	created" action.
	>>> new_topic = _add_new_topic(topic1)
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> _set_topic_details(new_topic, "New Topic Name (1)", "description", combine_action=True)
	>>> new_topic.name
	'New Topic Name (1)'
	>>> new_topic.description
	'description'
	>>> _set_topic_details(new_topic, "New Topic Name", "description", combine_action=True)
	>>> operations_manager.undo()
	Topic 'topic1 (new name)': remove subtopic observer called.
	>>> operations_manager.redo()
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> topic1.subtopics
	[<PassageList 'topic2'>, <PassageList 'New Topic Name'>]

	Check operations work over multiple passages.
	>>> topic_zzz = _test_create_topic(name="ZZZ")
	>>> topic_zzz2 = _test_create_topic(name="ZZZ2")
	>>> _add_subtopic(manager, topic_zzz)
	Topic 'None': add subtopic observer called.
	>>> _add_subtopic(manager, topic_zzz2)
	Topic 'None': add subtopic observer called.
	>>> _add_passage(topic_zzz, PassageEntry(VerseList("ex 2:2")))
	Topic 'ZZZ': add passage observer called.
	>>> _add_passage(topic_zzz, PassageEntry(VerseList("ex 2:3")))
	Topic 'ZZZ': add passage observer called.
	>>> _add_passage(topic_zzz, PassageEntry(VerseList("ex 2:4")))
	Topic 'ZZZ': add passage observer called.
	>>> topic_zzz.passages
	[PassageEntry('Exodus 2:2', ''), PassageEntry('Exodus 2:3', ''), PassageEntry('Exodus 2:4', '')]
	>>> passage_subset = [topic_zzz.passages[0], topic_zzz.passages[2]]
	>>> _remove_passage(passage_subset)
	Topic 'ZZZ': remove passage observer called.
	Topic 'ZZZ': remove passage observer called.
	>>> topic_zzz.passages
	[PassageEntry('Exodus 2:3', '')]
	>>> operations_manager.undo()
	Topic 'ZZZ': add passage observer called.
	Topic 'ZZZ': add passage observer called.
	>>> _copy_passage(passage_subset, topic_zzz2)
	Topic 'ZZZ2': add passage observer called.
	Topic 'ZZZ2': add passage observer called.
	>>> _move_passage(passage_subset, topic_zzz2)
	Topic 'ZZZ': remove passage observer called.
	Topic 'ZZZ2': add passage observer called.
	Topic 'ZZZ': remove passage observer called.
	Topic 'ZZZ2': add passage observer called.
	>>> topic_zzz.passages
	[PassageEntry('Exodus 2:3', '')]
	>>> topic_zzz2.passages
	[PassageEntry('Exodus 2:2', ''), PassageEntry('Exodus 2:4', ''), PassageEntry('Exodus 2:2', ''), PassageEntry('Exodus 2:4', '')]
	>>> _set_passage_details(topic_zzz2.passages[0], VerseList("lev 3:3"), "")
	>>> topic_zzz2.passages
	[PassageEntry('Leviticus 3:3', ''), PassageEntry('Exodus 2:4', ''), PassageEntry('Exodus 2:2', ''), PassageEntry('Exodus 2:4', '')]
	>>> operations_manager.undo()
	>>> operations_manager.undo()
	Topic 'ZZZ2': remove passage observer called.
	Topic 'ZZZ': add passage observer called.
	Topic 'ZZZ2': remove passage observer called.
	Topic 'ZZZ': add passage observer called.
	>>> operations_manager.undo()
	Topic 'ZZZ2': remove passage observer called.
	Topic 'ZZZ2': remove passage observer called.
	>>> topic_zzz.passages
	[PassageEntry('Exodus 2:2', ''), PassageEntry('Exodus 2:3', ''), PassageEntry('Exodus 2:4', '')]
	>>> _move_current_passage([topic_zzz.passages[1], topic_zzz.passages[2]], 0)
	Topic 'ZZZ': remove passage observer called.
	Topic 'ZZZ': add passage observer called.
	Topic 'ZZZ': remove passage observer called.
	Topic 'ZZZ': add passage observer called.
	>>> topic_zzz.passages
	[PassageEntry('Exodus 2:3', ''), PassageEntry('Exodus 2:4', ''), PassageEntry('Exodus 2:2', '')]
	>>> _check_get_all_passage_entries_for_verse(manager, manager)

	Check that they work over no passages too:
	>>> _remove_passage([])
	>>> _move_passage([], topic_zzz2)
	>>> _copy_passage([], topic_zzz2)

	Clean up afterwards
	>>> _remove_subtopic(topic_zzz)
	Topic 'None': remove subtopic observer called.
	>>> _remove_subtopic(topic_zzz2)
	Topic 'None': remove subtopic observer called.

	Test that the creation function works.
	>>> new_topic = _add_new_topic(topic1, lambda: PassageList(name="abc", description="description"))
	Topic 'topic1 (new name)': add subtopic observer called.
	>>> new_topic.name
	'abc'
	>>> new_topic.description
	'description'

	>>> _set_passage_details(passage1, VerseList("gen 8:8"), "comment.", combine_action=False)
	Passage 'Genesis 8:8': passage changed observer called.
	Passage 'Genesis 8:8': comment changed observer called.
	>>> _set_passage_details(passage1, VerseList("gen 8:8"), "comment 2.", combine_action=True)
	Passage 'Genesis 8:8': comment changed observer called.
	>>> operations_manager.undo()
	Passage 'Genesis 3:5': passage changed observer called.
	Passage 'Genesis 3:5': comment changed observer called.
	>>> new_passage = PassageEntry(VerseList("gen 9:2"))
	>>> _add_passage(manager.subtopics[2], new_passage)
	>>> _set_passage_details(new_passage, VerseList("gen 8:8"), "", combine_action=True)
	>>> _set_passage_details(new_passage, VerseList("gen 8:8"), "comment.", combine_action=True)
	>>> _set_passage_details(new_passage, VerseList("gen 8:8"), "comment 2.", combine_action=False)
	>>> str(new_passage)
	'Genesis 8:8'
	>>> new_passage.comment
	'comment 2.'
	>>> operations_manager.undo()
	>>> str(new_passage)
	'Genesis 8:8'
	>>> new_passage.comment
	'comment.'
	>>> manager.subtopics[2].passages[-1]
	PassageEntry('Genesis 8:8', 'comment.')
	>>> operations_manager.undo()
	>>> manager.subtopics[2].passages[-1]
	PassageEntry('Genesis 50:1', '')

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

	>>> _check_get_all_passage_entries_for_verse(loaded_manager, loaded_manager)
	
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
	>>> _remove_passage(passage1)
	>>> _set_topic_details(topic1, "New Topic Name", "description")
	>>> _set_passage_details(passage1, "Genesis 3:3", "description")
	>>> _set_passage_details(passage1, "Genesis 3:4 - 5, 7, 9", "description")
	
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
	elif isinstance(item, list):
		if len(item) == 1:
			return _get_wrapper(item[0])
		else:
			return [_get_wrapper(subitem) for subitem in item]
	else:
		return item

class PassageWrapper(object):
	def __init__(self, passage):
		self._passage = passage
		self.wrapped = passage

	@property
	def parent(self):
		return self._passage.parent

	def insert_into_topic(self, parent_topic, index):
		parent_topic.insert_passage(self._passage, index)

	def is_child_topic(self, topic):
		return False

	def find_index(self):
		return self._passage.parent._natural_order_passages.index(self._passage)

	def remove_from_parent(self):
		self._passage.parent.remove_passage(self._passage)

	def clone(self):
		return PassageWrapper(self._passage.clone())

class TopicWrapper(object):
	def __init__(self, topic):
		self._topic = topic
		self.wrapped = topic

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

def _check_get_all_passage_entries_for_verse(manager, topic):
	for passage_entry in topic.passages:
		for verse_key in passage_entry.passage:
			for verse in verse_key:
				assert (passage_entry in manager.get_all_passage_entries_for_verse(verse),
					repr(passage_entry) + " not contained in " + str(verse))
	for subtopic in topic.subtopics:
		_check_get_all_passage_entries_for_verse(manager, subtopic)

if __name__ == "__main__":
	_test()
