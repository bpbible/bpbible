from util.configmgr import config_manager

options = config_manager.add_section("Options")
options.add_item("columns", False, item_type=bool)
options.add_item("verse_per_line", False, item_type=bool)
options.add_item("continuous_scrolling", True, item_type=bool)
options.add_item("headings", True, item_type=bool)
options.add_item("cross_references", True, item_type=bool)
options.add_item("footnotes", True, item_type=bool)
options.add_item("strongs_numbers", True, item_type=bool)
options.add_item("strongs_blocked", True, item_type=bool)
options.add_item("morphology", True, item_type=bool)
options.add_item("morph_segmentation", False, item_type=bool)
options.add_item("raw", False, item_type=bool)
options.add_item("colour_speakers", "off", item_type=str)


def all_options():
	return options.items.keys()

def get_js_option_value(option):
	type = options.item_types[option]
	if type not in (str, bool):
		raise TypeError("Only bools supported at the moment (option: %s)" % option)
	if type == bool:
		return "true" if options[option] else "false"
	else:
		return options[option].encode("utf8")
