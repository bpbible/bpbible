try:
#	from swlib import BenSword 
#	from swlib import Sword
	from BenSword import *

	from Sword import *
	from Sword import _swig_setattr	
except ImportError, e:
	#try:
	#	from swlib.Sword import Callback as MarkupCallback
	#	from swlib.Sword import Callback2 as RenderCallback
	#	from swlib import Sword
	#	Sword.MarkupCallback = MarkupCallback
	#	Sword.RenderCallback = RenderCallback

	#	
	#	BenSword = Sword
	#except ImportError, e:
		try:
			#from swlib.Sword import MarkupCallback
			#from swlib.Sword import RenderCallback
			#from swlib import Sword
			#BenSword = Sword
			from Sword import MarkupCallback
			from Sword import _swig_setattr			
			#from Sword import 
			from Sword import *
			
		except ImportError:
			print "You do not seem to have Ben's sword extensions"
			raise

