from passage_entry import PassageEntry
from util.observerlist import ObserverList
import sqlite

_passage_list_id_dict = {}

class BasePassageList(object):
	"""This provides the basic passage list functionality.

	This functionality is used by both passage lists and the passage list
	manager.  It involves the management of passage lists that are contained
	by the list, including an observer list for observers of new subtopics
	being added.
	"""
	contains_passages = True
	__table__ = "topic"
	__fields_to_store__ = ["name", "description", "order_number", "parent"]

	def __init__(self, description=""):
		self._description = description
		self.parent = None
		self.name_changed_observers = ObserverList()
		self.description_changed_observers = ObserverList()
		self.subtopics = []
		self._name = ""
		self.add_subtopic_observers = ObserverList()
		self.remove_subtopic_observers = ObserverList()

		global _passage_list_id_dict
		_passage_list_id_dict[self.get_id()] = self

		self.passages = []
		self.add_passage_observers = ObserverList()
		self.remove_passage_observers = ObserverList()
		self.id = None
		self.order_number = 0
	
	def add_subtopic(self, subtopic):
		"""Adds the given sub-topic to the end of the list of sub-topics."""
		self.insert_subtopic(subtopic, index=None)
	
	def insert_subtopic(self, subtopic, index):
		"""Inserts the given subtopic into the list of subtopics.
		
		index: The index to insert the subtopic before.
			If this is None, then the subtopic will be appended to the list.
		"""
		if index is None:
			index = len(self.subtopics)
		if self.subtopics:
			if index < len(self.subtopics):
				subtopic.order_number = self.subtopics[index].order_number
				for later_subtopic in self.subtopics[index:]:
					later_subtopic.order_number += 1
				sqlite.connection.execute("UPDATE topic SET order_number = order_number + 1 WHERE parent = ? AND order_number >= ?", (self.id, subtopic.order_number))
			else:
				subtopic.order_number = self.subtopics[-1].order_number + 1
		#print self.subtopics, index
		self.subtopics.insert(index, subtopic)
		subtopic.parent = self
		sqlite.save_or_update_item(subtopic)
		#print self.subtopics, index, subtopic.id
		self.add_subtopic_observers(subtopic)
	
	def add_empty_subtopic(self, name, description=""):
		"""Adds an empty passage list with the given name and description.
		
		Returns the newly created passage list.
		"""
		subtopic = PassageList(name, description)
		self.add_subtopic(subtopic)
		return subtopic

	def remove_subtopic(self, topic):
		"""Removes the given subtopic of the current topic.

		After removal the remove_subtopics observers will be called.

		If the subtopic is not present, then a MissingTopicError is raised.
		"""
		try:
			index = self.subtopics.index(topic)
			del self.subtopics[index]
			sqlite.remove_item(topic)
			self.remove_subtopic_observers(topic)
		except ValueError:
			raise MissingTopicError(topic)
	
	def add_passage(self, passage):
		"""Adds the given passage to the end of the list of passages."""
		self.insert_passage(passage, index=None)
	
	def insert_passage(self, passage, index):
		"""Inserts the given passage into the list of passages.
		
		index: The index to insert the passage before.
			If this is None, then the passage will be appended to the list.
		"""
		if index is None:
			index = len(self.passages)
		if self.passages:
			if index < len(self.passages):
				passage.order_number = self.passages[index].order_number
				for later_passage in self.passages[index:]:
					later_passage.order_number += 1
				sqlite.connection.execute("UPDATE passage SET order_number = order_number + 1 WHERE parent = ? AND order_number >= ?", (self.id, passage.order_number))
			else:
				passage.order_number = self.passages[-1].order_number + 1
		self.passages.insert(index, passage)
		passage.parent = self
		sqlite.save_or_update_item(passage)
		self.add_passage_observers(passage)

	def remove_passage(self, passage):
		"""Removes the given passage for the current topic.

		After removal the remove_passage observers will be called.

		If the passage is not present, then a MissingPassageError is raised.
		"""
		try:
			index = self.passages.index(passage)
			del self.passages[index]
			sqlite.remove_item(passage)
			self.remove_passage_observers(passage, index)
		except ValueError:
			raise MissingPassageError(passage)
	
	def contains_verse(self, verse_key, recursive=False):
		"""Returns true if the given verse is contained in the list.

		recursive: If true, search sub lists as well.
		"""
		for passage in self.passages:
			if passage.contains_verse(verse_key):
				return True
		if recursive:
			for topic in self.subtopics:
				if topic.contains_verse(verse_key, recursive=True):
					return True
		return False

	def get_id(self):
		"""Gets a unique identifier for this list.

		This can be used to identify the list and look it up using
		lookup_passage_list, which is used in creating tags for the HTML
		window.
		"""
		return id(self)

	def _find_or_create_topics(self, topics):
		"""Finds or creates all of the topics in the given list of topics."""
		assert topics, "Unexpected empty list."
		if not topics:
			return None

		topic_name = topics.pop(0)
		topic = self._find_or_create_topic(topic_name)

		if topics:
			return topic._find_or_create_topics(topics)
		else:
			return topic

	def _find_or_create_topic(self, topic_name):
		for topic in self.subtopics:
			if topic.name.lower() == topic_name.lower():
				return topic

		return self.add_empty_subtopic(topic_name)

	def clone(self):
		"""Makes a clean copy of this passage list (including its passages
		and subtopics) and returns it.
		"""
		new_list = PassageList(name=self.name, description=self.description)
		sqlite.save_or_update_item(new_list)
		for topic in self.subtopics:
			new_list.add_subtopic(topic.clone())
		for passage in self.passages:
			new_list.add_passage(passage.clone())
		return new_list
	
	def __eq__(self, other):
		try:
			return self.subtopics == other.subtopics \
					and self.passages == other.passages

			# For help in debugging.
			#import sys
			#sys.stderr.write("%s, subtopics equal: %s, passages equal: %s\n" % (self.full_name, self.subtopics == other.subtopics, self.passages == other.passages))
			#sys.stderr.write("Subtopic " + str(self.subtopics) + " " + str(other.subtopics) + "\n")
			#sys.stderr.write("Passage " + str(self.passages) + " " + str(other.passages) + "\n")
		except:
			return False

