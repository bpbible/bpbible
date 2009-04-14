import re
DEFAULTSECT = "DEFAULT"


# exception classes
class Error(Exception):
	"""Base class for ConfigParser exceptions."""

	def __init__(self, msg=''):
		self.message = msg
		Exception.__init__(self, msg)

	def __repr__(self):
		return self.message

	__str__ = __repr__

class NoSectionError(Error):
	"""Raised when no section matches a requested option."""

	def __init__(self, section):
		Error.__init__(self, 'No section: %r' % (section,))
		self.section = section

class DuplicateSectionError(Error):
	"""Raised when a section is multiply-created."""

	def __init__(self, section):
		Error.__init__(self, "Section %r already exists" % section)
		self.section = section

class NoOptionError(Error):
	"""A requested option was not found."""

	def __init__(self, option, section):
		Error.__init__(self, "No option %r in section: %r" %
					   (option, section))
		self.option = option
		self.section = section

class ParsingError(Error):
	"""Raised when a configuration file does not follow legal syntax."""

	def __init__(self, filename):
		Error.__init__(self, 'File contains parsing errors: %s' % filename)
		self.filename = filename
		self.errors = []

	def append(self, lineno, line):
		self.errors.append((lineno, line))
		self.message += '\n\t[line %2d]: %s' % (lineno, line)

class MissingSectionHeaderError(ParsingError):
	"""Raised when a key-value pair is found before any section header."""

	def __init__(self, filename, lineno, line):
		Error.__init__(
			self,
			'File contains no section headers.\nfile: %s, line: %d\n%r' %
			(filename, lineno, line))
		self.filename = filename
		self.lineno = lineno
		self.line = line

		


