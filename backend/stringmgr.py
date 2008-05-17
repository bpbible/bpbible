from swlib.pysw import SW
class MyStringMgr(SW.PyStringMgr):
	def getUpper(self, buf):
		# TODO: a more advanced heuristic like bibletime's to check whether it
		# is utf8 or latin1
		encodings = "UTF-8", "cp1252"
		text = buf.c_str()
		#print `text`
		for enc in encodings:
			try:
				# do an uppercase on the unicode object, then re-encode it 
				# back to how it was.
				# then set the buffer to the new string
				buf.set(text.decode(enc).upper().encode(enc))
				return

			except UnicodeDecodeError:
				pass

		dprint(WARNING, "Couldn't convert text to uppercase", text)
		return

	def supportsUnicode(self):
		return True
		
m=MyStringMgr()

# we don't own this, the system string mgr holder does
m.thisown = False
SW.StringMgr.setSystemStringMgr(m)
