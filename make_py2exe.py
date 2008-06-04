from distutils.core import setup
import py2exe
import os
import sys

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


if(setup(
    options = {"py2exe": #{"compressed": 1,
                          {"optimize": 1,
              #            "bundle_files": 1}
			  }},
	
	windows = [
		{
			"script":('bpbible.py'),#,'mainfrm.xrc','search.xrc'),
			"icon_resources":[(1, "graphics/bpbible.ico")],
            "other_resources": [(24,1,manifest)],
			"description": "BPBible - Flexible Bible Study",
        	"version": "0.3",
        	"name": "BPBible",
		}
	],
	#zipfile=None,
)):
	import os
	subdirs = r"xrc graphics harmony resources resources\locales.d".split()
	for subdir in subdirs:
		os.system(r"if not exist dist\%s mkdir dist\%s" % (subdir, subdir))

	os.system("copy xrc\\*.xrc dist\\xrc\\")
	for item in "png xpm svg gif".split():
		os.system("copy graphics\\*.%s dist\\graphics\\" % item)
	
	os.system("copy harmony\\robertson.harm dist\\harmony")
	os.system("copy harmony\\compositeGospel.1.3.xml.harm dist\\harmony")
	os.system("copy LICENSE.txt dist\\")
	os.system(r"copy resources\locales.d\bpbible.conf dist\resources\locales.d")
