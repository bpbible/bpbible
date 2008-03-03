#from Sword import *
from swlib.pysw import *
from backend.book import Book

topics_dict = dict()
class Dictionary(Book):
	type = "Lexicons / Dictionaries"
	def __init__(self, parent, version):
		super(Dictionary, self).__init__(parent, version)

		#self.SetModule(version)
		parent.on_before_reload += self.clear_cache


	def GetReference(self, ref, context = None, max_verses = 500, raw=False):
		if not self.mod:
			return None
		template = self.templatelist()
		key = self.mod.getKey();
		key.setText(ref);
		self.mod.setKey(key);
		text = self.mod.RenderText()
		# We have to get KeyText after RenderText, otherwise our
		# KeyText will be wrong
		d = dict(range = self.mod.KeyText(), 
				 version=self.mod.Name(),
				 description=self.mod.Description())
		verses = template.header.safe_substitute(d)
		d1 = d
		if raw:
			d1["text"] = self.mod.getRawEntry()
		else:
			d1["text"] = text

		verses+=template.body.safe_substitute(d1)

		verses += template.footer.safe_substitute(d) #dictionary name
		return verses;
	
	def clear_cache(self, parent=None):
		topics_dict.clear()
			
	def GetTopics(self):#gets topic lists
		topics = []
		if(self.mod):
			name = self.mod.Name();
			if name in topics_dict:
				return topics_dict[name]
			
			pos = SW.SW_POSITION(1)
			
			self.mod.setPosition(pos)

			while(not ord(self.mod.Error())):
				topics.append(self.mod.getKeyText())
				self.mod.increment(1)
		else:
			return []
		topics_dict[name] = topics
		return topics
	
	def snap_text(self, text):
		mod = self.mod
		if mod is None:
			return text
		k = mod.getKey()
		k.setText(str(text))
		mod.setKey(k)
		
		# snap to entry
		mod.getRawEntryBuf()
		return mod.getKeyText()
	
		

