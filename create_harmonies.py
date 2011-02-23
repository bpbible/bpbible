import glob
import os
from swlib.pysw import SW
from backend.create_module import ModuleCreator
from harmony import read_harmony

def main():
	for filename in glob.glob(r"harmony/*.harm"):
		create_harmony_genbook(read_harmony.process_harmony(filename), os.path.basename(filename)[:-5])

def create_harmony_genbook(harmony, shortname):
	print "Processing", shortname
	if not harmony.loaded:
		harmony.load()

	harmony_creator = ModuleCreator(shortname, SW.RawGenBook, SW.Key,
		duplicates=True,
		extra_attrs={
			"SourceType": "OSIS",
			"Lang": "en",
			"Version": "0.1",
			"Description": harmony.name,
			"About": "A gospel harmony.",
			"LCSH": "Bible--Harmonies.",
			"DistributionLicense": "XXX: FixME.  Public Domain",
			"Category": "Gospel Harmonies",
		})
	for child in harmony.top.children:
		process_entry(harmony_creator, child, parent_key="")

def process_entry(harmony_creator, child, parent_key):
	key = u"%s/%s" % (parent_key, child.name)
	print u"Processing entry with key", key
	if not child.visible:
		text = u""
	else:
		text = u""
		references = []
		assert len(child.references) == 1
		for reference in child.references[0]:
			references.append(reference.GetBestRange())
		text = (u"<harmonytable refs=\"%s\"></harmonytable>" %
			"|".join(references))
	harmony_creator.add_entry(key, text)
	
	for item in child.children:
		process_entry(harmony_creator, item, key)

if __name__ == "__main__":
	main()
