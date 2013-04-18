# contains code adapted from http://www.ibm.com/developerworks/xml/tutorials/x-epubtut/section5.html
import uuid

from backend.bibleinterface import biblemgr
from swlib.pysw import VK, SW, UserVK, internal_to_user
from backend.verse_template import VerseTemplate, SmartVerseTemplate
from util.debug import dprint, WARNING
from backend import filterutils
import re
import sys

N = 200
#N = 5

RESTRICTED = True

def create_mimetype(path='/path/to/our/epub/directory'):
	f = '%s/%s' % (path, 'mimetype')
	f = open(f, 'w')
	# Be careful not to add a newline here
	f.write('application/epub+zip')
	f.close()

def book_fix(text):
	if text.startswith("Psalms"):
		text = "Psalm" + text[6:]
	
	return text


def get_book(sword_book, bible_book, verse_per_line=False):
	print "fetching", bible_book, "from", sword_book
	bookname = str(bible_book)
	chapter_bookname = book_fix(bookname)

	osis_bookname = VK(bookname).getOSISBookName()
	filename = "book_%s.html" % osis_bookname

	preverse = '<span id="${osisRef}_start" />'

	# templates
	verse_number = u'''<span class="vnumber $numbertype%s"
		   id="${osisRef}_number">
		   $versenumber<span class="post_versenumber_space">&nbsp;</span></span>'''

	# TODO - reinstate  $usercomments $tags after $text?
	body = (u'''%s<span class="zwnj">&zwnj;</span>$text''') % verse_number
#		<a id="${osisRef}_end" osisRef="$osisRef"></a>''') % verse_number
	
	bible_template = SmartVerseTemplate(body=body % (
		''
	), preverse=preverse)
	bible_template.body.verse_per_line=verse_per_line

	toc = []
	chapters = []
	footnotes = {
		'n': [],
		'x': [],
	}
	footnote_types = {
		'n': "Footnotes",
		'x': "Cross-references",
	}

	for chapter in bible_book.chapters:
		if chapter.chapter_number % 10 == 0:
			print osis_bookname, chapter
			if RESTRICTED:
				break

		chapter_id = "%s_%s_start" % (osis_bookname, chapter)
		chapter_link = '<a class="chapter_link" href="#intro">%s</a>' % chapter_bookname
		toc.append(
			'''<a class="toc_chapter_link" href="#chapter_%s">%s</a>''' %
			(chapter_id, chapter)
		)

		ref = "%s %s" % (osis_bookname, chapter)
		content = sword_book.GetReference(ref, end_ref=ref, template=bible_template, max_verses=-1)
