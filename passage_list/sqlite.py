import sqlite3
from swlib.pysw import VK, VerseList
sqlite3.register_adapter(VK, lambda vk: str(vk))
sqlite3.register_adapter(VerseList, lambda verse_list: str(verse_list))

# XXX: Include subtopic is actually meant to be display tag, but
# I can't be bothered doing the schema migration so close to 0.4.
schema = """\
CREATE TABLE master_topic_record(
schema_version varchar,
base_topic_id integer
);

CREATE TABLE topic(
id integer PRIMARY KEY,
name varchar,
description varchar,
include_subtopic boolean,
parent integer,
order_passages_by varchar,
order_number integer
);

CREATE TABLE passage(
id integer PRIMARY KEY,
passage varchar,
comment varchar,
parent integer,
order_number integer
);
"""

"ALTER topic ADD order_passages_by varchar;"

_CURRENT_VERSION = "0.4.5"

connection = None
previous_filename = None

def load_manager(filename=None):
	"""Connects to the SQLite database with the given filename.

	If this is None, then it connects to an in-memory database (used for
	testing).
	"""
	from passage_list import PassageList, PassageListManager
	sqlite3.register_adapter(PassageList, lambda self: self.id)
	sqlite3.register_adapter(PassageListManager, lambda self: self.id)
	global connection, previous_filename
	if filename is None:
		filename = ":memory:"
	assert connection is None or previous_filename == filename
	previous_filename = filename
	if connection is None:
		connection = sqlite3.connect(filename)
	manager = PassageListManager()
	_maybe_setup_database(manager)
	_load_topic_children(manager)
	manager.parent = None
	return manager

def _maybe_setup_database(manager):
	num_tables = connection.execute("select count(*) from sqlite_master").fetchone()[0]
	if num_tables > 0:
		master_record = connection.execute("select base_topic_id, schema_version from master_topic_record").fetchone()
		manager.id = master_record[0]
		_maybe_upgrade_database(master_record[1])
		return

	connection.executescript(schema)
	save_or_update_item(manager)
	query, values = insert_query("master_topic_record", [
			("schema_version", _CURRENT_VERSION),
			("base_topic_id", manager.id),
		])
	connection.execute(query, values)
	connection.commit()

def _maybe_upgrade_database(version):
	# Quick schema migration.  More to do later.
	if version == "0.4":
		connection.executescript(
			"""
			ALTER TABLE topic ADD COLUMN order_passages_by varchar;
			UPDATE master_topic_record SET schema_version = '%s';
			""" % _CURRENT_VERSION)

def _load_topic_children(topic):
	from passage_list import PassageList
	from passage_entry import PassageEntry
	child_query = "select %s from %s where parent = ? order by order_number"
	subtopics = []

	fields = ", ".join('"%s"' % name for name in ["id",] + PassageList.__fields_to_store__)
	for row in connection.execute(child_query % (fields, "topic"), (topic.id,)):
		subtopic = PassageList("")
		_load_record(subtopic, row)
		subtopic.parent = topic
		_load_topic_children(subtopic)
		subtopics.append(subtopic)

	topic.subtopics = subtopics

	fields = ", ".join(["id",] + PassageEntry.__fields_to_store__)
	passages = []
	for row in connection.execute(child_query % (fields, "passage"), (topic.id,)):
		passage = PassageEntry(None)
		passage.parent = topic
		_load_record(passage, row)
		passage.parent = topic
		passages.append(passage)

	topic.passages = passages

def _load_record(item, row):
	for index, name in enumerate(["id",] + item.__fields_to_store__):
		setattr(item, name, row[index])

def store_topic(topic):
	save_children = topic.id is None
	save_or_update_item(topic)
	if save_children:
		for subtopic in topic.subtopics:
			store_topic(topic)
		for passage in topic.passages:
			save_or_update_item(passage)

def save_or_update_item(item):
	table = item.__table__
	column_values = [('"%s"' % column_name, getattr(item, column_name))
			for column_name in item.__fields_to_store__]
	if item.id is None:
		query, values = insert_query(table, column_values)
	else:
		query, values = update_query(table, column_values, item.id)


	cursor = connection.execute(query, values)
	if item.id is None:
		item.id = cursor.lastrowid

def remove_item(item):
	"""Removes the item from its parent by giving it a NULL parent."""
	query = "UPDATE %s SET parent = null WHERE id = ?" % item.__table__
	connection.execute(query, (item.id,))
	item.parent = None

def insert_query(table, column_values):
	columns = []
	values = []
	value_placeholders = []
	for column_name, value in column_values:
		columns.append(column_name)
		values.append(value)
		value_placeholders.append("?")

	value_placeholders = ",".join(value_placeholders)
	columns = ",".join(columns)
	query = "INSERT INTO %(table)s(%(columns)s) VALUES (%(value_placeholders)s)" % locals()
	return query, values

def update_query(table, column_values, id):
	set_commands = []
	values = []
	for column_name, value in column_values:
		set_commands.append("%s = ?" % column_name)
		values.append(value)

	set_commands = ", ".join(set_commands)
	values.append(id)
	query = "UPDATE %(table)s SET %(set_commands)s WHERE id = ?" % locals()
	return query, values

def save():
	connection.commit()

def close(manager):
	global connection
	remove_deleted_records(manager)
	connection.commit()
	# SQLite 3 documentation says that without this vacuum, the file will
	# never grow smaller.
	# However, vacuuming takes too long, and it does appear to grow smaller
	# anyway, so we don't do it.
	#connection.execute("VACUUM")
	connection.close()
	connection = None

def remove_deleted_records(manager):
	"""Removes all records in the database that have been deleted.

	We don't want to remove them at the time because it would make undo a
	little more complex.
	"""
	connection.execute("DELETE FROM passage WHERE parent IS NULL")
	ids = [row[0] for row in connection.execute(
			"SELECT id FROM topic WHERE parent IS NULL and id != ?", (manager.id,)
		)]
	while ids:
		if len(ids) == 1:
			id_condition = "= %s" % ids[0]
		else:
			id_condition = "IN (%s)" % ",".join(str(id) for id in ids)
		# Deletes all children of deleted topics and all their children.
		# This is essentially emulating cascading delete.
		connection.execute("DELETE FROM topic WHERE id %s" % id_condition)
		connection.execute("DELETE FROM passage WHERE parent %s" % id_condition)
		ids = connection.execute("SELECT id FROM topic WHERE parent %s" % id_condition).fetchall()
		ids = [row[0] for row in connection.execute(
				"SELECT id FROM topic WHERE parent %s" % id_condition
			)]
