from util import util
import os
from util import osutils
import sys
import getopt
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError


paths_file = "paths.ini"

# Set defaults
data_path = "data/"
xrc_path = "xrc" + os.path.sep
graphics_path = "graphics" + os.path.sep
index_path = "." + os.path.sep
sword_paths_file = "." + os.path.sep

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

if data_path[-1] != os.path.sep:
	data_path += os.path.sep
if index_path[-1] != os.path.sep:
	index_path += os.path.sep
if sword_paths_file[-1] != "/" and sword_paths_file[-1] != "\\":
	sword_paths_file += os.path.sep

sword_paths_file += "sword.conf"

raw = False
name = "BPBible"

MODULE_MISSING_STRING= """<b>This module is not set.</b><br>
This may be because you do not have any of this type of module installed.
Try going to <code>File > Set SWORD Paths</code> to set the module paths up."""

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
def make_template(verse_per_line):
	global bible_template, other_template
	global current_verse_template, verse_compare_template
	br = "<br>" * verse_per_line
	body = (
	'<a href = "#$versenumber" name="$versenumber" target="$versenumber">'
	'<small><sup>$versenumber</sup></small></a> $text %s\n' % br)
	
	bible_template = util.VerseTemplate(body=body)
	#, footer="<br>$range ($version)")


	other_template = util.VerseTemplate(
		body="<b>$range</b><br>$text<p>($description)</p> \n"
	)

	body = ("<a href = '#current' target='$versenumber'><a name='$versenumber'>"
			"<small><sup>$versenumber</sup></small></a></a> "
			"<font color = 'green'>$text</font> %s\n") % br

	current_verse_template = util.VerseTemplate(body)

	verse_compare_template = util.VerseTemplate("$text",
		header="<p><b>(<a href='%s:$version'>$version</a>)"
		"</b> " % BIBLE_VERSION_PROTOCOL
	)


make_template(verse_per_line)
