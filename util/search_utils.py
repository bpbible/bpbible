"""Search utilities. These are placed in a different package, otherwise
cPickle gives error messages like this:

cPickle.PicklingError: Can't pickle search.search.BookIndex: import of module se
arch.search failed
"""
import cPickle
import os


def WriteIndex(index, path = ""):
	f = open("%s%s.idx"	% (path, index.version), "w")
	cPickle.dump(index, f)

def ReadIndex(version, path = ""):
	f = open("%s%s.idx" % (path, version))
	return cPickle.load(f)

def IndexExists(version, path = ""):
	return os.path.exists("%s%s.idx" % (path, version))	

def DeleteIndex(version, path=""):
	#try:
	os.remove("%s%s.idx" % (path, version))
	#except Exception, e:
	#	return e

