import os
import sys
import shutil
import re

python_i18n_paths = [
	"~/Python-2.5.2",
	r"\Python25",
]

for item in python_i18n_paths:
	tools_path = os.path.expanduser(item) + "/Tools"
	if os.path.isdir(tools_path):
		python_i18n_path = tools_path + "/i18n"
		break
else:
	raise SystemExit("Couldn't find path to Tools directory")

def gather(force=False):
#	for item in languages:
#		if os.path.exists("locales/%s.po"):
			
	old_text = open("locales/messages.pot").read()
	old_text = re.sub('"POT-Creation-Date: .*"', "", old_text)
	
	error = os.system('python %s/pygettext.py -o messages.pot.new -p locales/ -k N_ `find . -name "*.py"`' % python_i18n_path)
	assert not error, error
	new_text = open("locales/messages.pot.new").read()
	new_text = re.sub('"POT-Creation-Date: .*"', "", new_text)
	if new_text == old_text:
		os.remove("locales/messages.pot.new")
		print "Nothing to do"
		if not force:
			return
	else:
		shutil.move("locales/messages.pot.new", "locales/messages.pot")
	
	f = open("locales/messages.pot").read()
		
	# change .\backend\book.py -> backend/book.py
	f = re.sub(r"#: (\.\\.*)", 
		lambda s:
			re.sub(
			r"\.\\([^ ]*)", 
			lambda z: z.group().replace("\\", "/"), 
			s.group()
		),
		f
	)
	open("locales/messages.pot", "w").write(f)		


	for item in languages:
		if not os.path.exists("locales/%s.po" % item):
			print "Language not existing", item
			print "Creating"
			text = open("locales/messages.pot").read()
			text = text.replace("Content-Type: text/plain; charset=CHARSET",
								"Content-Type: text/plain; charset=utf-8")
			text = text.replace("Content-Transfer-Encoding: ENCODING",
								"Content-Transfer-Encoding: utf-8")
			f = open("locales/%s.po" % item, "w")
			f.write(text)
			f.close()



		err = os.system(
			"msgmerge -D locales/ %s.po messages.pot -o locales/%s.po.new" % (				item, item
		))

		assert not err, err
		
		check("locales/%s.po.new" % item)
		

def compile():
	for item in languages:
		check("locales/%s.po" % item)
		if not os.path.isdir("locales/%s/LC_MESSAGES" % item):
			os.makedirs("locales/%s/LC_MESSAGES" % item)
		err = os.system("python %s/msgfmt.py -o locales/%s/LC_MESSAGES/messages.mo locales/%s.po" % (python_i18n_path, item, item))
		assert not err, err

def confirm():
	for item in languages:
		if os.path.exists("locales/%s.po.new" % item):
			shutil.move("locales/%s.po.new"%item, "locales/%s.po"%item)

def check(file):
	print "checking", file
	check_fuzzies(file)
	check_deletions(file)

def check_fuzzies(file):
	text = open(file).read()
	fuzzies = len(list(re.finditer("^#, fuzzy$", text, re.M)))
	if fuzzies: 
		print "WARNING: %d fuzzies" % fuzzies

def check_deletions(file):
	text = open(file).read()
	fuzzies = len(list(re.finditer("^#~ msgid", text, re.M)))
	if fuzzies:
		print "WARNING: %d deletions" % fuzzies

def diff():
	for item in languages:
		if os.path.exists("locales/%s.po.new" % item):
			print "Language:", item
			err = os.system("python %s/Scripts/diff.py -u locales/%s.po locales/%s.po.new" % (tools_path, item, item))
			assert not err, err

import util.i18n
languages = [language for language in util.i18n.languages]
#["en", "ne", "abc", "es"]
if __name__ == '__main__':
	if "gather" in sys.argv:
		gather("force" in sys.argv)

	elif "confirm" in sys.argv:
		confirm()

	elif "compile" in sys.argv:
		compile()
	elif "diff" in sys.argv:
		diff()
	else:
		raise SystemExit("Try one of gather, confirm, diff or compile")
