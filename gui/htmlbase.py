from util import string_util
import re
from util.configmgr import config_manager
from util.debug import dprint, ERROR, MESSAGE, WARNING
from gui import fonts
from swlib import pysw

def convert_language(text, language_code):
	# remove all &#1243;'s which will stop our language recognition
	text = string_util.amps_to_unicode(text, replace_specials=False)

	# put greek and hebrew in their fonts
	for lang_code, letters, dont_use_for in (
		# ancient greek (to 1453)
		("grc", string_util.greek, ("el", "grc")),

		# Hebrew (generally)
		("he", string_util.hebrew, ("he",)),
	):
		# if we are, say, a greek book, don't take greek out specially
		if language_code in dont_use_for:
			continue

		text = string_util.insert_language_font(text, letters, lang_code)

	return text
