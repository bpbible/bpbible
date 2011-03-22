class ObserverList(object):
	__slots__ = ["on_hold", "deferred", "observers"]
	def __init__(self, observers=[]):
		self.on_hold = False
		self.deferred = []
		self.observers = []
		for observer in observers:
			self.add_observer(observer)

	def __call__(self, *args, **kwargs):
		if self.on_hold:
			self.deferred.append((args, kwargs))
			return
		
		# take a copy so the objects can remove themselves from the list while
		# iterating over it
		for function, initial_args in self.observers[:]:
			if not self._call_function(function, initial_args + args, kwargs):
				return

	def _call_function(self, function, args, kwargs):
		function(*args, **kwargs)
		return True

	def remove(self, item):
		"""Removes the entry with the given callable."""
		for index, (function, args) in enumerate(self.observers):
			if function == item:
				del self.observers[index]
				return
		raise ValueError("ObserverList.remove(x): x not in list.")

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
		self.add_observer(item)
		return self

	def add_observer(self, function, args=()):
		"""Adds the given function as an observer to the list.

		This function will be called whenever the observer list is called,
		with the same arguments as the observer list is called with.

		args: These arguments are passed to the function before the arguments
			given when the observer list is called.
		"""
		assert callable(function), "Objects in observer list must be callable"
		self.observers.append((function, args))
	
	def prepend(self, item):
		self.observers.insert(0, (item, ()))

class STOP(object): 
	"""Empty class for stopping a stoppable observer list"""

class StoppableObserverList(ObserverList):
	"""This list adds support for a stoppable observer list.

	If any observer returns STOP, then further observers will not be called.
	"""
	def _call_function(self, function, args, kwargs):
		result = function(*args, **kwargs)
		return result != STOP

if __name__ == '__main__':
	print "Testing ObserverList"
	def print3():
		print 3
	
	def print_(item):
		print item

	ol = ObserverList([print3])
	print repr(ol)

	print "Running observer"
	ol()

	ol = ObserverList([print_])
	print repr(ol)

	print "Running observer with argument 5"
	ol(5)	
	
	ol = ObserverList([print_])
	print repr(ol)
	print "Putting observers on hold"
	ol.hold()
	print "Running observer with argument 5"
	ol(5)
	print "finishing hold"
	ol.finish_hold()

	def print_with_bound_arguments(a, b, item):
		print a, b
		print item

	ol = ObserverList()
	ol.add_observer(print_with_bound_arguments, args=(1, 2))
	ol(3)

	ol.add_observer(print_with_bound_arguments, (1, 3))
	ol(4)
	ol.remove(print_with_bound_arguments)
	ol(5)
	ol.remove(print_with_bound_arguments)
	ol(6)
