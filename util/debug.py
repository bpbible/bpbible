"""
debug.py - basic logging facilities
"""

import sys
import time

__all__ = ["MESSAGE", "WARNING", "ERROR", "dprint", "is_debugging", "TOOLTIP",
"INSTALL_ZIP"]
MESSAGE = 0
WARNING = 1
ERROR   = 2
TOOLTIP = 0.5
INSTALL_ZIP = 0.6

level = 0

def is_debugging():
	"""Are we debugging? 
	
	This is true if we are not in release mode or we have the -d flag.
	TODO: work out some better way to change "py2exe'd" to "released"
	"""
	import config
	return not config.is_release() or "-d" in sys.argv

def dprint(errorlevel, message, *args):
	if errorlevel >= level:	
		args = [message] + [repr(arg) for arg in args]
		print "%s %s" % (time.strftime("%H:%M:%S"), " ".join(args))
