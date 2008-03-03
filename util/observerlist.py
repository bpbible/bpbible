#import wx
#class meta(type):
#	def __getitem__(self, slice):
#		if not isinstance(slice, tuple):
#			return self([slice])
#		return self(slice)

class ObserverList(object):
	#__metaclass__ = meta
	def __init__(self, observers=None):
		#super(ObserverList, self).__init__(*args, **kwargs)
		self.on_hold = False
		self.deferred = []
		if observers is None:
			self.observers = []
		else:
			self.observers = observers

	def __call__(self, *args, **kwargs):
		if self.on_hold:
			self.deferred.append((args, kwargs))
			return

		for item in self.observers:
			item(*args, **kwargs)

	def remove(self, item):
		self.observers.remove(item)

	def __isub__(self, item):
		self.remove(item)
		return self

	def hold(self, on_hold=1):
		if on_hold > 0 and self.on_hold == 0:
			self.deferred = []
		
		self.on_hold += on_hold

		if on_hold < 0 and self.on_hold == 0:
			for args, kwargs in self.deferred:
				self(*args, **kwargs)
				
	def finish_hold(self):
		self.hold(-1)
	
	def __repr__(self):
		return "ObserverList%s" % repr(self.observers)
	
	def __iadd__(self, item):
		assert callable(item), "Objects in observer list must be callable"
		self.observers.append(item)
		return self
	
	def prepend(self, item):
		self.observers.insert(0, item)
	
	#def defer(self, *args, **kwargs):
	#	wx.CallAfter(self, *args, **kwargs)

class STOP(object): 
	"""Empty class for stopping a stoppable observer list"""

class StoppableObserverList(ObserverList):
	def __call__(self, *args, **kwargs):
		if self.on_hold:
			self.deferred.append((args, kwargs))
			return

		for item in self.observers:
			if item(*args, **kwargs) == STOP:
				return STOP

if __name__ == '__main__':
	print "Testing ObserverList"
	def print3():
		print 3
	
	def print_(item):
		print item

	ol = ObserverList[print3]
	print repr(ol)
	#print ol()

	print "Running observer"
	ol()

	ol = ObserverList[print_]
	print repr(ol)

	print "Running observer with argument 5"
	ol(5)	
	
	ol = ObserverList[print_]
	print repr(ol)
	print "Putting observers on hold"
	ol.hold()
	print "Running observer with argument 5"
	ol(5)
	print "finishing hold"
	ol.finish_hold()
