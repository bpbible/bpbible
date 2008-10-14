from backend.verse_template import VerseTemplate, SmartVerseTemplate
import os
import sys
import getopt
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError


paths_file = "paths.ini"

# Set defaults
data_path = "data/"
xrc_path = "xrc/"
graphics_path = "graphics/"
index_path = "./"
sword_paths_file = "./"
error_log = "error.log"

"""Attempt to override paths with settings in an INI file

The file referenced by the variable paths_file should be like this:

[BPBiblePaths]
DataPath = data
IndexPath = .
SwordPath = .

If the paths do not exist, they will be ignored.
"""
if os.path.isfile(paths_file):
	try:
		paths_file_parser = RawConfigParser()
		paths_file_parser.read([paths_file])
		v = paths_file_parser.get("BPBiblePaths", "DataPath")
		if os.path.isdir(v):
			data_path = v
		v = paths_file_parser.get("BPBiblePaths", "IndexPath")
		if os.path.isdir(v):
			index_path = v
		v = paths_file_parser.get("BPBiblePaths", "SwordPath")
		if os.path.isdir(v):
			sword_paths_file = v
	except (NoSectionError, NoOptionError):
		pass

"""Attempt to override paths with command-line arguments

Call BPBible like this:
python bpbible.py --data-path=data --index-path=. --sword-path=.
"""
try:
	opts, all = getopt.getopt(sys.argv[1:], "d", ["data-path=", "index-path=", "sword-path="])
except getopt.GetoptError:
	opts = None

if opts != None:
	for o, v in opts:
		if o == "--data-path" and os.path.isdir(v):
			data_path = v
		elif o == "--index-path" and os.path.isdir(v):
			index_path = v
		elif o == "--sword-path" and os.path.isdir(v):
			sword_paths_file = v

if data_path[-1] not in "\\/":
	data_path += "/"
if index_path[-1] not in "\\/":
	index_path += "/"
if sword_paths_file[-1] not in "\\/" and sword_paths_file[-1] not in "\\/":
	sword_paths_file += "/"

sword_paths_file += "sword.conf"

raw = False
name = "BPBible"

MODULE_MISSING_STRING= """<b>This book is not set.</b><br>
This may be because you do not have any of this type of book installed.
<p> If you don't have any of this type of book, first download them from <a
href="http://www.crosswire.org/sword/modules/index.jsp">http://www.crosswire.org/sword/modules/index.jsp</a>.<br>
Then to install them, either drag them onto BPBible, or go <code>File >
Install Books...</code> and select the books.
<p> If you have already have SWORD books installed, go to <code>File >
Set SWORD Paths</code> and add the path where the books are installed to the book search paths.
"""

MAX_VERSES_EXCEEDED = """<p><b>[Reference clipped as the maximum verse limit (%d verses) has been exceeded.
<br>This probably means the reference was invalid]</b>"""

BIBLE_VERSION_PROTOCOL = "set_bible_version"

title_str = "%(verse)s - %(name)s"

# settings
#search_disappear_on_doubleclick = True
verse_per_line = False
use_system_inactive_caption_colour = False
#
#use_osis_parser = True
#use_thml_parser = True
#
#expand_thml_refs = True
#footnote_ellipsis_level = 2
#
#strongs_headwords = True
#strongs_colour = "#0000ff"
#plain_xrefs = False


# templates
body = (
u'<glink href="nbible:$versenumber">'
u'<small><sup>$versenumber</sup></small></glink>$text $tags')


bible_template = SmartVerseTemplate(body=body)

#, footer="<br>$range ($version)")


other_template = VerseTemplate(
	body=u"<b>$range</b><br>$text<p>($description)</p> \n"
)
dictionary_template = VerseTemplate(
	body=u"<br>$text<p>($description)</p> \n"
)


body = (u"<glink href='nbible:$versenumber#current'>"
		u"<small><sup>$versenumber</sup></small></glink>"
		u"<font color = 'green'>$text</font> $tags")

current_verse_template = SmartVerseTemplate(body)

# TODO: do we want this to have tags? I'd guess not
verse_compare_template = VerseTemplate(
	u"<sup>$versenumber</sup> $text",
	header=u"<p><b>(<a href='%s:$version'>$version</a>)"
	u"</b> " % BIBLE_VERSION_PROTOCOL
)
