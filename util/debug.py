"""
debug.py - basic logging facilities
"""

import time

__all__ = ["MESSAGE", "WARNING", "ERROR", "dprint", "DEBUGGING", "TOOLTIP"]
MESSAGE = 0
WARNING = 1
ERROR   = 2
TOOLTIP = 3

level = 0

DEBUGGING = (level == 0)

def dprint(errorlevel, message, *args):
	if errorlevel >= level:	
		args = [message] + [repr(arg) for arg in args]
		print "%s %s" % (time.strftime("%H:%M:%S"), " ".join(args))
