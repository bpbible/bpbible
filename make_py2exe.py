from distutils.core import setup
import py2exe
import os
import re
import sys
import contrib
import config
from util.i18n import find_languages

version = sys.argv[-1]
if re.findall("^([0-9]+\.)*[0-9]+$", version):
	del sys.argv[-1]
else:
	version = "None"

if "py2exe" not in sys.argv:
	sys.argv.append('py2exe')

manifest = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>BPBible - Flexible Bible Study</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
"""

#os.system("del /s *.pyc")
#os.system("del /s *.xcfg")
#os.system("del /s *.*~")


if "compressed" in sys.argv:
	options = {"py2exe": {"compressed": 1,
						  "optimize": 1,
						  "bundle_files": 1
			  }}
	sys.argv.remove("compressed")
	zipfile=None
else:
	options = {"py2exe": {"optimize": 1}}
	zipfile="library.zip"

languages = find_languages(is_release=True)
if(setup(
	options = options,
	
	windows = [
		{
			"script":('bpbible.py'),#,'mainfrm.xrc','search.xrc'),
			"icon_resources":[(1, "graphics/bpbible.ico")],
			"other_resources": [(24,1,manifest)],
			"description": "BPBible - Flexible Bible Study",
			"version": version,
			"name": "BPBible",
		}
	],
	zipfile=zipfile,
)):
	import os
	subdirs = r"xrc graphics harmony resources locales locales\locales.d locales\locales.d\SWORD_1512".split()
	subdirs += ["locales\%s\LC_MESSAGES\\" % l for l in languages]
	for subdir in subdirs:
		os.system(r"if not exist dist\%s mkdir dist\%s" % (subdir, subdir))

	os.system("copy xrc\\*.xrc dist\\xrc\\")
	for item in "png gif".split():
		os.system("copy graphics\\*.%s dist\\graphics\\" % item)
	
	os.system("copy harmony\\robertson.harm dist\\harmony")
	os.system("copy harmony\\compositeGospel.1.3.xml.harm dist\\harmony")
	os.system("copy LICENSE.txt dist\\")
	os.system(r"copy locales\locales.d\*.conf dist\locales\locales.d")
	os.system(r"copy locales\locales.d\SWORD_1512\*.conf dist\locales\locales.d\SWORD_1512")	
	os.system(r"xcopy /e resources dist\resources")	

	for item in languages:
		os.system("copy locales\%s\LC_MESSAGES\messages.mo "
		"dist\locales\%s\LC_MESSAGES\messages.mo" % (item, item))
		os.system("copy locales\%s\locale.conf dist\locales\%s\locale.conf" % (item, item))
