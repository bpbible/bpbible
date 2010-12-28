from distutils.core import setup
import py2exe
import os
import re
import sys
import contrib
import config
import glob
from util.i18n import find_languages

version = sys.argv[-1]
if re.findall("^([0-9]+\.)*[0-9]+(b[0-9]+)?$", version):
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
<dependency>
  <dependentAssembly>
    <assemblyIdentity
      type="win32"
      name="Microsoft.VC90.CRT"
      version="9.0.21022.8"
      processorArchitecture="x86"
      publicKeyToken="1fc8b3b9a1e18e3b"
    />
  </dependentAssembly>
</dependency>
</assembly>
"""

#os.system("del /s *.pyc")
#os.system("del /s *.xcfg")
#os.system("del /s *.*~")

py2exe_options = {
	"optimize": 1,
	"dll_excludes": "msvcp90.dll"
}

zipfile = "library.zip"
if "compressed" in sys.argv:
	py2exe_options.update({
		"compressed": 1,
		"bundle_files": 1,
	})
	sys.argv.remove("compressed")
	zipfile = None

languages = find_languages(is_release=True)

data_files = []
# You will need to include this directory when building with Python 2.6.
# The manifest says that the directory will be there, since it depends on MSVC 9.
# You can get the directory from VC++ 2008 Express (read redist.txt).
if os.path.isdir('Microsoft.VC90.CRT'):
	vc_files = glob.glob('Microsoft.VC90.CRT\\*.*')
	data_files += [
			("Microsoft.VC90.CRT", vc_files),
	]

if(setup(
	options = {"py2exe": py2exe_options},
	data_files = data_files,
	
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
	subdirs = r"xrc graphics css js xulrunner resources locales locales\locales.d".split()
	subdirs += ["locales\%s\LC_MESSAGES\\" % l for l in languages]
	for subdir in subdirs:
		os.system(r"if not exist dist\%s mkdir dist\%s" % (subdir, subdir))

	os.system("copy xrc\\*.xrc dist\\xrc\\")
	for item in "png gif".split():
		os.system("copy graphics\\*.%s dist\\graphics\\" % item)
	
	os.system("copy LICENSE.txt dist\\")
	os.system(r"copy locales\locales.d\*.conf dist\locales\locales.d")
	os.system(r"xcopy /e /Y resources dist\resources")	
	os.system(r"xcopy /e /Y css dist\css")
	os.system(r"xcopy /e /Y js dist\js")
	os.system(r"xcopy /e /Y xulrunner dist\xulrunner")

	for item in languages:
		os.system("copy locales\%s\LC_MESSAGES\messages.mo "
		"dist\locales\%s\LC_MESSAGES\messages.mo" % (item, item))
		os.system("copy locales\%s\locale.conf dist\locales\%s\locale.conf" % (item, item))
