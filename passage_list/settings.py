from util.configmgr import config_manager

SECTION_NAME = "Topics"
topic_settings = config_manager.add_section(SECTION_NAME)
topic_settings.add_item("display_tags", True, item_type=bool)
topic_settings.add_item("expand_topic_passages", False, item_type=bool)
topic_settings.add_item("last_selected_topic", [], item_type="pickle")

class Settings(object):
	def get_display_tags(self):
		return topic_settings["display_tags"]

	def set_display_tags(self, display_tags):
		topic_settings["display_tags"] = display_tags

	display_tags = property(get_display_tags, set_display_tags)

	def get_expand_topic_passages(self):
		return topic_settings["expand_topic_passages"]

	def set_expand_topic_passages(self, expand_topic_passages):
		topic_settings["expand_topic_passages"] = expand_topic_passages

	expand_topic_passages = property(get_expand_topic_passages, set_expand_topic_passages)

	def get_last_selected_topic(self):
		from passage_list import get_primary_passage_list_manager
		return get_primary_passage_list_manager().find_topic_by_path(
				topic_settings["last_selected_topic"])

	def set_last_selected_topic(self, topic):
		topic_settings["last_selected_topic"] = topic.path

	last_selected_topic = property(get_last_selected_topic, set_last_selected_topic)
