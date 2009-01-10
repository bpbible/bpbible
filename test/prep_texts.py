import os
from swlib.pysw import SW
import zipfile

encodings = dict(cp1252="Latin-1", utf8="UTF-8")
text = """\
$$$Key1
First key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la 
lumi\xe8re d'avec les t\xe9n\xe8bres.
$$$Key1/lumi\xe8re
Second key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la
lumi\xe8re d'avec les t\xe9n\xe8bres."""
all_entries = [
	("$$$Key1",
	"""First key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la
lumi\xe8re d'avec les t\xe9n\xe8bres.
"""),

	("$$$Key1/lumi\xe8re",
	"""Second key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la
lumi\xe8re d'avec les t\xe9n\xe8bres.
"""),
	
	("$$$Key2",
	"""This is actually a third key
"""),

	("TTTTTTTTTTTTTTTTTTTTTTTT",
	"""This is a test\n\n\nWith three newlines above
"""),

]
bible_entries = [
	("Genesis 1:1",
	"""Time:long long ago
I'n the beginning God cree-ated the heavens and the 1,2345 earth."""),
	("Genesis 5:3",
	"""Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la
lumi\xe8re d'avec les t\xe9n\xe8bres."""),
]

stress_test = [
	("Key %d" % i, "This is key number '%d'" % i) for i in range(100000)
]

items = dict(
	genbook=(
		"modules/%(modulename)s",
		"/%(modulename)s",
		SW.RawGenBook,
		SW.Key,
		"""\
[%(modulename)s]
DataPath=./modules/%(modulename)s/%(modulename)s
Description=A test of %(modulename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawGenBook
""", 
		all_entries
	),
	genbook_displaylevel=(
		"modules/%(modulename)s",
		"/%(modulename)s",
		SW.RawGenBook,
		SW.Key,
		"""\
[%(modulename)s]
DataPath=./modules/%(modulename)s/%(modulename)s
Description=A test of %(modulename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawGenBook
DisplayLevel=2
""", 
		all_entries
	),
	
	dictionary=(
		"modules/%(modulename)s",
		"/%(modulename)s",
		SW.RawLD,
		SW.Key,
		"""\
[%(modulename)s]
DataPath=./modules/%(modulename)s/%(modulename)s
Description=A test of %(modulename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawLD
""", 
		all_entries
	),
	bible=(
		"modules/%(modulename)s",
		"",
		SW.RawText,
		SW.VerseKey,
		"""\
[%(modulename)s]
DataPath=./modules/%(modulename)s
Description=A test of %(modulename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawText
""", 
		bible_entries
	),
	
)

import sys

do_stresstest = "stresstest" in sys.argv
if do_stresstest:
	items["dictionary_stress_test"]=(
		"modules/%(modulename)s",
		"/%(modulename)s",
		SW.RawLD4,
		SW.Key,
		"""\
[%(modulename)s]
DataPath=./modules/%(modulename)s/%(modulename)s
Description=A stress test with 100,000 entries
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawLD4
""", 
		stress_test
	)
	


if not os.path.exists("mods.d"):
	os.mkdir("mods.d")

for item, (mod_dir, mod_extra, driver, key_type, conf, entries) in items.items():
	print item

	for encoding, sword_encoding in encodings.items():
		modulename = "%s%stest" % (encoding, item)
		print encoding, item
		print modulename
		module_dir = mod_dir % locals()
		module_extra = mod_extra % locals()
		#f = open(filename + ".imp", "w")
		#f.write(text.decode("cp1252").encode(encoding))
		#f.close()
		
		f2 = open("mods.d/%s.conf" % modulename, "w")
		f2.write((conf % locals()).decode("cp1252").encode(encoding))
		f2.close()
		
		if os.path.exists(module_dir):
			# empty directory
			for dir_item in os.listdir(module_dir):
				try:
					os.remove(module_dir + "/" + dir_item)
				except OSError, e:
					print "ERROR", e
			pass
		else:
			os.makedirs(module_dir)

		print module_dir + module_extra		
		result = driver.createModule(module_dir + module_extra) 
		assert result == '\x00', \
			"Failed creating module"

		
		module = driver(module_dir + module_extra)
		assert module.isWritable(), "MODULE MUST BE WRITABLE"

		for key, value in entries:
			value = value.decode("cp1252").encode(encoding)
			key = key.decode("cp1252").encode(encoding)

			print "KEY", key
			module.setKey(key_type(key))
			
			module.setEntry(value, len(value))

		#assert not os.system(importer % locals()), "%s failed" % (
		#	importer % locals())

modulename = "linked_verse_test"
module_dir = "modules/%(modulename)s" % locals()
driver = SW.RawText
key_type = SW.VerseKey
keys = ("Genesis 3:1 - 3", "Genesis 3:4 - 6", "Genesis 3:7 - 15", "Gen 3:16 - 20")

conf = """\
[%(modulename)s]
DataPath=./modules/%(modulename)s
Description=A test of %(modulename)s with linked verses.  See Genesis 3.
SourceType=Plaintext
ModDrv=RawText
""" % locals()
#f = open(filename + ".imp", "w")
#f.write(text.decode("cp1252").encode(encoding))
#f.close()

f2 = open("mods.d/%s.conf" % modulename, "w")
f2.write(conf % locals())
f2.close()

if os.path.exists(module_dir):
	# empty directory
	for dir_item in os.listdir(module_dir):
		try:
			os.remove(module_dir + "/" + dir_item)
		except OSError, e:
			print "ERROR", e
	pass
else:
	os.makedirs(module_dir)

print module_dir		
result = driver.createModule(module_dir)
assert result == '\x00', \
	"Failed creating module"

		
module = driver(module_dir)
assert module.isWritable(), "MODULE MUST BE WRITABLE"


for key in keys:
	from swlib.pysw import VerseList
	key = VerseList(key)[0]
	lower_bound = key.LowerBound().getText()
	key_text = "This is %s." % key.getRangeText()
	module.setKey(SW.VerseKey(lower_bound))
	module.setEntry(key_text)
	for linked_key in [key_.getText() for key_ in key][1:]:
		module.setKey(SW.VerseKey(linked_key))
		module.linkEntry(SW.VerseKey(lower_bound))

conf_file = items["bible"][4]

f = open("mods.d/test_bad.conf", "w")
f.write(conf_file + "\ntest")
f.close()

zip = zipfile.ZipFile("test_bad.zip", "w")
zip.write("mods.d/test_bad.conf")
zip.close()

zip = zipfile.ZipFile("test.zip", "w")
zip.write("mods.d/utf8bibletest.conf")
zip.close()
