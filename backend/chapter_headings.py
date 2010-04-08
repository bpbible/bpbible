from backend.bibleinterface import biblemgr
from swlib.pysw import EncodedVK
import re

headings_cache = {}

def clear_cache(self, biblemgr=None):
	global headings_cache
	headings_cache = {}

biblemgr.on_before_reload += clear_cache


def get_chapter_headings(chapter):
	"""Get chapter headings from the current Bible for a given chapter

	chapter must be a whole chapter reference, not a verse in the chapter
	Returns list of (VK, heading text)
	"""
	if biblemgr.bible.mod is None:
		return []

	version_headings = headings_cache.setdefault(biblemgr.bible.version, {})
	if chapter in version_headings:
		return version_headings[chapter]
		
	# put ourselves into a plain state
	biblemgr.temporary_state(biblemgr.plainstate)

	# and turn on headings
	biblemgr.set_option("Headings", True)

	vk = EncodedVK(("%s:0" % chapter, chapter), headings=True)

	mod = biblemgr.bible.mod
	headings = []
	for item in vk:	
		mod.setKey(item)
		content = mod.RenderText()

		# if it was in verse 0, link to verse 1 for now
		if item.Verse() == 0:
			item.Verse(1)
		
		hs = biblemgr.bible.get_headings(item.getText())

		# see comment in book.py for why we are checking if it starts with <
		# (short version - pre-verse div's)
		# try to handle pre-verse headings in div's
		content = '\n'.join(mod.RenderText(heading)
			for heading, canonical in hs if heading.startswith("<")) + content
		
		# and non-div pre-verse headings
		headings += ((item, mod.RenderText(heading))
			for heading, canonical in hs if not heading.startswith("<"))

		headings += ((item, text) for heading, text in re.findall(
			'(<h6 class="heading" canonical="[^"]*">(.*?)</h6>)', 
			content, re.U) if text)
	
	biblemgr.restore_state()
	version_headings[chapter] = headings
	return headings

if __name__ == '__main__':
	print get_chapter_headings("Psalm 3")
