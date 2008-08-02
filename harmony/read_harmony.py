"""
read_harmony.py
Reads a harmony from a data file.
"""

import re
from swlib.pysw import VerseList#, VK
from util import noop

gospels = ["Matthew", "Mark", "Luke", "John"]

class Harmony(object):
	def __init__(self, name, top):
		self.name = name
		self.top = top
		self.displaygranularity = -1
		self.next_id = -1
		self.sections = {}
		self.books = gospels
		self.loaded = False

	def set_ids(self):
		def set_id(item):
			self.next_id += 1
			self.sections[self.next_id] = item
			item.id = self.next_id
			for child in item.children:
				set_id(child)

		set_id(self.top)

	#def CheckGospel(self, gospel=""):
	#	err = []
	#	if gospel:
	#		gospels2=[gospel]
	#	else:
	#		gospels2=gospels

	#	for a in gospels2:
	#		l=[]
	#		vk = VK((a,a))
	#		l = len(vk)
	#		for a, key in enumerate(vk):
	#			print (a*100)/l
	#			if(not self.top.find_reference(str(key))):
	#				print "WARNING: VERSE OMITTED: " + str(key)
	#				err.append(str(key))
	#	return err

	def load(self):
		top = self.top
		
		# Find the harmony item
		found = None
		for harmony in top.children:
			if harmony.type == "Harmony":
				found = harmony
				break

		if found:
			#reassign ownership
			top.children = found.children
			for child in top.children:
				child.parent = top
	
		#status("\tProccessing references")
		top.process_references(self.books)
		
		def visibility(item):
			if(not item.references or not item.references[0] or
				self.ranks[item.type] < self.ranks[self.displaygranularity]):
				item.visible = False
			else:
				item.visible = True
	
		top.walk_tree(visibility)
	
		top.description = self.name
		top.fulldescription = self.description
		top.name = top.description
	
		#give each container a unique id
		self.set_ids()
		#status("Done")
		self.loaded = True
		
	
		return self


class Container(object):
	def __init__(self, harmony, description="", number="", type=""):
		#description
		self.description = description
		self.harmony = harmony

		#group matched by re
		self.number = number
		self.type = type
		#full text as matched
		self.fulldescription = ""
		self.name = description

		#references
		self.references = []
		
		#relatives
		self.parent = None
		self.next = None
		self.previous = None
		self.children = []

		self.display = False
		self.id = -1
		self.processed = False

	def process_references(self, gospels):
		self.fulldescription += self.description
		self.name = self.fulldescription

		if not self.references:
			self.references = [[]]
		else:
			#merge all lines after first into first
			for refs in self.references[1:]:
				for idx, ref in enumerate(refs):
					self.references[0][idx] += ref

			self.references = self.references[0]
			#split each reflist at ;
			self.references = [ref.split(";") for ref in self.references]

			if not self.references:
				longest = 0
			else:
				longest = max(len(ref) for ref in self.references)

			references = [[] for _ in range(longest)]

			for book_idx, refs in enumerate(self.references):
				for ref_idx, ref in enumerate(refs):
					if ref:
						references[ref_idx].append(
							VerseList(ref, gospels[book_idx])
						)

			self.references = references

		for idx, child in enumerate(self.children):
			child.process_references(gospels)
			
			# set forward and back links on child
			if idx:
				child.previous = self.children[idx - 1]

			if idx != len(self.children) - 1:
				child.next = self.children[idx + 1]

	
	def find_reference(self, reference):
		found = False

		for refs in self.references:
			for ref in refs:
				if ref and ref.VerseInRange(reference):
					found = True
					break
			else:
				# keep on looking
				continue

			break
		
		# if it is in our children, return them
		# they should override their parent
		for child in self.children:
			ansa = child.find_reference(reference)
			if ansa:
				return ansa

		if found:
			return self

		return None

	def walk_tree(self, func):
		func(self)
		for child in self.children:
			child.walk_tree(func)
	
	