class PassageList(BasePassageList):
	contains_passages = True

	def __init__(self, name, description=""):
		super(PassageList, self).__init__(description)
		self._name = name

	def set_name(self, name):
		if name != self._name:
			self._name = name
			self.name_changed_observers(name)

	name = property(lambda self: self._name, set_name)

	def set_description(self, description):
		if description != self._description:
			self._description = description
			self.description_changed_observers(description)
	
	description = property(lambda self: self._description, set_description)
	
	def get_topic_trail(self):
		return self.parent.topic_trail + (self.name,)

	topic_trail = property(get_topic_trail,
			doc="The complete list of topics in the hierarchy of this topic.")

	def get_path(self):
		path = self.parent.path
		path.append(self.parent.subtopics.index(self))
		return path

	path = property(get_path,
			doc="The path to get to this topic, as a list of integer indexes.")
	
	def get_full_name(self):
		"""Gets the full name of the passage list.

		This includes the name of this passage list and all parent passage
		lists, formatted as a bread-crumb list.
		"""
		return " > ".join(self.get_topic_trail())
	
	full_name = property(get_full_name)
	
	def __eq__(self, other):
		try:
			return self.name == other.name \
					and super(PassageList, self).__eq__(other)
		except:
			return False

	def __repr__(self):
		return '<PassageList %s>' % repr(self.name)
	
	@staticmethod
	def create_from_verse_list(name, verse_list, description="", comment=""):
		"""Creates a passage list with the given name.

		verse_list: The list of verses to create the passage list from.
		description: The description for the passage list.
		comment: The comment to attach to every passage entry.
		"""
		passage_list = PassageList(name, description)
		for verse in verse_list:
			passage_list.add_passage(PassageEntry(verse, comment))
		return passage_list

