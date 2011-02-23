import csv
import cStringIO
from collections import defaultdict
import hashlib

def djb2hash(hashstring):
	hashvalue = 5381
	for i in range(len(hashstring)):
		ascii_code = ord(hashstring[i])
		hashvalue = ((hashvalue << 5) + hashvalue) + ascii_code

	return hashvalue;

def compute_colour(item, 
	alpha=1, 
	lum_range=range(30, 45), 
	sat_range=range(50, 100)):
	if item == "God" or item == "Lord":
		return "hsla(287, 100%%, 60%%, %s)" % alpha #8B00B2"
	
	if item == "Jesus":
		return "hsla(360, 100%%, 70%%, %s)" % alpha

	# Compute a hash of the hostname, 
	# and clamp it to the 0-360 range allowed for the hue.
	hue = djb2hash(item) % 360 + 60
	sat = 100 #CHROMATABS._prefs.getIntPref("color.saturation");
	lum = 40 #CHROMATABS._prefs.getIntPref("color.luminance");
	lum = lum_range[(djb2hash(item) + 5) % len(lum_range)]
	sat = sat_range[djb2hash(item) % len(sat_range)]
	

	# Make the color string. eg: hsl(180, 100%, 40%)
	color = "hsla(%d, %d%%, %d%%, %s)" % (hue, sat, lum, alpha)

	return color

def compute_colour2(item):
	return "#" + hashlib.md5(item).hexdigest()[:6]

def compute_colour3(item):
	m = hashlib.sha1(item)
	items = map(ord, m.digest())
	r, g, b = items.pop(), items.pop(), items.pop()
	rgb_sum = sum((r,g,b))
	if rgb_sum < 150:
		r += 25
		g += 25
		b += 25
	
	if rgb_sum > 500:
		r -= 25
		g -= 25
		b -= 25
	
	return "hsl(%d, %d%%, %d%%)" % (r, g / 2.55, b/2.55)

colour_functions = compute_colour, compute_colour2#, compute_colour3

def read_quotes():
	file = open(r"resources/esv_quotes.txt")
	
	f = iter(file)
	f.next()
	reader = csv.DictReader(f)
	names = defaultdict(int)
	
	#css = open("colourize.out.css", "w")
	css1 = cStringIO.StringIO()
	
	#print >> css, '.quote[qid$="1"] {border-bottom: green;}'
	print >> css1, '.quote[qid] {border-bottom: red;}'
	quote_mapping = {}
	
	s = set()
	stack = []
	for item in reader:
		name = item["Who (Normalized)"]
		names[name] += 1
		qID = item["Quote ID"].replace(".", "_")
		eID = item["End ID"].replace(".", "_")
		quote_mapping[qID] = name
		
		# inner
		while stack and qID > stack[-1][1]:
			stack.pop()
		
		n = name[1:] if name.startswith("@") else name
		if name != "NULL":
			stack.append((qID, eID, compute_colour(n, alpha=1 if n==name else 0.9,
				sat_range=range(100, 101), lum_range=range(70, 71)
			), name))
	
			# TODO: we can optimize this by adding/removing stylesheet, rather
			# than putting conditionals in rules
			s.add('body[colour_speakers="coloured_quotes"] .chapterview %s {border-bottom: %dpx solid; -moz-border-bottom-colors: %s}' % (
				' > '.join('.quote[who="%s"]' % n for q, e, c, n in stack),
				len(stack) * 2,
				' '.join(c + " " + c for q, e, c, n in reversed(stack))
				))
	
	for i in s:
		print >> css1, i

	return css1.getvalue(), quote_mapping

quotes = None
def get_quotes():
	global quotes
	if quotes is None:
		quotes = read_quotes()
	
	#open("quotes.css", "w").write(quotes[0])
	return quotes

