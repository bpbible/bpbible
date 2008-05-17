"""Search utilities. These are placed in a different package, otherwise
cPickle gives error messages like this:

cPickle.PicklingError: Can't pickle search.search.BookIndex: import of module se
arch.search failed
"""
import cPickle
import os
import config
import gzip
from configmgr import config_manager


search_config = config_manager.add_section("Search")
search_config.add_item("zip_indexes", True, item_type=bool)

def WriteIndex(index, path = config.index_path):
	if search_config["zip_indexes"]:
		f = gzip.GzipFile("%s%s.idxz" % (path, index.version), "w",
				compresslevel=5)
	else:
		f = open("%s%s.idx" % (path, index.version), "w")

	cPickle.dump(index, f)

def ReadIndex(version, path = config.index_path):
	if os.path.exists("%s%s.idxz" % (path, version)):
		f = gzip.GzipFile("%s%s.idxz" % (path, version))
	else:
		f = open("%s%s.idx" % (path, version))
	
	return cPickle.load(f)

def IndexExists(version, path = config.index_path):
	return os.path.exists("%s%s.idx" % (path, version)) or \
			os.path.exists("%s%s.idxz" % (path, version))

def DeleteIndex(version, path = config.index_path):
	if os.path.exists("%s%s.idx" % (path, version)):
		os.remove("%s%s.idx" % (path, version))
	if os.path.exists("%s%s.idxz" % (path, version)):
		os.remove("%s%s.idxz" % (path, version))