def _create_passage_list(name, description, passages, subtopics):
	passage_list = PassageList(name, description)
	for passage in passages:
		passage_list.add_passage(passage)

	for subtopic in subtopics:
		passage_list.add_subtopic(subtopic)
	
	return passage_list

class PassageListManager(BasePassageList):
	"""This class provides the root passage list manager."""
	def __init__(self):
		super(PassageListManager, self).__init__()
		self.description = ""

	def save(self):
		"""Saves this passage list manager to its file."""
		sqlite.save()

	def save_item(self, item):
		"""Saves changes to the given item."""
		if isinstance(item, BasePassageList):
			sqlite.store_topic(item)
		else:
			sqlite.save_or_update_item(item)

	def close(self):
		"""To be called when the application is closed, to close the
		connection.
		"""
		global _global_passage_list_manager
		_global_passage_list_manager = None
		sqlite.close()

	def get_name(self):
		return "Topics"
		#return _("Topics")

	name = property(get_name, lambda self, new_name: None)

	def get_topic_trail(self):
		return ()

	topic_trail = property(get_topic_trail)

	@property
	def full_name(self):
		#return _("None")
		return "None"

	def find_topic_by_path(self, path):
		"""Finds the topic in this manager with the given path.
		
		Returns the topic that was found.
		"""
		try:
			current_topic = self
			for index in path:
				current_topic = current_topic.subtopics[index]
			return current_topic
		except IndexError:
			# If the path no longer exists, then return the manager.
			# This means that the last selected topic will be the top-level
			# manager, equivalent to if there was no last selected topic.
			return self

	def get_path(self):
		return []

	path = property(get_path)

	def find_or_create_topic(self, name):
		"""Finds the topic with the given name.  If it doesn't exist, then
		this will create it.
		The search for the topic name is case insensitive.

		If the name is a full name, then it will be handled properly.

		This is used in the tag passage dialog to create a new topic if
		the user doesn't select an existing topic.

		>>> from passage_list import PassageListManager
		>>> manager = PassageListManager()
		>>> manager.find_or_create_topic("topic1")
		<PassageList 'topic1'>
		>>> manager.find_or_create_topic("topic2")
		<PassageList 'topic2'>
		>>> manager.subtopics
		[<PassageList 'topic1'>, <PassageList 'topic2'>]
		>>> manager.find_or_create_topic("topic1 > topic2")
		<PassageList 'topic2'>
		>>> manager.find_or_create_topic("Topic1")
		<PassageList 'topic1'>
		>>> manager.subtopics[0].subtopics
		[<PassageList 'topic2'>]
		"""
		topics = [topic_name.strip() for topic_name in name.split(">")]
		return self._find_or_create_topics(topics)

def _create_manager(lists, passages):
	manager = PassageListManager()
	for list in lists:
		manager.add_subtopic(list)

	for passage in passages:
		manager.add_passage(passage)

	return manager

import config

DEFAULT_FILENAME = config.data_path + "passages.sqlite"

_global_passage_list_manager = None

def get_primary_passage_list_manager(filename=DEFAULT_FILENAME):
	"""Gets the primary passage list manager for the application."""
	global _global_passage_list_manager
	if _global_passage_list_manager is None:
		_global_passage_list_manager = sqlite.load_manager(filename)
		import guiconfig
		guiconfig.mainfrm.on_close += _global_passage_list_manager.close
	return _global_passage_list_manager

class MissingTopicError(Exception):
	"""This exception is thrown when an operation is performed on a topic
	that is not a subtopic of the current topic.
	"""

class MissingPassageError(Exception):
	"""This exception is thrown when an operation is performed on a passage
	that is not present in the current topic.
	"""

def lookup_passage_list(id):
	"""Looks up the passage list with the given ID.

	This is used by the passage tag to easily identify a given passage list
	(since tags can only receive string parameters).
	"""
	global _passage_list_id_dict
	return _passage_list_id_dict[id]

if __name__ == "__main__":
	import doctest, passage_list as p
	doctest.testmod(p)