#def WriteData(self, details, titles):
#	if(self.type=="Pericope"):
#		if(self.parent.type=="Subsubpart"):
#			titles.writerow(("%s - %s Nisan AD 30"% (self.description,\
#			self.parent.description),))
#		elif(self.parent.type=="Part"):
#			titles.writerow(("%s - %s"%(self.description, \
#			self.parent.description),))
#		elif(self.parent.parent.type=="Part"):
#			titles.writerow(("%s - %s"%(self.description, \
#			self.parent.parent.description),))
#
#		for a in self.references:
#			for id, b in enumerate(a):
#				if(b):
#					details.writerow((str(self.number), str(id+1), b[0]))
#	for a in self.children:
#		WriteData(a, details, titles)
#
#
#def DumpCSV(top):
#	f=open("title.csv","w")
#	f2=open("pericopes.csv","w")
#	import csv
#	titles=csv.writer(f)
#	titles.writerow(("Title",))
#	details=csv.writer(f2)
#	details.writerow(("Section ID", "Part", "Reference"))
#	WriteData(top, details, titles)
		

def process_harmony(filename, status=noop):
	status("Processing harmony from "+ filename)

	# basic setup
	top = Container(None, "Top", "", "Top")
	current = top
	harmony = Harmony("No Name Harmony", top)
	top.harmony = harmony

	# Original processing pieces
	bits = [
		(r"", "Top"),
		(r"Harmony", "Harmony"),
		(r"Settings", "Settings"),
		(r"/([a-zA-Z]*): ", "Setting"),
		#(r"PART ([VIX]+): ", "Part"), #VII:  
		#(r"([A-Z])\. ","Subpart"), #A.
		#(r"([a-z])\. ","Subsubpart"),
		#(r"([0-9]+): ","Pericope"), #34: 
		#(r"\(([a-z]+)\) ","Subpericope"), #(b) 
		#(r"\(([0-9])\) ","Subsubpericope")] #(1) 
		]

	ranks = {-1:-1}

	for idx, (regex, description) in enumerate(bits):
		ranks[description] = idx
	
	def compile_regex(regex):
		if regex:
			return re.compile(regex)

	bits = [(compile_regex(regex), name) for regex, name in bits]

	f = open(filename)

	for line in f:
		line = [item.strip() for item in line.split("|")]
		for regex, description in bits:
			if not regex:
				continue

			match = regex.match(line[0])
			if match:
				try:
					number = match.group(1)
				except IndexError:
					number = None
				
				# go up until we find an appropriate parent (i.e. one with a
				# higher rank than ourselves)
				while ranks[current.type] >= ranks[description]:
					current = current.parent

				new = Container(harmony, description=line[0][match.end():], 
					number=number, type=description)

				new.fulldescription = match.group(0)
				new.parent = current

				current.children.append(new)
				current = new
				break
		else:
			# If we haven't matched anything, this means we are continuing the
			# previous line

			# If we have a "-", chop it off, and don't 
			# put a space before it (this presumes that the dash should 
			# not be there)
			if current.description[-1] == "-":
				current.description = current.description[:-1] + line[0]
			
			# otherwise, just add the last line with a space in
			elif line[0]:
				current.description += " "+line[0]

		current.references.append(line[1:])

		#if we are a pattern, add ourselves to the list
		if(current.type == "Setting" and current.number == "pattern" and
			not current.processed):
			for refs in current.references[1:]:
				for idx, ref in enumerate(refs):
					current.references[0][idx] += ref

			current.references = current.references[0]

			ranks[current.description] = len(ranks)

			bits.append((
				re.compile(current.references[0]), 
				current.description
			))

			current.processed = True

	for child in top.children:
		# not a settings clause
		if child.type != "Settings":
			continue

		for item in child.children:
			if item.number == "name":
				harmony.name = item.description

			elif item.number == "description":
				harmony.description = item.description
				harmony.fulldescription = item.description

			elif item.number == "DisplayGranularity":
				harmony.displaygranularity = item.description
				assert item.description in ranks, (
					"DisplayGranularity %s not found in ranks" % 
					item.description
				)

			elif item.number == "books":
				harmony.books = [item.description] + item.references[0]

	harmony.ranks = ranks
	return harmony