#		content = re.sub(r'<(/?)h2([^>]*)>', r'<\1h4\2>', content)
		
		chapter_marker = '<span class="vnumber chapternumber'
		# always a chance
		new_content = content.replace(chapter_marker, 
			chapter_link + chapter_marker)

		osisRef = "%s.%s.%s" % (osis_bookname, chapter, 1)
		if new_content == content:
			print "No chapter intro link found for %s %s" % (osis_bookname, chapter)
			new_content = (chapter_link + 
				(verse_number % '').replace("$numbertype", "chapternumber")
								   .replace("${osisRef}", osisRef)
								   .replace("${versenumber}", "%s" % (chapter))
			)

		content = new_content
		expected_start = preverse.replace("${osisRef}", osisRef) + chapter_link
		if not content.startswith(expected_start):
			print "pre-content chapter intro link found for %s %s" % (osis_bookname, chapter)
			#print "Sample starter content: " + content[:100]
			content = content.replace(chapter_link, 
				"<br / >" + chapter_link)
		
			# now take it back out if write after a lg
			q = '<blockquote class="lg" width="0">'
			content = content.replace(q + '<br / >', q)

		# check - did we have a closing or opening <p> last?
		if 0:
			# note, it's only epubcheck which complains about this. kindlegen
			# complains as this support isn't perfect so it sees some unclosed
			# <p> tags
			add_p = True
			for a in re.findall("<(/?)p>", content):
				add_p = not (a)

			if add_p:
				content += '</p>'
			
		def insert_footnotes(match):
			#print "Inserting footnotes", match
			href = match.group(1)
			url = SW.URL(href.encode("utf8"))
			ftype = url.getParameterValue("type") #x or n
			value = url.getParameterValue("value") #number footnote in verse
			if((not ftype) or (not value)): 
				dprint(WARNING, "Not type or value in showNote", href)
				return ""

			module = biblemgr.get_module(url.getParameterValue("module"))
			passage = url.getParameterValue("passage")
			back_ref = VK(passage).getOSISRef()
			user_ref = book_fix(internal_to_user(passage))

			if not passage or not module:
				print "No passage/module?"
				return ""

			id = "footnote_data_%s_%s" % (back_ref, value)
			#print passage, id
			if ftype in ("n", "x"):
				data = sword_book.GetFootnoteData(module, passage, value, "body")
				if footnotes[ftype] and footnotes[ftype][-1][0] == back_ref:
					footnotes_group = footnotes[ftype][-1]
				else:
					footnotes_group = [back_ref,
						"<div class='verse_footnotes footnote_%s' id='verse_footnote_%s_%s'>%s for "
						"<a href='#%s_start'>%s</a>%%s</div>" % (
							ftype, back_ref, ftype,
							footnote_types[ftype], back_ref, user_ref)
					]
					
					footnotes[ftype].append(footnotes_group)
					
				footnotes_group.append(
					"<div class='footnote_data' id='%s'><span class='footnote_marker'>%s</span>: %s</div>"
					% (id, match.group(3), data)
				)
			else:
				print "Footnote type was", ftype

			id = "verse_footnote_%s_%s" % (back_ref, ftype)
			return 'href="#%s"%s' % (id, match.group(2))


		content = re.sub(
			r'href="newbible://content/(passagestudy\.jsp\?action=showNote&type=[nx]&value=\d+&module=\w+&passage=(?:[^"]+))"(>([^<]*)</a>)',
			insert_footnotes,
			content)

		chapters.append(
			'''
			<div class="chapter" id="chapter_%s">
			<!-- <p> -->
			%s
			</div>
			<hr />
			''' % (chapter_id, content)
		)

	footnotes_html = ''
	for ftype in "nx":
		if footnotes[ftype]:
			footnotes_html += '<div class="book_footnotes"><h3>%s for %s</h3>%s</div>' % (
				footnote_types[ftype],
				bookname,
				'<hr />\n'.join([
					f[1] % ('\n\t'.join(f[2:]))
					for f in footnotes[ftype]
				])
			)

	html_content = '''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
	<head>
		<title>%s</title>
    	<link type="text/css" rel="stylesheet" href="bpbible_epub.css" />
	</head>
	<body>
		<div id="intro">
			<h3>%s</h3>
			<div class="book_toc">%s</div>
			<hr style="clear:both" />
			<div style="clear:both">
			Return to <a href="toc.html">Table of Contents</a>
			</div>
		</div>
		<hr class="pagebreak" />
		<div class="chapterview">
		%s
		</div>
		%s
	</body>
</html>
		''' % (
			bookname,
			bookname,
			'\n'.join(toc),
			'\n'.join(chapters),
			footnotes_html
		)

	# TODO: sword:// links, any others?
	print "Resolving bible links for", bookname
	def replace_bible_links(match):
		ref = match.group(1)
		#print "Replacing bible link", ref
		vk = VK(ref)
		
		return "href='book_%s.html#%s_start'" % (vk.getOSISBookName(), vk.getOSISRef())

	html_content = re.sub(
		r'href="bible:([^"]*)"',
		replace_bible_links,
		html_content)

	return (
		osis_bookname,
		filename,
		bookname,
		html_content.encode("utf8"),
	)


def get_content(module_name="ESV", verse_per_line=False):
	biblemgr.temporary_state(biblemgr.plainstate)
	old_expand_crossref = filterutils.filter_settings["footnote_ellipsis_level"]
	try:
		book = biblemgr.get_module_book_wrapper(module_name)
		biblemgr.set_option("Footnotes", True)
		biblemgr.set_option("Cross-references", True)
		filterutils.filter_settings["footnote_ellipsis_level"] = 0
		content = []

		#vk = VK()
		for bible_book in [bible_book for bible_book in UserVK.books
			#if len(bible_book.chapters) < N
			if not RESTRICTED or (
				bible_book.bookname in ("Psalms", "Matthew")
			)
		]:#VK.books:
			print "Processing", bible_book
			content.append(get_book(book, bible_book, verse_per_line=verse_per_line))
		#	if bible_book.bookname == "Genesis": break
		#	if bible_book.bookname == "Joshua": break
	finally:
		filterutils.filter_settings["footnote_ellipsis_level"] = old_expand_crossref
		biblemgr.restore_state()
	
	return content

# 				old_mod_skiplinks = mod.getSkipConsecutiveLinks()
# 				mod.setSkipConsecutiveLinks(True)
# 				try:
# 					vk.Persist(1)
# 					mod.setKey(vk)
# 					#print repr(mod.Error())
# 					mod.increment(1)
# 
# 					if mod.Error() != '\x00':
# 						print "Mod had an error"
# 						no_more = True
# 					else:
# 						if book.chapter_view:
# 							new_ref = vk.get_chapter_osis_ref()
# 						else:
# 							new_ref = vk.getOSISRef()
# 				finally:
# 					mod.setKey(SW.Key())
# 					mod.setSkipConsecutiveLinks(old_mod_skiplinks)
		

import zipfile, os

