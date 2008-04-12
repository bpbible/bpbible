from backend.bibleinterface import biblemgr
from swlib.pysw import VK

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

	#
	vk = VK((chapter, chapter))

	mod = biblemgr.bible.mod
	headings = []
	for item in vk:	
		mod.setKey(item)
		mod.RenderText()
		headings += ((item, mod.RenderText(heading))
			for heading in biblemgr.bible.get_headings(item.getText()))
	
	biblemgr.restore_state()
	version_headings[chapter] = headings
	return headings

if __name__ == '__main__':
	print get_chapter_headings("Matthew 5")
