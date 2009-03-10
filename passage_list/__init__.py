"""\
This package contains all the classes used for passage lists.
"""
from passage_list import BasePassageList, PassageList, PassageListManager, \
		lookup_passage_list, get_primary_passage_list_manager
from passage_entry import PassageEntry, InvalidPassageError, \
		lookup_passage_entry
from settings import Settings

settings = Settings()
