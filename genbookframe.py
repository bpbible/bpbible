import wx
from swlib.pysw import TK
from bookframe import BookFrame
import genbooktree
from backend.bibleinterface import biblemgr


import config

class GenBookFrame(BookFrame):
	title="Other Books"
	use_quickselector = False
	def __init__(self, parent, book):
		self.genbookpanel = wx.Panel(parent)
		super(GenBookFrame, self).__init__(self.genbookpanel)
		self.SetBook(book)

		self.genbooktree = genbooktree.GenBookTree(self.genbookpanel, 
				book, self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.genbooktree, flag = wx.GROW)
		sizer.Add(self, 3, flag = wx.GROW)
		self.genbookpanel.SetSizer(sizer)
		self.genbookpanel.Fit()
		self.genbooktree.Bind(wx.EVT_COMBOBOX, self.on_genbook_change)
		biblemgr.genbook.observers += self.genbook_version_changed
		
		
	
	def SetReference(self, ref, context = None):
		self.reference = ref
		if self.book.mod:
			bref = TK(ref)

			breadcrumb = bref.breadcrumb(
				include_home=self.book.version,
				book=self.book
			)
			data = "<b>%s</b><br />" % breadcrumb.replace(">", "&gt;")
		
			text = self.book.GetReferenceFromKey(ref, context = context)
			data += text
			data = data.replace("<!P>","</p><p>")

		else:
			data = config.MODULE_MISSING_STRING
				
		self.SetPage(data)
		self.update_title()
		

	def chapter_move(self, amount):
		mod = self.book.mod
		if not mod: return
		key = TK(self.reference)
		key.Persist(1)
		#key.setText(self.reference)
		mod.setKey(key)
		#while(not ord(self.mod.Error())):
		#		topics.append(self.mod.getKeyText());
		mod.increment(amount);
		#ref = mod.getKeyText()
		text = key.getText()
		rootkey = TK(key)
		rootkey.root()

		# don't set it to the root
		if key.getText() != rootkey.getText() or ord(mod.Error()):
			self.SetReference(key)

	def get_window(self):
		return self.genbookpanel


	def on_genbook_change(self, event):
		self.SetReference(
			self.genbooktree.tree.GetPyData(self.genbooktree.popup.value)[0]
		)

	def genbook_version_changed(self, newversion):
		if newversion:
			key = TK(newversion.getKey())
			key.root()
			self.SetReference(key)
		else:
			self.SetReference(None)

		self.genbooktree.SetBook(biblemgr.genbook)
	

