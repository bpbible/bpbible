#from swlib.Sword import *
from swlib.pysw import SW, TK
from backend.book import Book

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
	def GetReference(self, ref, style = -1, context = None, max_verses = 500):
		if not self.mod:
			return None
		
		template = self.templatelist()
		key = self.mod.getKey()
		key.setText(ref)
		self.mod.setKey(key)
		text = self.mod.RenderText()
		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		d = dict(range = self.mod.KeyText(), version = self.mod.Name())
		verses = template.header.substitute(d)
		d1 = d
		d1["text"] = text
		verses += template.body.substitute(d1)

#		verses += "<b>" + self.mod.KeyText() + "</b><br>"; #output heading
#		verses += self.mod.RenderText(); #output text
#		verses += "<br>(";
#		verses += self.mod.Name();
		verses += template.footer.substitute(d) #dictionary name
		return verses

	def GetReferenceFromKey(self, ref, context = None, max_verses = 500):
		if not self.mod:
			return None
		template = self.templatelist()
		#key = self.mod.getKey()
		#	key.setText(ref)
		
		# Without persist, most of the ones in heretics will not work!!!
		ref.Persist(1)
		self.mod.setKey(ref)
		text = self.mod.RenderText()
		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		d = dict(range = self.mod.KeyText(), version = self.mod.Name())
		verses = template.header.substitute(d)
		d1 = d
		d1["text"] = text
		verses += template.body.substitute(d1)

#			verses += "<b>" + self.mod.KeyText() + "</b><br>"; #output heading
#			verses += self.mod.RenderText(); #output text
#			verses += "<br>(";
#			verses += self.mod.Name();
		verses += template.footer.substitute(d) #dictionary name
		return verses
			
			
	def GetKey(self):
		if not self.mod:
			return None
		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk)
		return tk
	
	def GetTopicsTree(self):#gets topic lists
		if not self.mod:
			return None
		mod_tk = SW.TreeKey.castTo(self.mod.getKey())
		mod_tk.root()
		tk = TK(mod_tk)
		root = TreeNode(None, None)

		def AddTopic(parent, tk):
			me = parent.AddChild(tk.getText())
			for a in tk:
				AddTopic(me, a)

		AddTopic(root, tk)
		return root.children[0]
	
	def GetChildren(self, tk):
		return [a for a in tk]
