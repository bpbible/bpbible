from util import string_util
import re
from util.configmgr import config_manager
from util.debug import dprint, ERROR, MESSAGE, WARNING
from gui import fonts
from swlib import pysw


html_settings = config_manager.add_section("Html")
html_settings.add_item("zoom_level", 0, item_type=int)

# some magic zoom constants
zoom_levels = {-2: 0.75, 
			   -1: 0.83, 
			   	0: 1, 
				1: 1.2, 
				2: 1.44, 
				3: 1.73, 
				4: 2,
				5: 2.5,
				6: 3,
				7: 3.5
				}


def get_text_size(base):
	ansa = zoom_levels[html_settings["zoom_level"]] * base
	return ansa

def zoom(direction):
	if direction == 0:
		# reset zoom
		html_settings["zoom_level"] = 0
	else:
		html_settings["zoom_level"] += direction

		# but make sure it is in bounds
		html_settings["zoom_level"] = (
			max(min(html_settings["zoom_level"], 7), -2)
		)
	


def convert_lgs(text, width):
	blocks = []
	#def extractor(text):
	#	t = '<block id="%d">' % len(blocks)
	#	blocks.append(text.group(1))
	#	return t

	parts = []
	for item in re.finditer(
		r'<indent-block-(start|end) source="lg"( width="0")? />', text
	):
		parts.append((item.group(1), item.span()))

	if not parts:
		return text
	
	if parts[0][0] == "end":
		parts.insert(0, ("start", (0, 0)))
	
	if parts[-1][0] == "start":
		parts.append(("end", (len(text), len(text))))

	if len(parts) % 2 != 0:
		dprint(ERROR, "Num of parts is odd!!", parts)
		return text

	blocks = [[False, text[:parts[0][1][0]]]]
	for a in range(len(parts)/2):
		f_type, (f_start, f_end) = parts[2*a]
		e_type, (e_start, e_end) = parts[2*a+1]
		if f_type != "start" or e_type != "end":
			dprint(ERROR, "Start or end in wrong spot!!!", parts)
			return text

		
		blocks.append([True, text[f_end:e_start]])
		if a == len(parts)/2 - 1:
			next_end = len(text)
		else:
			next_end = parts[2*a+2][1][0]

		blocks.append([False, text[e_end:next_end]])
	
	#start = 
	#end = '(.*?)(<indent-block-end source="lg" />)'
	#

	#s = re.compile(start + end[:-1] + "|$)", re.S)
	#s2 = re.compile(end, re.S)
	#
	#text, num = s.subn(
	#	extractor,
	#	text
	#)

	#text = s2.sub(
	#	extractor,
	#	text
	#)

	for block in blocks:
		if not block[0]:
			continue

		digits = "[0-9]"
		if pysw.locale_digits:
			digits = "[%s]" % pysw.locale_digits["digits"]

		block[1] = """<indent-area-start /><table cellspacing=0 cellpadding=0 width=100%%><tr><td width=%dpx></td><td>%s</td></tr></table><indent-area-end />""" % (
		width,
		re.sub(
			r'(^|<(indent-block-end|/h6|br|/p)((>)|(/>)|( [^>]*>)))\s*((<indent-block-start source="l"[^>]+>)?\s*)(<glink href="nbible:[^"]*"[^>]*><small><sup>%s*</sup></small></glink>)' % digits,
	r"\1</td></tr><tr><td valign=top align=center width=%dpx>\9</td><td>\7" % width,
	block[1]
		)
		)
	
	return re.sub("<br /></td>", "</td>", 
		u''.join(text for is_lg, text in blocks))
	
def convert_language(text, language_code):
	# remove all &#1243;'s which will stop our language recognition
	text = string_util.amps_to_unicode(text, replace_specials=False)

	# put greek and hebrew in their fonts
	for lang_code, letters, dont_use_for in (
		# ancient greek (to 1453)
		("grc", string_util.greek, ("el", "grc")),

		# Hebrew (generally)
		("he", string_util.hebrew, ("he",)),
	):
		# if we are, say, a greek book, don't take greek out specially
		if language_code in dont_use_for:
			continue

		default, (font, size, use_in_gui) = \
			fonts.get_language_font_params(lang_code)
		text = string_util.insert_language_font(text, letters, font, size)

	return text
