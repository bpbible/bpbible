filtering = "quotes backend.filterutils backend.osisparser backend.thmlparser protocol_handlers"
tooltip_bits = filtering + " config display_options tooltip protocols displayframe new_displayframe bookframe bibleframe genbooktree genbookframe gui.reference_display_frame search.highlighted_frame preview_window header_bar versecompare mainframe"
copying = "templatemanager copyverses"
ALL = "filtering tooltip_bits".split()

def reboot_section(name):
	for item in globals()[name].split():
		print "Reloading", item
		# fromlist non-empty means for A.B B is returned, not A
		# HACK: fromlist=True
		m = __import__(item, fromlist=True)
		reload(m)
	
	print "Reloaded", name

def reload_all():
	for item in ALL:
		reboot_section(item)
