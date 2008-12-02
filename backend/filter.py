import sys
from swlib.pysw import SW
from util.debug import dprint, ERROR

from backend import thmlparser, osisparser
from backend import filterutils


# keep a list of all our items so they don't get GC'ed
items = []

class MarkupInserter(SW.MarkupCallback):
	def __init__(self, biblemgr):
		super(MarkupInserter, self).__init__()
		self.thisown = False
		self.biblemgr = biblemgr

		filterutils.register_biblemgr(biblemgr)
		items.append(self)
	
	def run(self, module):
		try:
			markup = self.get_filter(module)
			if markup is not None:
				module.AddRenderFilter(markup)
				return True
			return False

		except Exception, e:
			import traceback
			dprint(ERROR, "EXCEPTION: ", e)
			try:
				traceback.print_exc(file=sys.stdout)
			except Exception, e2:
				dprint(ERROR, "Couldn't print exception - exception raised", e2)
	
	def get_filter(self, module):
		markup = ord(module.Markup())
		markups = {SW.FMT_OSIS:osis, SW.FMT_THML:thml}
		if markup in markups:
			return markups[markup]
		return None
	
	def get_alternate_filter(self, module):
		markup = ord(module.Markup())
		markups = {SW.FMT_OSIS:osis2, SW.FMT_THML:thml2}
		if markup in markups:
			return markups[markup]
		return None
	
	

def make_thml():
	thmlrenderer = thmlparser.THMLRenderer()
	items.append(thmlrenderer)
	thml = SW.PyThMLHTMLHREF(thmlrenderer)
	thml.thisown = False
	#thmlrenderer
	return thml

def make_osis():
	osisrenderer = osisparser.OSISRenderer()
	items.append(osisrenderer)
	
	osis = SW.PyOSISHTMLHREF(osisrenderer)
	osis.thisown = False
	return osis
 
osis = make_osis()
thml = make_thml()
osis2 = SW.OSISHTMLHREF()
thml2 = SW.ThMLHTMLHREF()

items.extend([osis2, thml2])

