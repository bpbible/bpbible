import os
import sys
import shutil
import re

def system(path):
	err = os.system(path)
	if err:
		raise Exception("Running %r gave return error %s" % (path, err))

python_i18n_paths = [
	"~/Python-2.5.2",
	r"\Python25",
	r"C:\Python25",
]

ignore_strings = [
	r'"<h5>$$heading</h5>"',
	r'''""
"\n"
"$$range ($$version)"''',
	r'"$$text "',
	'"DUMMY"'
]
for item in python_i18n_paths:
	tools_path = os.path.expanduser(item) + "/Tools"
	if os.path.isdir(tools_path):
		python_i18n_path = tools_path + "/i18n"
		break
else:
	raise Exception("Couldn't find path to Tools directory")

def convert_slashes(text):
	return re.sub(r"#: (\.[\\/].*)", 
		lambda s:
			re.sub(
			r"\.[\\/]([^ ]*)", 
			lambda z: z.group(1).replace("\\", "/"), 
			s.group()
		),
		text
	)

def gather(force=True):
#	for item in languages:
#		if os.path.exists("locales/%s.po"):
			
	old_text = open("locales/messages.pot").read()
	old_text = re.sub('"POT-Creation-Date: .*"', "", old_text)
	
	system('python %s/pygettext.py -o messages.pot.new -p locales/ -k N_ `find . -name "*.py"`' % python_i18n_path)

	new_text = open("locales/messages.pot.new").read()
	# ignore certain strings. Would use -x on pygettext.py, but it doesn't
	# work!
	for item in ignore_strings:
		r = '''\
#: .*
msgid %s
msgstr ""

''' % re.escape(item)
		new_text, cnt = re.subn(r, "", new_text)
		assert cnt, `r`

	open("locales/messages.pot.new", "w").write(new_text)
	new_text = re.sub('"POT-Creation-Date: .*"', "", new_text)


	if convert_slashes(new_text) == convert_slashes(old_text) and False:
		os.remove("locales/messages.pot.new")
		print "Nothing to do"
		if not force:
			return
	else:
		shutil.move("locales/messages.pot.new", "locales/messages.pot")
	
	f = open("locales/messages.pot").read()
		
	f = convert_slashes(f)
	# change .\backend\book.py -> backend/book.py
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



		err = system(
			"msgmerge -D locales/ %s.po messages.pot -o locales/%s.po.new" % (				item, item
		))
		
		check("locales/%s.po.new" % item)
		

def compile():
	for item in languages:
		check("locales/%s.po" % item)
		if not os.path.isdir("locales/%s/LC_MESSAGES" % item):
			os.makedirs("locales/%s/LC_MESSAGES" % item)
		err = system("python %s/msgfmt.py -o locales/%s/LC_MESSAGES/messages.mo locales/%s.po" % (python_i18n_path, item, item))

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
			err = system("python %s/scripts/diff.py -u locales/%s.po locales/%s.po.new" % (tools_path, item, item))

import util.i18n
languages = [language for language in util.i18n.languages]
#["en", "ne", "abc", "es"]

def main(args):
	if "gather" in args:
		gather("force" in args)

	elif "confirm" in args:
		confirm()

	elif "compile" in args:
		compile()
	elif "diff" in args:
		diff()
	else:
		raise Exception("Try one of gather, confirm, diff or compile")

if __name__ == '__main__':
	main(sys.argv[1:])
