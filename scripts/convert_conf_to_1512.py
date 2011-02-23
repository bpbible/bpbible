import sys
import Sword
import re
f = sys.argv[1]
t = open(f, "rU").read()
vk = Sword.VerseKey()
for a in reversed(range(0, 66)):
	t, g = re.subn("(?m)=%d[ \t]*$" % (a+1), "=%s" % vk.getOSISBookName(a), t)
	print g

open("SWORD_1512/%s" % f, "w").write(t)


