from passage_entry import PassageEntry
from util.observerlist import ObserverList

_passage_list_id_dict = {}

class _BasePassageList(object):
	"""This provides the basic passage list functionality.

	This functionality is used by both passage lists and the passage list
	manager.  It involves the management of passage lists that are contained
	by the list, including an observer list for observers of new subtopics
	being added.
	"""
	contains_passages = True

	def __init__(self, description=""):
		self.description = description
		self.parent = None
		self.name_changed_observers = ObserverList()
		self.subtopics = []
		self.add_subtopic_observers = ObserverList()
		self.remove_subtopic_observers = ObserverList()

		global _passage_list_id_dict
		_passage_list_id_dict[self.get_id()] = self

		self.passages = []
		self.add_passage_observers = ObserverList()
		self.remove_passage_observers = ObserverList()
	
	def add_subtopic(self, subtopic):
		"""Adds the given sub-topic to the end of the list of sub-topics."""
		self.subtopics.append(subtopic)
		subtopic.parent = self
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
			self.remove_subtopic_observers(topic)
		except ValueError:
			raise MissingTopicError(topic)
	
	def add_passage(self, passage):
		"""Adds the given passage to the end of the list of passages."""
		self.passages.append(passage)
		passage.parent = self
		self.add_passage_observers(passage)
	
	def insert_passage(self, passage, index):
		"""Inserts the given passage into the list of passages."""
		self.passages.insert(index, passage)

	def remove_passage(self, passage):
		"""Removes the given passage for the current topic.

		After removal the remove_passage observers will be called.

		If the passage is not present, then a MissingPassageError is raised.
		"""
		try:
			index = self.passages.index(passage)
			del self.passages[index]
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
		for topic in self.subtopics:
			new_list.add_subtopic(topic.clone())
		for passage in self.passages:
			new_list.add_passage(passage.clone())
		return new_list
	
	def __eq__(self, other):
		try:
			return self.subtopics == other.subtopics \
					and self.passages == other.passages
		except:
			return False

class PassageList(_BasePassageList):
	contains_passages = True

	def __init__(self, name, description=""):
		super(PassageList, self).__init__(description)
		self._name = name

	def set_name(self, name):
		self._name = name
		self.name_changed_observers(name)

	name = property(lambda self: self._name, set_name)
	
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

class PassageListManager(_BasePassageList):
	"""This class provides the root passage list manager.

	A passage list manager must be associated with a file name, and the
	save() method will save the file.
	"""
	def __init__(self, filename=None):
		super(PassageListManager, self).__init__()
		self.filename = filename

	def save(self):
		"""Saves this passage list manager to its file.
		
		This relies on the manager having an associated file name.
		"""
		_save_to_xml_file(self, self.filename)

	def get_topic_trail(self):
		return ()

	topic_trail = property(get_topic_trail)

	def get_full_name(self):
		return "None"

	full_name = property(get_full_name)

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

DEFAULT_FILENAME = config.data_path + "passages"

sample_xml = """
<passage_list version="1">
	<topic name="Topic Name">
		<topic name="Subtopic">
			<description>Some description.</description>
		</topic>
		<passage reference="Matthew 2:2">
			<comment>A comment.</comment>
		</passage>
	</topic>
</passage_list>
"""

import xml.dom.minidom

def load_from_xml_file(filename):
	"""Loads a PassageFileManager from the given file name, and returns it.
	
	If it is unable to load from the given file, then it raises an
	InvalidPassageListError.
	"""
	try:
		dom = xml.dom.minidom.parse(filename)
	except Exception, e:
		raise InvalidPassageListError(e)
	manager = _handle_passage_list(dom)
	manager.filename = filename
	return manager

load_from_file = load_from_xml_file

def _handle_passage_list(dom):
	version = dom.documentElement.getAttribute("version")
	assert version == "1"
	return _create_manager(_handle_subtopics(dom.documentElement),
			_handle_passages(dom.documentElement))

def _handle_subtopics(topic):
	return [_handle_topic(subtopic)
			for subtopic in topic.childNodes
			if subtopic.tagName == "topic"]

def _handle_topic(topic):
	name = topic.getAttribute("name")
	description = _get_element_text(topic, "description")
	subtopics = _handle_subtopics(topic)
	passages = _handle_passages(topic)
	return _create_passage_list(name, description, passages, subtopics)

def _handle_passages(topic):
	return [_handle_passage(passage)
			for passage in topic.childNodes
			if passage.tagName == "passage"]

def _handle_passage(passage):
	reference = passage.getAttribute("reference")
	comment = _get_element_text(passage, "comment")
	return PassageEntry(reference, comment)

def _get_element_text(parent, tag_name):
	"""Gets all the text in the first element of the parent with the given
	tag name.
	Returns "" if there is no element with the given tag name.
	"""
	tag_nodes = parent.getElementsByTagName(tag_name)
	if not tag_nodes:
		return ""

	return _get_text(tag_nodes[0].childNodes)

def _get_text(nodes):
	return "".join(node.data for node in nodes
			if node.nodeType == node.TEXT_NODE)

def _save_to_xml_file(list, filename):
	dom = _get_passage_list_manager_dom(list)
	file = open(filename, "w")
	dom.writexml(file)
	file.close()

def _get_passage_list_manager_dom(list):
	doc = _create_xml_doc()
	top_element = doc.documentElement
	top_element.setAttribute("version", "1")
	_xml_for_subtopics(list, doc, top_element)
	_xml_for_passages(list, doc, top_element)
	return doc

def _create_xml_doc():
	impl = xml.dom.minidom.getDOMImplementation()
	return impl.createDocument(None, "passage_list", None)

def _xml_for_subtopics(topic, doc, parent):
	for subtopic in topic.subtopics:
		parent.appendChild(_xml_for_topic(subtopic, doc))

def _xml_for_topic(topic, doc):
	element = doc.createElement("topic")
	element.setAttribute("name", topic.name)
	element.setAttribute("display_tag", "true")
	element.appendChild(_create_text_element(doc, "description", topic.description))
	_xml_for_subtopics(topic, doc, element)
	_xml_for_passages(topic, doc, element)
	return element

def _xml_for_passages(topic, doc, parent):
	for passage in topic.passages:
		parent.appendChild(_xml_for_passage(passage, doc))

def _xml_for_passage(passage_entry, doc):
	element = doc.createElement("passage")
	element.setAttribute("reference", str(passage_entry))
	element.appendChild(_create_text_element(doc, "comment", passage_entry.comment))
	return element

def _create_text_element(doc, tag_name, text):
	"""Creates an element with the given tag name containing the given text,
	and returns it.
	"""
	element = doc.createElement(tag_name)
	element.appendChild(doc.createTextNode(text))
	return element

def load_default_passage_lists(filename=DEFAULT_FILENAME):
	"""Attempts to load the passage lists from the given file name.

	If it is unable to load them, then it returns an empty passage list
	manager.
	"""
	try:
		return load_from_file(filename)
	except InvalidPassageListError:
		return PassageListManager(filename)

class InvalidPassageListError(Exception):
	"""This exception is thrown when the passage list cannot be loaded."""

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
