sources = (
	HISTORY,
	#HISTORY_BACK,
	QUICK_SELECTOR,
	VERSE_TREE,
	BIBLE_REF_ENTER,
	#TOOLTIP,
	BIBLEFRAME,
	LINK_CLICKED,
	SETTINGS_CHANGED,
	RANDOM_VERSE,
	VERSE_LINK_SELECTED,
	VERSE_MOVE,
	CHAPTER_MOVE,
	HARMONY,
	SEARCH,
	TOPIC_LIST,
	LOADING_SETTINGS,
	PASSAGE_TAGGED,
	HEADER_BAR,
	COMMENT_DELETED,
) = range(18)

class BibleEvent(object):
	def __init__(self, ref, settings_changed=False, source=None, ref_to_scroll_to=None):
		self.ref = ref
		self.settings_changed = settings_changed
		self.source = source
		self.ref_to_scroll_to = ref_to_scroll_to
