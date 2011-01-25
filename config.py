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
If the paths include $DATADIR, it will be replaced with the wx user data dir
for the appropriate platform.
"""

from util import osutils
user_data_dir = osutils.get_user_data_dir()

def get_path_if_exists(path, alternate_path):
	"""Expands the given path and checks if it exists.

	If it is an empty path, then alternate_path will be returned.
	If the path does not exist, then it will be created if possible.
	"""
	if "$DATADIR" in path:
		path = path.replace("$DATADIR", user_data_dir)

	if not path:
		path = alternate_path

	return path

def create_path_if_not_exists(path):
	if os.path.exists(path):
		return

	try:
		os.makedirs(path)
	except OSError, e:
		sys.stderr.write(str(e))

if os.path.isfile(paths_file):
	try:
		paths_file_parser = RawConfigParser()
		paths_file_parser.read([paths_file])
		data_path = get_path_if_exists(
				paths_file_parser.get("BPBiblePaths", "DataPath"),
				data_path
			)
		index_path = get_path_if_exists(
				paths_file_parser.get("BPBiblePaths", "IndexPath"),
				index_path
			)
		sword_paths_file = get_path_if_exists(
				paths_file_parser.get("BPBiblePaths", "SwordPath"),
				sword_paths_file
			)
	except (NoSectionError, NoOptionError):
		pass

"""Attempt to override paths with command-line arguments

Call BPBible like this:
python bpbible.py --data-path=data --index-path=. --sword-path=.
"""
try:
	opts, all = getopt.getopt(sys.argv[1:], "d", ["data-path=", "index-path=", "sword-path=", "no-splashscreen"])
except getopt.GetoptError:
	opts = []

if opts:
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

create_path_if_not_exists(data_path)
create_path_if_not_exists(index_path)


raw = False

def name():
	# Note that the string BPBible is *not* translated, since it is the
	# application trade name and must be preserved in all languages in any
	# place it occurs (including this one).
	return "BPBible"

def MODULE_MISSING_STRING():
	return _("""<b>This book is not set.</b><br>
This may be because you do not have any of this type of book installed.
<p> If you don't have any of this type of book, first download them from <a
href="http://www.crosswire.org/sword/modules/index.jsp">http://www.crosswire.org/sword/modules/index.jsp</a>.<br>
Then to install them, either drag them onto BPBible, or go <code>File >
Install Books...</code> and select the books.
<p> If you have already have SWORD books installed, go to <code>File >
Set SWORD Paths</code> and add the path where the books are installed to the book search paths.
""")

def MAX_VERSES_EXCEEDED():
	return _("""<p><b>[Reference clipped as the maximum verse limit (%d verses) has been exceeded.
<br>This probably means the reference was invalid]</b>""")

from util.configmgr import ConfigManager
bpbible_configuration = ConfigManager("bpbible.conf")
release_settings = bpbible_configuration.add_section("Release")
release_settings.add_item("version", "DEV", item_type=str)
release_settings.add_item("is_released", False, item_type=bool)
splashscreen_settings = bpbible_configuration.add_section("SplashScreen")
splashscreen_settings.add_item("show", True, item_type=bool)
bpbible_configuration.load()

version = release_settings["version"]

def is_release():
	"""Checks if this is a released version of BPBible."""
	return release_settings["is_released"]

xulrunner_version = "UNKNOWN"

def show_splashscreen():
	if ("--no-splashscreen", "") in opts:
		return False

	return splashscreen_settings["show"]

BIBLE_VERSION_PROTOCOL = "setbibleversion"

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


preverse = '<a name="${osisRef}_start" osisRef="$osisRef"></a>'
# templates
verse_number = u'''
	<a class="vnumber $numbertype%s"
	   href="nbible://$internal_reference"
	   osisRef="$osisRef"
	   reference="$reference">
	   $versenumber</a>'''

body = (u'''%s $text $usercomments $tags
	<a name="${osisRef}_end" osisRef="$osisRef"></a>''') % verse_number

bible_template = SmartVerseTemplate(body=body%'', preverse=preverse)
bible_template_without_headings = SmartVerseTemplate(body=body % '',
	headings=u'', preverse=preverse)


current_verse_template = SmartVerseTemplate(body % ' currentverse',
											preverse=preverse)


#, footer="<br>$range ($version)")


commentary_template = VerseTemplate(
	body=u"<div class='commentary_entry'><h3>$reference</h3>$text\n</div>"
)
dictionary_template = VerseTemplate(
	body=u"<div class='dictionary_entry'><h3>$reference</h3>$text\n</div>"
)
genbook_template = VerseTemplate(
	body=u"<div class='genbook_entry'><div class='genbook_key' level='$level'>$breadcrumbed_reference</div>$text\n</div>"
)


# TODO: do we want this to have tags? I'd guess not
verse_compare_template = VerseTemplate(
	u'<glink href="nbible:$internal_reference">'
	u'<small><sup>$versenumber</sup></small></glink> $text ',
	
	header=u"<p><b>(<a href=\"%s://content/$version\">$version</a>)"
	u"</b> " % BIBLE_VERSION_PROTOCOL
)
