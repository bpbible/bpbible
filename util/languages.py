import csv

language_mapping = {}
country_mapping = {}

is_initialized = False
def get_language_description(code):
	if not is_initialized:
		initialize_iso_data()

	country = None
	parts = code.split("_")
	lang_code = parts[0]
	
	language = lookup_language_code(lang_code)
	if len(parts) > 1:
		country = lookup_country_code(parts[1])
		language = "%(language)s (%(country)s)" % locals()
	
	return language.decode("utf8")

def lookup_language_code(code):
	return language_mapping.get(code, "<Unknown language %s>" % code)

def lookup_country_code(code):
	return country_mapping.get(code, "<Unknown country %s>" % code)

def initialize_iso_data():
	global is_initialized
	iso639_3_data = open("resources/iso-639-3_Name_Index_20080902.tab", "rb")
	r = csv.reader(iso639_3_data, delimiter='\t')
	for id, print_name, inverted_name in r:
		# we use the inverted name as it sorts better and the iso639_1_2 data
		# uses it as well.
		if id in language_mapping:
			# sometimes we have one code for different items
			# ;  separate them for consistency with iso639_1_2 data
			language_mapping[id] += "; " + inverted_name
		else:
			language_mapping[id] = inverted_name
	
	# overwrite the above if necessary
	iso639_1_2_data = open("resources/iso-639-2.data", "rb")
	r = csv.reader(iso639_1_2_data, delimiter='\t')
	for row in r:
		three = row[0]
		two = row[1]
		language = row[2]
		if three:
			language_mapping[three] = language
		if two and two != " ":
			language_mapping[two] = language
	
	iso_3166_data = open("resources/iso_3166.data", "rb")
	r = csv.reader(iso_3166_data, delimiter='\t')
	for name, code in r:
		country_mapping[code] = name
	
	is_initialized = True
