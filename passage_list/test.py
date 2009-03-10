"""\
This module is a convenience module.
It collects all the classes from all the different test modules into one
module, so that all unit tests can be run at once.
"""
from test_passage_entry import *
from test_passage_list import *
from test_passage_list_manager import *

import unittest
unittest.main()
