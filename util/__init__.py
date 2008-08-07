"""Utility functions."""
import sys
import time

def noop(*args, **kwargs):
	"""Do nothing."""

def is_py2exe():
	return hasattr(sys, "frozen")	
	
def timeit(f, *args, **kwargs):
	t = time.time()
	times = kwargs.pop("times", 1)
	last_result = None
	try:
		for a in xrange(times):
			last_result = f(*args, **kwargs)

	finally:
		print "%s took %f time" % (f.__name__, time.time() - t)
		return last_result

	
