"""Search utilities. These are placed in a different package, otherwise
cPickle gives error messages like this:

cPickle.PicklingError: Can't pickle search.search.BookIndex: import of module se
arch.search failed
"""
import cPickle
import os
import config
import zipfile
import gzip
from configmgr import config_manager
import util
from swlib import pysw


search_config = config_manager.add_section("Search")
search_config.add_item("zip_indexes", False, item_type=bool)

def WriteIndex(index, path = config.index_path, progress=util.noop):
	z = zipfile.ZipFile("%s%s.idx" % (path, index.version), "w",  
		zipfile.ZIP_DEFLATED)

	length = float(len(index.books) + 2)
	for idx, item in enumerate(index.books):
		# two translates in case of dashes
		bookname_ui = pysw.locale.translate(
			pysw.locale.translate(
				item.bookname
			)
		).decode(pysw.locale_encoding)
		
		continuing = progress((bookname_ui, 100*idx/length))
		if not continuing: return
		
		z.writestr("books/" + item.bookname.encode("utf8"),
			cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
		)
	
	b = index.books
	del index.books

	index.book_names = [x.bookname for x in b]
	
	try:
		continuing = progress(("Index", 100*(length-1)/length))	
		if not continuing: return
	
		z.writestr("index", cPickle.dumps(
			index,
			cPickle.HIGHEST_PROTOCOL
		))
	finally:
		del index.book_names	
		index.books = b

	z.close()

	#if search_config["zip_indexes"]:
	#	f = gzip.GzipFile("%s%s.idxz" % (path, index.version), "w",
	#			compresslevel=5)
	#else:
	#	f = open("%s%s.idx" % (path, index.version), "wb")

	#cPickle.dump(index, f, cPickle.HIGHEST_PROTOCOL)

def ReadIndex(version, path = config.index_path):
	z = zipfile.ZipFile("%s%s.idx" % (path, version))
	try:
	
		index = cPickle.loads(z.read("index"))
		index.books = []
		for item in index.book_names:
			index.books.append(
				cPickle.loads(
					z.read("books/" + item.encode("utf8"))
				)
			)
			

		del index.book_names
	
	finally:
		# make sure we close the file
		z.close()
	
	return index
	#if os.path.exists("%s%s.idxz" % (path, version)):
	#	f = gzip.GzipFile("%s%s.idxz" % (path, version))
	#else:
	#	f = open("%s%s.idx" % (path, version), "rb")
	#
	#return cPickle.load(f)

def IndexExists(version, path = config.index_path):
	return os.path.exists("%s%s.idx" % (path, version))

def DeleteIndex(version, path=config.index_path):
	if os.path.exists("%s%s.idx" % (path, version)):
		os.remove("%s%s.idx" % (path, version))
