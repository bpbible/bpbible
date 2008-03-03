from util import util
import os

sword_path = None
data_path = "data" + os.path.sep
xrc_path = "xrc" + os.path.sep
graphics_path = "graphics" + os.path.sep

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