def create_archive(content, name="sample", long_name=None, verse_per_line=False):
	'''Create the ZIP archive.  The mimetype must be the first file in the archive 
	and it must not be compressed.'''

	if long_name is None: long_name = name

	epub_name = '%s.epub' % name
	book_uuid = uuid.uuid4()
	book_metadata = dict(
		title=long_name,
		creator='BPBible ePub generator',
		uuid=book_uuid,
	)

	# Open a new zipfile for writing
	epub = zipfile.ZipFile(epub_name, 'w')

	# Add the mimetype file first and set it to be uncompressed
	epub.writestr('mimetype', 'application/epub+zip',
			compress_type=zipfile.ZIP_STORED)

	epub.writestr('META-INF/container.xml',
		'''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
	<rootfile full-path="OEBPS/content.opf"
	 media-type="application/oebps-package+xml" />
  </rootfiles>
</container>''')

	# use book_ as a prefix as it seems epubcheck doesn't like leading numbers
	# (e.g. 2Thess)
	items = '\n    '.join([
		'<item id="book_%s" href="%s" media-type="application/xhtml+xml"/>' %
			(item[0], item[1])
		for item in content
	])
	html_toc = '\n    '.join([
		'<div class="toc_book %s">'
		'<a href="%s">%s</a></div>' %
			("odd" if idx % 2 == 1 else "even", item[1], item[2])
		for idx, item in enumerate(content)
	])

	itemrefs = '\n    '.join([
		'<itemref idref="book_%s" />' % item[0] for item in content
	])

	navpoints = '\n'.join([
	'''
    <navPoint id="navpoint-%d" playOrder="%d">
      <navLabel>
        <text>%s</text>
      </navLabel>
      <content src="%s"/>
    </navPoint>
	''' % (idx+3, idx+3, item[2], item[1]) 
		for idx, item in enumerate(content)
	])
	book_metadata["html_toc"] = html_toc
	book_metadata["items"] = items
	book_metadata["itemrefs"] = itemrefs
	book_metadata["navpoints"] = navpoints
	
	epub.writestr('OEBPS/content.opf',
		'''<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            unique-identifier="bookid" version="2.0">
  <metadata>
    <dc:title>%(title)s</dc:title>
    <dc:creator>%(creator)s</dc:creator>
    <dc:identifier
id="bookid">urn:uuid:%(uuid)s</dc:identifier>
    <dc:language>en-US</dc:language>
    <meta name="cover" content="cover-image" />
  </metadata>
  <manifest>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
    <item id="cover" href="title.html" media-type="application/xhtml+xml"/>
    <item id="toc" href="toc.html" media-type="application/xhtml+xml"/>
    %(items)s
    <item id="cover-image" href="images/cover.png" media-type="image/png"/>
    <item id="css" href="bpbible_epub.css" media-type="text/css"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="cover" linear="no"/>
    <itemref idref="toc" />
    %(itemrefs)s
  </spine>
  <guide>
    <reference href="title.html" type="cover" title="Cover"/>
	<reference type="toc" title="Table of Contents" href="toc.html"/> </guide>
  </guide>
</package>''' % book_metadata)

	epub.writestr('OEBPS/toc.ncx',
		'''<?xml version='1.0' encoding='utf-8'?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN"
                 "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid"
content="urn:uuid:%(uuid)s"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle>
    <text>%(title)s</text>
  </docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel>
        <text>Book cover</text>
      </navLabel>
      <content src="title.html"/>
    </navPoint>
    <navPoint id="navpoint-2" playOrder="2">
      <navLabel>
        <text>Table of Contents</text>
      </navLabel>
      <content src="toc.html"/>
    </navPoint>
    %(navpoints)s
  </navMap>
</ncx>''' % book_metadata)

	epub.writestr('OEBPS/title.html',
		'''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>%(title)s</title>
    <link type="text/css" rel="stylesheet" href="bpbible_epub.css" />
  </head>
  <body>
    <h1>%(title)s</h1>
    <div><img src="images/cover.png" alt="Title page"/></div>
  </body>
</html>
		''' % book_metadata)

	epub.writestr('OEBPS/toc.html',
		'''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <title>%(title)s</title>
    <link type="text/css" rel="stylesheet" href="bpbible_epub.css" />
  </head>
  <body>
    <h1>%(title)s</h1>
    <div class="Bible_ToC">
		%(html_toc)s
	</div>
  </body>
</html>
		''' % book_metadata)

	for id, filename, bookname, book_content in content:
		epub.writestr("OEBPS/" + filename, book_content)

	epub.write("css/bpbible_epub.css", "OEBPS/bpbible_epub.css")
	epub.write("graphics/bible-256x256.png", "OEBPS/images/cover.png")
	
	# For the remaining paths in the EPUB, add all of their files
	# using normal ZIP compression
	#for p in os.listdir('.'):
	#	for f in os.listdir(p):
	#		epub.write(os.path.join(p, f)), compress_type=zipfile.ZIP_DEFLATED)
	epub.close()

	import os
	os.system("cp %s %s_epub.zip" % (epub_name, name))

def main():
	global RESTRICTED
	book = "ESV"
	long_name = "English Standard Version"
	book = "KJV"
	long_name = "King James Version"
	#book = "NASB"
	#long_name = "New American Standard Bible"
	#book = "WEB"
	#long_name = "World English Bible"
	if 'all' in sys.argv:
		RESTRICTED = False

	create_archive(get_content(book, verse_per_line=False), book, long_name)

main()
