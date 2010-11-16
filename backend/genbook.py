import os
import re
import cPickle as pickle
from swlib.pysw import SW, TK, VerseList
from backend.book import Book
from util import classproperty
from util.unicode import to_str, to_unicode
import display_options

class TreeNode(object):
	def __init__(self, parent, data): 
		self.children = []
		self.parent = parent
		self.data = data
	
	def AddChild(self, data):
		self.children.append(TreeNode(self, data))
		return self.children[-1]
	
	def __iter__(self):
		return iter(self.children)


class GenBook(Book):
	type = 'Generic Books'	
	noun = "book"
	is_genbook = True
	categories_to_exclude = ["Harmonies"]

	def GetReference(self, ref, context = None, max_verses = 500,
			stripped=False, end_ref=None):
		"""Get a reference from a genbook.

		ref should be either a TK or a string. If it is a TK, it is guaranteed
		not to change its position."""
		if not self.mod:
			return None
		
		template = self.templatelist[-1]
		render_text, render_start, render_end = self.get_rendertext()
		#TODO: use render_start and render_end?
		
		module = self.mod
		
		if isinstance(ref, TK) and end_ref:
			# we will move, so take a copy to move
			ref = TK(ref)
		
		if isinstance(ref, basestring):
			key = TK(module.getKey(), module)
			key.setText(to_str(ref, module))
			ref = key
		
		if isinstance(end_ref, basestring):
			key = TK(module.getKey(), module)
			key.setText(to_str(end_ref, module))
			end_ref = key

		old_key = module.getKey()
		if not ord(old_key.Persist()):
			# if it wasn't a persistent key, the module owns it
			# so take a copy of it, and say we own it
			old_key = old_key.clone()
			old_key.thisown = True
		
		ref.Persist(1)
		module.setKey(ref)
		
		# snap to it
		entry = module.getRawEntry()
		
		# We have to get KeyText after getRawEntry, otherwise our
		# KeyText will be wrong
		d = dict(range = module.KeyText(), version = module.Name())
		verses = template.header.substitute(d)
		
		d1 = d.copy()
		
		raw = display_options.options["raw"]
	
		while True:
			if stripped:
				text = module.StripText(entry).decode("utf-8", "replace")
			else:
				# we can't specify entry here for the same reasons as in
				# book.py
				text = render_text(#entry
				).decode("utf-8", "replace")

			if raw:
				text = self.process_raw(entry, text, ref, module)

			d1["reference"] = to_unicode(module.getKeyText(), module)
			d1["reference_encoded"] = \
				SW.URL.encode(module.getKeyText()).c_str()
			
			d1["text"] = text
			d1["breadcrumbed_reference"] = ref.breadcrumb(delimiter=" > ")		
			d1["level"] = ref.getLevel()
			
			verses += template.body.substitute(d1)
			if not end_ref or end_ref == ref:
				break
			
			ref.increment(1)
			entry = module.getRawEntry()

		verses += template.footer.substitute(d)
		module.setKey(old_key)
		
		return verses
			
			
	def GetKey(self, key_text=None):
		if not self.mod:
			return None
		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk, self.mod)
		if key_text is not None:
			tk.setText(to_str(key_text, self.mod))
		return tk
	
	def GetTopicsTree(self):#gets topic lists
		if not self.mod:
			return None
		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk, self.mod)
		root = TreeNode(None, None)

		def AddTopic(parent, tk):
			me = parent.AddChild(tk.getText())
			for a in tk:
				AddTopic(me, a)

		AddTopic(root, tk)
		return root.children[0]
	
	def GetChildren(self, tk):
		return [a for a in tk]
	
	def display_level(self):
		assert self.mod, "No module in get_config_entry"

		try:
			return int(self.mod.getConfigEntry("DisplayLevel"))
		except (TypeError, ValueError), e:
			# invalid number or not specified
			return 1
	
	def get_display_level_root(self, key):
		"""
		Return the root of the view, and whether to 
		display sub-levels for this node
		"""
		assert key.module == self.mod, \
			"Mismatched module and key: %s, %s" % (
				key.module.Name(),
				self.mod.Name()
			)

		display_level = self.display_level()
		if display_level != 1:
			# display levels:
			# if we are a leaf, just climb up the given number of levels
			# if we are inbetween the above and below cases here, then go down
			# first as far as possible, then up
			# if our display-level'th first child is a leaf, then display
			# all below here.
			# if we are in between those two
			count = 0
			
			ref = TK(key)
			while ref.firstChild() and count < display_level:
				count += 1
		
			if count < display_level:
				# it was a close enough to being a leaf, go up now
				parents_count = 1
				root = TK(key)
				root.root()
				last_ref = TK(ref)
				ref.parent()
				while ref != root and parents_count < display_level:
					last_ref = TK(ref)
					ref.parent()
					parents_count += 1

				# show that reference and all its children
				return last_ref, True

		# don't show any children for this
		return key, False

class Harmony(GenBook):
	category = "Harmonies"
	categories_to_exclude = ()

	def __init__(self, parent, version=""):
		super(Harmony, self).__init__(parent, version)
		self._harmony_references = {}

	@classproperty
	def noun(cls):
		return _("harmony")

	def find_reference(self, reference):
		for tree_key_references in self.harmony_references:
			for harmony_reference in tree_key_references[1]:
				if harmony_reference.VerseInRange(reference):
					return tree_key_references[0]

		return None

	@property
	def harmony_references(self):
		if self.mod is None:
			return []

		module_name = self.mod.Name()
		if module_name not in self._harmony_references:
			self._harmony_references[module_name] = self._load_harmony_references(module_name)

		return self._harmony_references[module_name]

	def _load_harmony_references(self, module_name):
		pickle_filename = "resources/%s.refidx" % module_name
		if os.path.exists(pickle_filename):
			pickle_file = open(pickle_filename, "rb")
			return pickle.load(pickle_file)

		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk, self.mod)
		references = []

		def add_references(tk, references):
			self.mod.setKey(tk)
			entry = self.mod.getRawEntry()
			entry_references = '|'.join(re.findall('<harmonytable refs="([^"]*)"></harmonytable>', entry))
			if entry_references:
				references.append((
					tk.getText(),
					[VerseList(reference, userInput=False) for reference in entry_references.split('|')]
				))

			for child_tk in tk:
				add_references(child_tk, references)

		add_references(tk, references)

		pickle_file = open(pickle_filename, "wb")
		pickle.dump(references, pickle_file)

		return references
