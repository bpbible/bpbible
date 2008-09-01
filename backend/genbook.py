#from swlib.Sword import *
from swlib.pysw import SW, TK
from backend.book import Book
from util.unicode import to_str

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

	def GetReference(self, ref, context = None, max_verses = 500,
			stripped=False):
		if not self.mod:
			return None
		template = self.templatelist[-1]
		render_text = self.get_rendertext()
		
		#key = self.mod.getKey()
		#	key.setText(ref)
		
		if isinstance(ref, basestring):
			key = TK(self.mod.getKey(), self.mod)
			key.setText(to_str(ref, self.mod))
			ref = key
			
		# Without persist, most of the ones in heretics will not work!!!
		ref.Persist(1)
		self.mod.setKey(ref)
		if stripped:
			text = self.mod.StripText().decode("utf-8", "replace")
		else:
			text = render_text()

		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		d = dict(range = self.mod.KeyText(), version = self.mod.Name())
		verses = template.header.substitute(d)
		d1 = d
		d1["text"] = text
		verses += template.body.substitute(d1)

		verses += template.footer.substitute(d)
		return verses
			
			
	def GetKey(self):
		if not self.mod:
			return None
		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk, self.mod)
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
		assert key.module == self.mod
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
