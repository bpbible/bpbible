"""\
This package contains all the classes used for passage lists.
"""
from passage_list import PassageList, PassageListManager, load_from_file, \
		load_default_passage_lists, InvalidPassageListError, lookup_passage_list
from passage_entry import PassageEntry, InvalidPassageError, \
		MultiplePassagesError, lookup_passage_entry
from settings import Settings

_global_passage_list_manager = None

def get_primary_passage_list_manager():
	"""Gets the primary passage list manager for the application."""
	global _global_passage_list_manager
	if _global_passage_list_manager is None:
		_global_passage_list_manager = load_default_passage_lists()
	return _global_passage_list_manager

settings = Settings(get_primary_passage_list_manager())
