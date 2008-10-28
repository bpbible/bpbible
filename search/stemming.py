from util.debug import dprint, MESSAGE, WARNING
import re

class DummyStemmer(object):
	"""A dummy stemmer which doesn't do anything"""
	def stemWords(self, words):
		"""Stem the words - this just returns them as is"""
		return words
	
	def stemWord(self, word):
		return self.stemWords([word])[0]

	def do_stemming(self):
		return type(self) != DummyStemmer

	def compose_regex(self, stemming_data, word):
		if self.do_stemming():
			words_to_search_for = stemming_data.get(self.stemWord(word.lower()),
												None)

			if words_to_search_for is None:
				dprint(WARNING, "Stemmed word not found", word, word.lower())
		else:
			# don't try using the stemming data, as it might lead to
			# inconsistencies
			words_to_search_for = [word]

		# if there are too many options, factorizing these will be a worthwile
		# option. With around 10, it seems ~10% slower than a simple
		# factorization.
		return "(?:" + "|".join(words_to_search_for) + ")"

class SnowballStemmer(DummyStemmer):
	def __init__(self, language, cache_size=0):
		self.stemWords = Stemmer.Stemmer(language, cache_size).stemWords
		
stemmer_imported = False
Stemmer = None

snowball_language_mappings = dict(
	# Problems observed with english stemmer:
	# executioner -> execution,
	# execution -> execut
	# wretched -> wretch
	# wretchedness -> wretched
	en="english",
	de="german",
	es="spanish",
	da="danish",
	nl="dutch",
	fi="finnish",
	it="italian",
	no="norwegian",
	pt="portuguese",
	ru="russian",
	sv="swedish",
	fr="french",
)

def get_stemmer(module):
	global Stemmer, stemmer_imported
	if not stemmer_imported:
		try:
			import Stemmer
		except ImportError:
			dprint(WARNING, "Snowball not installed")
			Stemmer = None

		stemmer_imported = True
	
	language = module.getConfigEntry("Lang") or "en"
	if not Stemmer:
		return DummyStemmer()
	
	if language not in snowball_language_mappings:
		print "No stemmer for language", language
		return DummyStemmer()		

	else:
		# don't use its cache
		return SnowballStemmer(snowball_language_mappings[language], 0)

	
