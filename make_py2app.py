"""
Make a Mac .app folder. Requires py2app, and XULRunner 1.9.2.x installed.

Usage:
    python make_py2app.py -A --use-pythonpath (for development)
    python make_py2app.py (for standalone)
"""
import os
from util.i18n import find_languages
import contrib
import sys

from setuptools import setup

APP = ['bpbible.py']
DATA_FILES = []#"locales", "graphics"]
OPTIONS = {
	'argv_emulation': True, 
	'iconfile': 'graphics/bpbible.icns',
}

if "py2app" not in sys.argv:
	print sys.argv
	sys.argv.insert(1, "py2app")

languages = find_languages(is_release=True)
def sh(x):
	print x
	assert os.system(x) == 0

if setup(
    app=APP,
	name="BPBible",
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
):
	if "-A" not in sys.argv:
		subdirs = r"xrc graphics css js xulrunner resources locales locales/locales.d locales/locales.d/SWORD_1512".split()
		subdirs += ["locales/%s/LC_MESSAGES/" % l for l in languages]
		for subdir in subdirs:
			sh(r"mkdir -p dist/bpbible.app/Contents/Resources/%s" % subdir)

		sh("cp xrc/*.xrc dist/bpbible.app/Contents/Resources/xrc")
		for item in "png gif".split():
			sh("cp graphics/*.%s dist/bpbible.app/Contents/Resources/graphics" % item)
		
		sh("cp LICENSE.txt dist/bpbible.app/Contents/Resources")
		sh(r"cp locales/locales.d/*.conf dist/bpbible.app/Contents/Resources/locales/locales.d")
		sh(r"cp locales/locales.d/SWORD_1512/*.conf dist/bpbible.app/Contents/Resources/locales/locales.d/SWORD_1512")	
		sh(r"rm -rf dist/bpbible.app/Contents/Resources/resources")
		sh(r"rm -rf dist/bpbible.app/Contents/Resources/css")
		sh(r"rm -rf dist/bpbible.app/Contents/Resources/js")
		sh(r"cp -r resources dist/bpbible.app/Contents/Resources/resources")	
		sh(r"cp -r css dist/bpbible.app/Contents/Resources/css")
		sh(r"cp -r js dist/bpbible.app/Contents/Resources/js")

	sh(r"cp -r /Library/Frameworks/XUL.framework/Versions/Current/* dist/bpbible.app/Contents/MacOS")
