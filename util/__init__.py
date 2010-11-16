"""Utility functions."""
import sys
import time
import cProfile

if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    default_timer = time.clock
else:
    # On most other platforms the best timer is time.time()
    default_timer = time.time

def noop(*args, **kwargs):
	"""Do nothing."""

def is_py2exe():
	return hasattr(sys, "frozen")	
	
def profile_func(f):
	def x(*args, **kwargs): 
		return profile(f, *args, **kwargs)
	
	return x

def time_func(f):
	def x(*args, **kwargs): 
		return timeit(f, *args, **kwargs)
	
	return x

def timeit(f, *args, **kwargs):
	t = default_timer()
	times = kwargs.pop("times", 1)
	last_result = None
	try:
		for a in xrange(times):
			last_result = f(*args, **kwargs)

		return last_result

	finally:
		print "%s took %f time" % (f.__name__, default_timer() - t)

def profile(callable, *args, **kwargs):
	prof = cProfile.Profile()
	sort = kwargs.pop("sort", -1)

	result = None
	try:
		return prof.runcall(callable, *args, **kwargs)
	finally:
		prof.print_stats(sort)

	
class classproperty(object):
	def __init__(self, data):
		self._data = data

	def __get__(self, obj, objtype):
		return self._data(objtype)
	
class overridableproperty(object):
	"""
	A computed default value which can be overridden. 
	
	@overridableproperty
	def template(self):
		return None
	
	Is approximately the equivalent of:
	def get_template(self):
		if hasattr(self, "_template"):
			return self._template

		return None

	def set_template(self, template):
		self._template = template
	
	def del_template(self):
		del self._template
	
	template = property(get_template, set_template, del_template)
	del get_template, set_template, del_template
	"""
	
	def __init__(self, function, storage=None):
		self._default_get = function
		if storage is None:
			self.storage = "__%s_data" % self._default_get.__name__
		else:
			self.storage = storage

	def __get__(self, obj, objtype):
		if obj is None:
			return self

		if not hasattr(obj, self.storage):
			return self._default_get(obj)
		
		return getattr(obj, self.storage)

	def __set__(self, obj, value):
		return setattr(obj, self.storage, value)
	
	def __delete__(self, obj):
		return delattr(obj, self.storage)