class config(object):
	SECTCRE = re.compile(
		r'\['								 # [
		r'(?P<header>[^]]+)'				 # very permissive!
		r'\]'								 # ]
		)
	OPTCRE = re.compile(
		r'(?P<option>[^:=\s][^:=]*)'		 # very permissive!
		r'\s*(?P<vi>[:=])\s*'				 # any number of space/tab,
											 # followed by separator
											 # (either : or =), followed
											 # by any # space/tab
		r'(?P<value>.*)$'					 # everything up to eol
		)
	def __init__(self, defaults=None):
		self._sections = {}
		self._defaults = {}
		if defaults:
			for key, value in defaults.items():
				self._defaults[self.optionxform(key)] = value

	def optionxform(self, optionstr):
		return optionstr#.lower()
				
		

	def _read(self, fp, fpname):
		"""Parse a sectioned setup file.

		The sections in setup file contains a title line at the top,
		indicated by a name in square brackets (`[]'), plus key/value
		options lines, indicated by `name: value' format lines.
		Continuations are represented by an embedded newline then
		leading whitespace.  Blank lines, lines beginning with a '#',
		and just about everything else are ignored.

		BM: made this work with multiple items for an option
		BM: line continuation with \ working
		"""
		cursect = None							# None, or a dictionary
		optname = None
		lineno = 0
		e = None								  # None, or an exception
		was_continuation = False
		is_continuation = False
		
		while True:
			was_continuation = is_continuation
			line = fp.readline()

			# if we are at the first line, strip it of the BOM if it has it
			# TODO: test this!!!
			if lineno == 0 and line.startswith('\xef\xbb\xbf'):
				line = line[3:]

			if not line:
				break
			lineno = lineno + 1
			# comment or blank line?
			if line.strip() == '' or line[0] in '#;':
				continue
			if line.split(None, 1)[0].lower() == 'rem' and line[0] in "rR":
				# no leading whitespace
				continue
			if line.endswith("\\\n"):
				is_continuation = True
				# chop off the continuation character
				line = line[:-2] + "\n"
			else:
				is_continuation = False

			# continuation line?
			if(line[0].isspace() and cursect is not None and optname) or (
				was_continuation
			):
				value = line.strip()
				if value:
					cursect[optname][-1] = "%s\n%s" % \
						(cursect[optname][-1], value)
			# a section header or option header?
			else:
				# is it a section header?
				mo = self.SECTCRE.match(line)
				if mo:
					sectname = mo.group('header')
					if sectname in self._sections:
						cursect = self._sections[sectname]
					elif sectname == DEFAULTSECT:
						cursect = self._defaults
					else:
						cursect = {'__name__': sectname}
						self._sections[sectname] = cursect
					# So sections can't start with a continuation line
					optname = None
				# no section header in the file?
				elif cursect is None:
					raise MissingSectionHeaderError(fpname, lineno, line)
				# an option line?
				else:
					mo = self.OPTCRE.match(line)
					if mo:
						optname, vi, optval = mo.group('option', 'vi', 'value')
						if vi in ('=', ':') and ';' in optval:
							# ';' is a comment delimiter only if it follows
							# a spacing character
							pos = optval.find(';')
							if pos != -1 and optval[pos-1].isspace():
								optval = optval[:pos]
						optval = optval.strip()
						# allow empty values
						if optval == '""':
							optval = ''
						optname = self.optionxform(optname.rstrip())
						cursect.setdefault(optname, []).append(optval)
					else:
						# a non-fatal parsing error occurred.  set up the
						# exception but keep going. the exception will be
						# raised at the end of the file and will contain a
						# list of all bogus lines
						if not e:
							e = ParsingError(fpname)
						e.append(lineno, repr(line))
		if e:
			raise e

	def read(self, filenames):
		"""Read and parse a filename or a list of filenames.

		Files that cannot be opened are silently ignored; this is
		designed so that you can specify a list of potential
		configuration file locations (e.g. current directory, user's
		home directory, systemwide directory), and all existing
		configuration files in the list will be read.  A single
		filename may also be given.

		Return list of successfully read files.
		"""
		if isinstance(filenames, basestring):
			filenames = [filenames]
		read_ok = []
		for filename in filenames:
			try:
				fp = open(filename)
			except IOError:
				continue
			self._read(fp, filename)
			fp.close()
			read_ok.append(filename)
		return read_ok

	def get(self, section, option):
		opt = self.optionxform(option)
		if section not in self._sections:
			if section != DEFAULTSECT:
				raise NoSectionError(section)
			if opt in self._defaults:
				return self._defaults[opt]
			else:
				raise NoOptionError(option, section)
		elif opt in self._sections[section]:
			return self._sections[section][opt]
		elif opt in self._defaults:
			return self._defaults[opt]
		else:
			raise NoOptionError(option, section)

	def defaults(self):
		return self._defaults

	def sections(self):
		"""Return a list of section names, excluding [DEFAULT]"""
		# self._sections will never have [DEFAULT] in it
		return self._sections.keys()

	def add_section(self, section):
		"""Create a new section in the configuration.

		Raise DuplicateSectionError if a section by the specified name
		already exists.
		"""
		if section in self._sections:
			raise DuplicateSectionError(section)
		self._sections[section] = {}

	def has_section(self, section):
		"""Indicate whether the named section is present in the configuration.

		The DEFAULT section is not acknowledged.
		"""
		return section in self._sections

	def options(self, section):
		"""Return a list of option names for the given section name."""
		try:
			opts = self._sections[section].copy()
		except KeyError:
			raise NoSectionError(section)
		opts.update(self._defaults)
		if '__name__' in opts:
			del opts['__name__']
		return opts.keys()

	def has_option(self, section, option):
		"""Check for the existence of a given option in a given section."""
		if not section or section == DEFAULTSECT:
			option = self.optionxform(option)
			return option in self._defaults
		elif section not in self._sections:
			return False
		else:
			option = self.optionxform(option)
			return (option in self._sections[section]
					or option in self._defaults)

	def write(self, fp):
		"""Write an .ini-format representation of the configuration state.
		
		BM: updated to write out multiple values for a given option
		BM: removed spaces from output"""
		if self._defaults:
			fp.write("[%s]\n" % DEFAULTSECT)
			for (key, values) in self._defaults.items():			
				for value in values:
					fp.write("%s=%s\n" % (key, str(value).replace('\n', '\n\t')))
			fp.write("\n")
		for section in self._sections:
			fp.write("[%s]\n" % section)
			for (key, values) in self._sections[section].items():
				for value in values:
					if key != "__name__":
						fp.write("%s=%s\n" %
							 (key, str(value).replace('\n', '\n\t')))
			fp.write("\n")
	
	def set(self, section, option, value):
		"""Set an option.
		
		BM: clears the list and puts this in as first in list"""
		if not section or section == DEFAULTSECT:
			sectdict = self._defaults
		else:
			try:
				sectdict = self._sections[section]
			except KeyError:
				raise NoSectionError(section)
		sectdict[self.optionxform(option)] = [value]
			

	def remove_option(self, section, option):
		"""Remove an option."""
		if not section or section == DEFAULTSECT:
			sectdict = self._defaults
		else:
			try:
				sectdict = self._sections[section]
			except KeyError:
				raise NoSectionError(section)
		option = self.optionxform(option)
		existed = option in sectdict
		if existed:
			del sectdict[option]
		return existed

	def remove_section(self, section):
		"""Remove a file section."""
		existed = section in self._sections
		if existed:
			del self._sections[section]
		return existed

