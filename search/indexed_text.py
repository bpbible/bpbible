from backend.bibleinterface import biblemgr
from swlib.pysw import VK, TOP, vk, SW
import re
from util.debug import dprint, WARNING, ERROR

from query_parser import removeformatting
import process_text




class IndexedText(object):
	"""A bit of text, one reference per line, with an index built against it"""
	gatherstatistics = True
	def __init__(self, version, bookname=None):
		self.index = [("NULL", 0, 0)] # ref, start, length
		self.text = ""
		self.bookname = bookname or version
		self.version = version
		module = self.load_module(version)
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

		self.create_index_against_text(module, key)

		module.setKey(old_key)

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
		
		dprint(ERROR, "Exceeded index length", mylist[upto])
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
	def multi_search(self, wordlist, proximity, case_sensitive=False, \
	average_word=0, minimum_average=5, ignore_minimum=False, excludes=(), 
	try_all=False):

		# t is shorter to use than self.text
		t = self.text
		
		mylist = []
		
		#empty query, empty results...
		
		#compile regex - it is escaped and may be case insensitive
		#esc = re.escape(wordlist[0])
		# keep track of our bounds
		
		total_length = 0
		for regex, length in wordlist:
			total_length += length

		if(not average_word):
			average_word = total_length/len(wordlist)

		if(average_word < minimum_average and not ignore_minimum):
			average_word = minimum_average
		
		
		wordlist = [word for word, length in wordlist]
		
		relist = []
		if(not try_all):
			# find the first word in the text, and then search based on it
			# TODO: do all, and then match based on that?
			# seems to be slower though
			for a in wordlist[0].finditer(t):
				relist+=[a]
			del wordlist[0]
		else:
			relist2 = {}
			for r in wordlist:
				relist2[r] = list(r.finditer(t))
			min = (0, None)
			for comp, results in relist2.items():
				if(min[0]<len(results)):
					min = (comp, len(results))
			relist = relist2[min[0]]
			del relist2[min[0]]
			#relist = relist2.keys()
			#print relist

		len_t = len(t)
		len_words = 0#len(words)
		lastbounds = (0,0)
		
		for id, match in enumerate(relist):
			# if the next match of the master word
			# is in the range we have just matched,
			# go onto the next one
			# NOTE: This is probably undesirable behaviour
			# e.g. searching for foo bar in boink foo foo bar boink
			# will yield foo foo bar instead of foo bar
			if(match.start() < lastbounds[1]):
				continue
			
			# Make sure our boundaries are at word borders.
			# This is important, as otherwise we may match incorrectly
			lower = match.start()-proximity*average_word-len_words
			if(lower>0 and not t[lower]==" "):
				# why not get next space instead of previous?
				# might be quicker?
				lower = t.rfind(" ", 0, lower) 
			upper = match.end()+proximity*average_word+len_words
			if(upper<len_t and not t[upper]==" "):
				upper = t.find(" ", upper, len_t)

			if(lower < 0):lower=0
			if(upper>len_t): upper=len_t
			bounds = lower, upper
			
			textrange = t[bounds[0]: bounds[1]]
			#t[bounds[0]: bounds[1]]

			docontinue=False
			for exclude, length in excludes:
				if(exclude.search(textrange)):
					docontinue=True
					break

			if docontinue: continue

			inrange = True
			for comp in wordlist:
				if(not comp.search(textrange)):
					inrange = False
					break

			if not inrange:
				continue
			
			start = match.start()
			end = match.end()
			
			# make range as narrow as possible
			docontinue = False
			for comp in wordlist:
				#try back first
				backrange = self.text[bounds[0]: match.start()]
				forwardrange = self.text[match.end(): bounds[1]]
				#backind2 = t.rfind(word, bounds[0], match.start())
				last = None
				for j in comp.finditer(backrange):
					last = j
								
				if last: backind = last.start() + bounds[0]
				else: backind = -1
				#print backind, backind2
				#else:
				#	backind = text.rfind(word, bounds
				if backind < lastbounds[1]:
					backind = -1
	
				#if bounds[1]:
				#	forwardind2 = t.find(word, match.end(), bounds[1])
				#else:
				#	forwardind2 = t.find(word, match.end())
				forwardind = comp.search(forwardrange)
				if forwardind: forwardind = forwardind.end() + match.end()
				else: forwardind = -1
				#if(forwardind2 != -1): forwardind += len(word)
				#print forwardind, forwardind2
				
				#if we stray into the previous matches bounds, ignore it
				if(forwardind < lastbounds[1]):
					forwardind = -1
	
				if(forwardind == -1 and backind == -1):
					docontinue = True
					break
	
				if(forwardind == -1):
					ind = backind

				elif(backind == -1 or match.start() - backind > forwardind -
				match.end()):
					ind = forwardind
				else: ind = backind
				if(ind < start):
					start = ind
				if ind > end:
					end = ind
			if docontinue:
				continue
	
			lastbounds=(start, end)
			mylist.append((start, end - start))

		return mylist
	
	def regex_search(self, comp, case_sensitive=False):
		mylist = []
		
		for a in comp.finditer(self.text):
			mylist.append((a.start(), a.end()-a.start()))

		return mylist
	
	RegexSearch = regex_search
	MultiSearch = multi_search
	FindIndex = find_index
	
class VerseIndexedText(IndexedText):
	def __init__(self, version, testament, booknumber):
		self.testament = testament
		self.book = booknumber
		super(VerseIndexedText, self).__init__(
			version, vk.bookName(self.testament, self.book)
		)

	def get_key(self, module):
		vk = VK((self.bookname, self.bookname))
		vk.Headings(0)
		vk.setPosition(TOP)
		return vk

	def get_index(self, key):
		return key.Chapter(), key.Verse()
	
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

