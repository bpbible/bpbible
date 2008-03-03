from distutils.core import setup
import py2exe
import os

os.system("del /s *.pyc")
os.system("del /s *.xcfg")
os.system("del /s *.*~")


if(setup(
	windows = [
		{
			"script":('bpbible.py'),#,'mainfrm.xrc','search.xrc'),
			"icon_resources":[(1, "graphics/Bible-48x48.ico")]
			
		}
	],
)):
	import os
	os.system("copy mainfrm.xrc build\mainfrm.xrc")
	os.system("copy search.xrc build\search.xrc")
