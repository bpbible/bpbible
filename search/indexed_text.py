from backend.bibleinterface import biblemgr
from swlib.pysw import VK, TOP, vk, SW
import re
import sys
from util.debug import dprint, WARNING, ERROR

from query_parser import removeformatting
import process_text

class IndexedText(object):
	"""A bit of text, one reference per line, with an index built against it"""
	gatherstatistics = True
	def __init__(self, version, bookname=None, create_index=True):
		self.index = [] # ref, start, length
		self.text = ""
		self.strongs_info = ""
		self.bookname = bookname or version
		self.version = version
		module = self.load_module(version)
		if create_index:
			self.collect_text(module)
	
	def collect_text(self, module):
		"""Collect the text for a given module, into a reference per line
		format, then build an index against it"""
		# this is a guaranteed non-character...
		# so it shouldn't be used in text
		# http://en.wikibooks.org/wiki/Unicode/Character_reference/F000-FFFF
		MAGIC_TOKEN = u"\uFDD0"

		xml_token = "&#%d;" % ord(MAGIC_TOKEN)

		items = []

		old_key = module.getKey()
		if not ord(old_key.Persist()):
			# if it wasn't a persistent key, the module owns it
			# so take a copy of it, and say we own it
			old_key = old_key.clone()
			old_key.thisown = True

		key = self.get_key(module)
		key.Persist(1)
		module.setPosition(TOP)
		module.setKey(key)
		
		# clear the error
		module.Error()

		# gather the text
		while not ord(module.Error()):
			items.append(module.getRawEntry())
			module.increment(1)
		
		# the key's headings attribute gets set to 1 at the end of the
		# previous loop...
		if isinstance(key, VK): key.Headings(0)
		
		# try and do smart parsing
		content = None
		if ord(module.Markup()) == SW.FMT_OSIS:
			# fix its encoding if necessary
			if ord(module.Encoding()) == SW.ENC_LATIN1:
				xml_items = [
					item.decode("cp1252").encode("utf8") for item in items
				]
			else:
				xml_items = items


			try:
				content = process_text.ParseOSIS().parse(
					xml_token.join(xml_items)
				)

			except Exception, e:
				import traceback
				traceback.print_exc()
		
		if content is None:
			# fallback, don't want to have to do this...
			
			# encode the token as utf-8 so that we end up with a string from
			# here
			content = MAGIC_TOKEN.encode("utf8").join(
				module.StripText(item) for item in items
			)

		content = content.decode("utf-8", "ignore")
		content = removeformatting(content)
		self.text = re.sub("\s*%s\s*" % MAGIC_TOKEN, "\n", content)
		self.text, self.strongs_info = self.extract_strongs(self.text)

		self.create_index_against_text(module, key)

		module.setKey(old_key)

	def extract_strongs(self, text):
		# put offset in an array, so that we can write to it in the callback
		offset = [0]
		matches = []

		def replace(match):
			o = offset[0]
			number, text = match.group(1, 2)
			new_offset = (o + len(number) + 3)
			matches.append("%s\x00%s %s" % (
				number, match.start() - o, match.end() - new_offset
			))
			offset[0] = new_offset
			return text

		text = re.sub(
			# the second group can actually be empty, if it is just the
			# article
			u"%s([^%s]+)%s([^%s]*)%s" % ((
				process_text.ParseOSIS.STRONGS_MARKER.decode("utf8"),
			) * 5),
			replace,
			text
		)

		return text, '\n'.join(matches)

	def create_index_against_text(self, module, key):
		"""Build an index against the text"""
		self.index = [] # reference, start, length
		
		module.setPosition(TOP)
		
		# clear error
		module.Error()

		iterator = re.compile("^.*$", re.M).finditer(self.text)
		for match in iterator:
			error = ord(module.Error())
			assert not error, "%r %s %s" % (error, match.group(), module.getKeyText())

			ind = self.get_index(key)
			start, end = match.span()
			self.index.append((ind, start, end-start))
			module.increment(1)
		
	def find_index(self, mylist):
		"""Turn a sorted list of begin, end pairs into references using 
		the index"""
		if not mylist:
			return []
		
		module = self.load_module(self.version)		
		key = self.get_key(module)

		upto = 0
		begin, end = mylist[upto]
		ret = []
		for idx, (key_value, start, length) in enumerate(self.index):
			# find in index
			# mylist must be sorted
			while start + length > begin:
				# loop here because search phrase may be
				# multiple times in one verse, so we get all
				n = 1

				# This loop tells us if we go over verse boundaries
				while (idx + n < len(self.index) and 
					self.index[idx + n][1] < begin + end):
					n += 1
	
				self.set_key(module, key, key_value)
				ref1 = key.getText()

				if n > 1:
					self.set_key(module, key, self.index[idx+n-1][0])
					ref2 = key.getText()
					ret.append("%s - %s" % (ref1, ref2))

				else:
					ret.append(ref1)
	
				upto += 1
				if upto >= len(mylist):
					return ret

				begin, end = mylist[upto]
		
		dprint(
			WARNING, 
			"Exceeded index length "
			"(this usually means 0 width match at the end of the text)", 
			mylist[upto]
		)
		return ret
		
	def cut_down_index(self, bottom, top):
		### not fully implemented for non-bibles
		vk1 = VK((self.bookname, self.bookname))
		vk = VK((bottom, top))
		vk_dn = vk.LowerBound()
		vk_up = vk.UpperBound()

		# the item we are currently looking for
		start_ref = None
		ret = []
		items = []
		
		self.old_text = self.text
		self.old_index = self.index

		for match in re.finditer("(?m)^.*$", self.text):
			if vk_dn <= vk1 <= vk_up:
				items.append(match.group())
			
			vk1.increment(1)
		
		self.text = '\n'.join(items)
		self.create_index_against_text(vk)

		
	def load_module(self, version):
		return biblemgr.get_module(version)
	
	def get_key(self, module):
		return module.getKey()
	
	def get_index(self, key):
		return key.getText()
	
	def set_key(self, module, key, to):
		key.setText(to)

	# --- Searching functions
	def multi_search(self, wordlist, proximity, is_word_proximity=True,
		average_word=0, minimum_average=5, ignore_minimum=False, 
		excludes=(), strongs=(), excluded_strongs=()):

		# t is shorter to use than self.text, also should be slightly faster
		t = self.text
		
		mylist = []
		
		# keep track of our bounds
		
		total_length = 0
		for regex, length in wordlist:
			total_length += length

		if not average_word and len(wordlist):
			average_word = total_length/len(wordlist)

		if(average_word < minimum_average and not ignore_minimum):
			average_word = minimum_average
		
		
		wordlist = [word for word, length in wordlist]
		
		len_t = len(t)
		len_words = 0#len(words)
		lastbounds = (0, 0)
		
		self.start_strongs_find(strongs, excluded_strongs)

		if wordlist:
			# we have to start with the wordlist if we can, otherwise we may
			# not get references where the word overlaps with the strong's
			# number
			result_iter = wordlist.pop(0).finditer(t)
		else:			
			result_iter = self.strongs[0].pop(0)
			self.strongs_upto[0].pop(0)
			self.current_strongs[0].pop(0)
			
			# Knock sentinel off end
			result_iter = result_iter[:-1]
			

		for result in result_iter:
			if isinstance(result, tuple):
				match_start, match_end = result
			else:
				match_start, match_end = result.span()

			# if the next match of the master word
			# is in the range we have just matched,
			# go onto the next one
			# NOTE: This is probably undesirable behaviour
			# e.g. searching for foo bar in boink foo foo bar boink
			# will yield foo foo bar instead of foo bar
			if(match_start < lastbounds[1]):
				continue
			
			# Establish our boundary on this particularly match.

			# Make sure our boundaries are at word borders.
			# This is important, as otherwise we may match incorrectly

			if is_word_proximity:
				# NOTE: this doesn't respect end of verse (e.g. new line) word
				# boundaries. This is desirable behaviour, but not crucial, as 
				# we will just end up with a larger range
				lower = match_start-proximity*average_word-len_words
				if lower > 0 and t[lower] not in " \n":
					# why not get next space instead of previous?
					# might be quicker?
					lower = t.rfind(" ", 0, lower)

				upper = match_end + proximity * average_word + len_words
				if upper < len_t and t[upper] not in " \n":
					upper = t.find(" ", upper, len_t)
				
				# make sure we stay in bounds
				if lower < 0: lower = 0
				if upper > len_t: upper = len_t
					
			else:
				lower = match_start
				upper = match_end - 1
				for item in range(proximity):
					lower = t.rfind("\n", 0, lower)
					upper = t.find("\n", upper+1)
					# make sure we stay in bounds
					if lower == -1: lower = 0
					if upper == -1: upper = len_t					

			
			bounds = lower, upper
			textrange = t[lower: upper]

			# check for the excluded words in our range
			excluded = False
			for exclude, length in excludes:
				if exclude.search(textrange):
					excluded = True
					break

			if excluded: 
				continue
			
			self.set_strongs_range(lower, upper, excluded=True)
			for strongs_info in self.current_strongs[1]:
				if strongs_info:
					excluded = True
					break

			if excluded: 
				continue
				

			# check for all the words to match
			inrange = True
			
			for comp in wordlist:
				if not comp.search(textrange):
					inrange = False
					break
			
			if not inrange:
				continue
			
			self.set_strongs_range(lower, upper)
			for strongs_info in self.current_strongs[0]:
				if not strongs_info:
					inrange = False
					break

			if not inrange:
				continue
			
			# make range as narrow as possible
			docontinue = False
			start, end = match_start, match_end

			for comp in wordlist:
				backrange = t[bounds[0]: match_start]
				forwardrange = t[match_end: bounds[1]]
				
				# find smallest backwards match				
				last = None
				for j in comp.finditer(backrange):
					last = j
								
				if last:
					backind = last.start() + bounds[0]
				else: 
					backind = -1

				if backind < lastbounds[1]:
					backind = -1
	
				# find smallest forwards match
				forward_match = comp.search(forwardrange)
				if forward_match: 
					forwardind = forward_match.end() + match_end
				else: 
					forwardind = -1
				
				#if we stray into the previous matches bounds, ignore it
				if(forwardind < lastbounds[1]):
					forwardind = -1
	
				# WARNING: duplicated code used below
				# pick which side to take
				# if neither forward nor back are there, skip this match
				if forwardind == -1 and backind == -1:
					docontinue = True
					break
	
				# if we couldn't find it forward, take the back
				if forwardind == -1:
					ind = backind
				
				# if no back, or forward is closer, pick it
				elif backind == -1 or \
						match_start - backind > forwardind - match_end:

					ind = forwardind
				
				# otherwise, pick backwards
				else: 
					ind = backind
				
				# and loosen the range to include this
				if ind < start:
					start = ind

				if ind > end:
					end = ind

			if docontinue:
				continue
	
			for item in self.current_strongs[0]:
				# cast out all ones that hit the previous one
				item = [a for a in item if a[0] > lastbounds[1]]
				
				forwardind = backind = -1
				# now find the one closest to start and end
				for obj in item:
					# We have a slightly different policy here:
					# The main match can overlap with this
					# This isn't true for word searches
					if obj[1] <= match_end:
						backind = obj[0]

					if obj[0] >= match_start and forwardind == -1:
						forwardind = obj[1]
				
				# WARNING: duplicated code taken from above
				# pick which side to take
				# if neither forward nor back are there, skip this match
				if forwardind == -1 and backind == -1:
					docontinue = True
					break
	
				# if we couldn't find it forward, take the back
				if forwardind == -1:
					ind = backind
				
				# if no back, or forward is closer, pick it
				elif backind == -1 or \
						match_start - backind > forwardind - match_end:

					ind = forwardind
				
				# otherwise, pick backwards
				else: 
					ind = backind
				
				# and loosen the range to include this
				if ind < start:
					start = ind

				if ind > end:
					end = ind

			if docontinue:
				continue
			# add this match onto our list of matches
			lastbounds = (start, end)
			mylist.append((start, end - start))

		return mylist
	
	def start_strongs_find(self, words, excluded):
		"""Set the strongs words we are looking for. This finds them and sets
		up to look for them when needed"""
		self.strongs = [[], []]
		self.strongs_upto = [[], []]
		self.current_strongs = [[], []]
		for idx, group in enumerate((words, excluded)):
			for word in group:
				l = []
				word = "%s[^\x00]*\x00(\d+) (\d+)" % word

				regex = re.compile(word, re.MULTILINE|re.IGNORECASE|re.UNICODE)
				for item in regex.finditer(self.strongs_info):
					l.append((int(item.group(1)), int(item.group(2))))
				
				# end sentinel - we use the end sentinel so that we don't have to
				# check for the end of the list
				l.append((sys.maxint, sys.maxint))

				self.strongs_upto[idx].append(0)
				self.strongs[idx].append(l)
				self.current_strongs[idx].append([])

	def set_strongs_range(self, start, end, excluded=False):
		"""Set the current strongs to the ones which fall in this range.
		start >= previous start values"""
		for idx, strongs in enumerate(self.strongs[excluded]):
			# remove old ones
			current = [
				item for item in self.current_strongs[excluded][idx] if item[1] >= start
			]
			
			it = self.strongs_upto[excluded][idx]
			
			# pass over ones before here
			while strongs[it][1] < start:
				it += 1 
			
			# and put new ones in
			while start <= strongs[it][0] and strongs[it][1] <= end:
				current.append(strongs[it])
				it += 1 
			
			self.strongs_upto[excluded][idx] = it
			self.current_strongs[excluded][idx] = current


	def find_strongs(self, word):
		word = "%s[^\x00]*\x00(\d+) (\d+)" % word
		regex = re.compile(word, re.MULTILINE|re.IGNORECASE|re.UNICODE)
		ret = []
		for item in regex.finditer(self.strongs_info):
			ret.append((int(item.group(1)), 0))

		return ret

	def regex_search(self, comp):
		mylist = []
		
		for a in comp.finditer(self.text):
			mylist.append((a.start(), a.end()-a.start()))

		return mylist
	
	def save(self, directory):
		f = open(directory + "/index", "w")
		for (item, start, length) in self.index:
			print >> f, "%s|%s|%s" % (item.encode("utf8"), start, length)

		f2 = open(directory + "/text", "w")
		print >> f2, self.text.encode("utf8")
		
		f3 = open(directory + "/metadata", "w")
		print >> f3, self.bookname
		print >> f3, self.version
	
	@classmethod
	def read(cls, directory):
		f = open(directory + "/index")
		index = []
		for line in f:
			item, start, length = line.split("|")
			start = int(start)
			length = int(length)
			item = item.decode("utf8")
			index.append((item, start, length))

		f2 = open(directory + "/text")
		text = f2.read().decode("utf8")

		f3 = open(directory + "/metadata")
		bookname = f3.next()
		version = f3.next()
		
		obj = cls(version, bookname, create_index=False)
		obj.bookname = bookname
		obj.version = version
		obj.index = index
		obj.text = text
		return obj
	
class VerseIndexedText(IndexedText):
	def get_key(self, module):
		vk = VK((self.bookname, self.bookname))
		vk.Headings(0)
		vk.setPosition(TOP)
		return vk

	def get_index(self, key):
		return (key.Chapter(), key.Verse())
	
	def set_key(self, module, key, to):
		key.Chapter(to[0])
		key.Verse(to[1])

#class GenbookText(IndexedText):
#	def get_key(self, module):
#		tk = TK(module.getKey())
#		tk.root()
#		return tk
#	
#	def get_index(self, key):
#		return str(tk)

if __name__ == '__main__':
	from util import timeit
	import cPickle
	v = VerseIndexedText("ESV", "Genesis")
	def main1(cnt):
		timeit(v.save, "ESV", times=cnt)
		timeit(v.read, "ESV", times=cnt)
	
	def main2(cnt):
		timeit(cPickle.dump, v, open("ESV/pickle", "w"), times=cnt)
		timeit(cPickle.load, open("ESV/pickle"), times=cnt)

	main1(300)
	main2(300)


