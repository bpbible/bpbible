# nstallMgr functions to be made into something usefully exposed by
# master Glassey

import os
import shutil
import tarfile
import Sword
from pyftptransport import PyFTPTransport
from swlib.installsource import InstallSource
from util.debug import dprint, WARNING, MESSAGE

try:
  WindowsError
except NameError:
  WindowsError = None


def copytree(src, dst, symlinks=False):
	# pinched from shutil.py
	"""Recursively copy a directory tree using copy2().

	#The destination directory must not already exist.
	If exception(s) occur, an Error is raised with a list of reasons.

	If the optional symlinks flag is true, symbolic links in the
	source tree result in symbolic links in the destination tree; if
	it is false, the contents of the files pointed to by symbolic
	links are copied.

	XXX Consider this example code rather than the ultimate tool.

	"""
	names = os.listdir(src)
	try:
		os.makedirs(dst)
	except os.error:
		pass

	errors = []
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				copytree(srcname, dstname, symlinks)
			else:
				shutil.copy2(srcname, dstname)
			# XXX What about devices, sockets etc.?
		except (IOError, os.error), why:
			errors.append((srcname, dstname, str(why)))
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except shutil.Error, err:
			errors.extend(err.args)
	try:
		shutil.copystat(src, dst)
	except OSError, why:
		if WindowsError is None or isinstance(why, WindowsError):
			# can't copy file access times on Windows
			pass
		else:
			errors.extend((src, dst, str(why)))
	if errors:
		raise shutil.Error, errors

class UnsafeUntarringException(Exception):
	pass

def untargz(filename, dest):
	tar = tarfile.open(filename, "r:gz")
	
	for item in tar:
		split_name = os.path.split(item.name)
		if ".." in split_name:
			raise UnsafeUntarringException(
"""Cannot extract the tar file, as it contains a reference to a parent
directory.
File in question is %s.
This may indicate someone is trying to exploit your system!""" % item.name)

	tar.extractall(dest)
	
def removeTrailingSlash(buf):
	if buf and buf[-1] in '\\/':
		buf = buf[:-1]
	
	return buf

def printf(arg, *args):
	print arg % args

class FileMgr(object):
	@staticmethod
	def createParent(path):
		dest_directory = os.path.dirname(path)
		if not os.path.exists(dest_directory):
			os.makedirs(dest_directory)
	
	
	@staticmethod
	def removeFile(file):
		os.remove(file)
	
	@staticmethod
	def removeDir(dir):
		if not os.path.exists(dir):
			return
	
		for item in os.listdir(dir):
			dprint(MESSAGE, "Encountered", item)
			path = dir + "/" + item
			if os.path.isdir(path):
				dprint(MESSAGE, "Removing directory")
				FileMgr.removeDir(path)
			else:
				dprint(MESSAGE, "removing", path)
				os.remove(path)

		# check whether this directory still exists, removedirs on its
		# children may have deleted it already
		if os.path.exists(dir):
			os.removedirs(dir)

	@staticmethod
	def copyFile(file, dest):
		dest_directory = os.path.dirname(dest)
		if not os.path.exists(dest_directory):
			os.makedirs(dest_directory)

		shutil.copy(file, dest)

	@staticmethod
	def copyDir(dir, dest_dir):
		copytree(dir, dest_dir)
	
	@staticmethod	
	def existsDir(dir):
		return os.path.exists(dir)

class InstallMgr(object):
	MODSTAT_OLDER			= 0x001
	MODSTAT_SAMEVERSION	  = 0x002
	MODSTAT_UPDATED		  = 0x004
	MODSTAT_NEW			  = 0x008
	MODSTAT_CIPHERED		 = 0x010
	MODSTAT_CIPHERKEYPRESENT = 0x020
	
	# override this method and provide your own custom FTPTransport subclass
	# here we try a couple defaults if sword was compiled with support for them.
	# see these classes for examples of how to make your own
	def createFTPTransport(self, host, statusReporter):
		return PyFTPTransport(host, statusReporter)

	def __init__(self, privatePath="./", sr=None):
		self.statusReporter = sr
		self.privatePath = privatePath
		self.transport = None
		self.passive = False
		self.term = False
		if self.privatePath:
			self.privatePath = removeTrailingSlash(self.privatePath)

		confPath = privatePath + "/InstallMgr.conf"
		FileMgr.createParent(confPath)
		
		installConf = Sword.SWConfig(confPath)

		#SectionMap::iterator sourcesSection;
		#ConfigEntMap::iterator sourceBegin;
		#ConfigEntMap::iterator sourceEnd;

		self.sources = {}
		
		self.setFTPPassive(
			installConf.get("General", "PassiveFTP") == "false"
		)

		sourcesSection = installConf.getSections().find(Sword.SWBuf("Sources"))
		if sourcesSection != installConf.getSections().end():
			ftp_source = Sword.SWBuf("FTPSource")
			ss = sourcesSection.value()[1]
			
			sourceBegin = ss.lower_bound(ftp_source)
			sourceEnd = ss.upper_bound(ftp_source)

			while sourceBegin != sourceEnd:
				install_source = InstallSource("FTP", 
					sourceBegin.value()[1].c_str())

				self.sources[install_source.caption] = install_source
				parent = privatePath + "/" + install_source.source + "/file"
				FileMgr.createParent(parent)
				install_source.localShadow = privatePath + "/" + install_source.source
				sourceBegin += 1

		self.defaultMods = set()
		sourcesSection = installConf.getSections().find(Sword.SWBuf("General"))
		general = sourcesSection.value()[1]
		
		if sourcesSection != installConf.getSections().end():
			default_mod = Sword.SWBuf("DefaultMod")
			sourceBegin = general.lower_bound(default_mod)
			sourceEnd = general.upper_bound(default_mod)

			while sourceBegin != sourceEnd:
				self.defaultMods.add(sourceBegin.value()[1].c_str())
				sourceBegin += 1


#def InstallMgr::~InstallMgr() {
#	delete [] privatePath;
#	delete installConf;
#
#	for (InstallSourceMap::iterator it = sources.begin(); it != sources.end(); ++it) {
#		delete it.value()[1];
#	}
#}


	def setFTPPassive(self, passive):
		self.passive = passive

	def terminate(self):
		if self.transport:
			self.transport.terminate()

	@staticmethod
	def removeModule(manager, moduleName):
		"""Physically deletes a module from the hard disk

		Returns True if module couldn't be found, False otherwise"""
		mod_name = Sword.SWBuf(moduleName)
		module = manager.config.getSections().find(mod_name)

		if (module != manager.config.getSections().end()):
			# to be sure all files are closed
			# this does not remove the .conf information from SWMgr
			manager.deleteModule(moduleName)
				
			file_buf = Sword.SWBuf("File")
			mod_second = module.value()[1]
			fileBegin = mod_second.lower_bound(file_buf)
			fileEnd = mod_second.upper_bound(file_buf)

			entry = mod_second.find(Sword.SWBuf("AbsoluteDataPath"))
			modDir = entry.value()[1].c_str()
			modDir = removeTrailingSlash(modDir)
			if fileBegin != fileEnd: 
				# remove each file
				while fileBegin != fileEnd:
					modFile = modDir
					modFile += "/"
					modFile += fileBegin.value()[1].c_str()

					# remove file
					FileMgr.removeFile(modFile.c_str())
					fileBegin += 1

			else: 	
				#remove all files in DataPath directory
				FileMgr.removeDir(modDir)
				
				# BM: this could be a bit ticklish...
				# I hope I have copied the correct behaviour

				# find and remove .conf file
				try:
					items = os.listdir(manager.configPath)
				except OSError:
					pass
				else:
					baseModFile = manager.configPath
					baseModFile = removeTrailingSlash(baseModFile)
					
					for item in items:
						modFile = baseModFile + "/"
						modFile += item
						config = Sword.SWConfig(modFile)
						if config.getSections().find(mod_name) != \
							config.getSections().end():
							del config
							FileMgr.removeFile(modFile)

			return False

		return True


	def ftpCopy(self, install_source, src, dest, dirTransfer=False, suffix=""):
		retVal = 0
		trans = self.createFTPTransport(
			install_source.source, 
			self.statusReporter
		)

		# set classwide current transport for other thread terminate() call
		self.transport = trans
		trans.setPassive(self.passive)
		
		urlPrefix = "ftp://" + install_source.source

		# let's be sure we can connect.  This seems to be necessary but sucks
#		SWBuf url = urlPrefix + install_source.directory.c_str() + "/"; //dont forget the final slash
#		if (trans.getURL("swdirlist.tmp", url.c_str())) {
#			 printf("FTPCopy: failed to get dir %s\n", url.c_str());
#			 return -1;
#		}

		   
		if dirTransfer:
			dir = install_source.directory
			dir = removeTrailingSlash(dir)
			dir += "/" + src #dont forget the final slash

			retVal = trans.copyDirectory(urlPrefix, dir, dest, suffix)

		else:
			try:
				url = urlPrefix + install_source.directory
				url = removeTrailingSlash(url)
				url += "/" + src #dont forget the final slash
				if trans.getURL(dest, url):
					printf(
						"FTPCopy: failed to get file %s", url)
					retVal = -1

			# TODO: A bare except block...
			except Exception, e:
				print "EXCEPTION", e
				retVal = -1
				raise

		#TODO: does this block make sense in python?
		try:
			deleteMe = trans
			# do this order for threadsafeness
			# (see terminate())
			trans = self.transport = None
			del deleteMe

		# TODO: A bare except block...
		except:
			pass

		return retVal


	def installModule(self, destMgr, fromLocation, modName, 
		install_source=None):
		"""Install a module from destMgr to a location

		Returns -1 on aborted, 0 on success and 1 on error
		"""

		aborted = False
		cipher = False

		print destMgr, fromLocation, modName, install_source
		#printf("***** InstallMgr::installModule\n")
		
		#if fromLocation:
		#	printf("***** fromLocation: %s \n", fromLocation)
		
		#printf("***** modName: %s \n", modName)
		
		if install_source:
			sourceDir = self.privatePath + "/" + install_source.source
		else:
			sourceDir = fromLocation;
		
		sourceDir = removeTrailingSlash(sourceDir)
		sourceDir += '/'
		
		# do this with False at the end to stop the augmenting
		mgr = Sword.SWMgr(sourceDir, True, None, False, False)
		
		module = mgr.config.getSections().find(Sword.SWBuf(modName))
		
		if module != mgr.config.getSections().end():
			mod_second = module.value()[1]
		
			entry = mod_second.find(Sword.SWBuf("CipherKey"))
			if entry != mod_second.end():
				cipher = True
			
			# This first check is a method to allow a module to specify each
			# file that needs to be copied
			file_buf = Sword.SWBuf("File")
			file_value = mod_second
			fileEnd = file_value.upper_bound(file_buf)
			fileBegin = file_value.lower_bound(file_buf)
			print fileEnd == fileBegin
		
			if (fileBegin != fileEnd):
				# copy each file
				if (install_source):
					while (fileBegin != fileEnd):
						swbuf = fileBegin.value()[1]
						src = swbuf.c_str()
						# ftp each file first
						buffer = sourceDir + src
						if self.ftpCopy(
							install_source, 
							src,
							buffer):
							
							aborted = True
							break	# user aborted

						fileBegin += 1

					fileBegin = mod_second.lower_bound(file_buf)
				
		
				if not aborted:
					# DO THE INSTALL
					while fileBegin != fileEnd:
						sourcePath = sourceDir
						sourcePath += fileBegin.value()[1].c_str()
						dest = destMgr.prefixPath
						dest = removeTrailingSlash(dest)
						dest += '/'
						dest += fileBegin.value()[1].c_str()
						FileMgr.copyFile(sourcePath, dest)
		
						fileBegin += 1
				
				# ---------------
		
				if install_source:
					fileBegin = mod_second.lower_bound(file_buf)
					while (fileBegin != fileEnd):
						# delete each tmp ftp file
						buffer = sourceDir + fileBegin.value()[1].c_str()
						FileMgr.removeFile(buffer.c_str())
						fileBegin += 1



		
			# This is the REAL install code, the above code I don't think has
			# ever been used
			#
			# Copy all files in DataPath directory
			# 
			else:
				
				entry = mod_second.find(Sword.SWBuf("AbsoluteDataPath"))
				if (entry != mod_second.end()):
					absolutePath = entry.value()[1].c_str()
					relativePath = absolutePath
					
					entry = mod_second.find(Sword.SWBuf("PrefixPath"))
					if (entry != mod_second.end()):
						relativePath = relativePath[entry.value()[1].size():]
					else:
						relativePath = relativePath[len(mgr.prefixPath):]

					printf("***** mgr.prefixPath: %s", mgr.prefixPath)
					printf("***** destMgr.prefixPath: %s", destMgr.prefixPath)
					printf("***** absolutePath: %s", absolutePath)
					printf("***** relativePath: %s", relativePath)
		
					if install_source:
						if self.ftpCopy(install_source, relativePath, 
							absolutePath, True):
							aborted = True;	# user aborted

					if not aborted:
						destPath = (destMgr.prefixPath or "") + relativePath
						FileMgr.copyDir(absolutePath, destPath)
					
					if install_source:
						# delete tmp ftp files
						mgr.deleteModule(modName)
						FileMgr.removeDir(absolutePath)
			
			if not aborted:
				confDir = sourceDir + "mods.d/";
				try:
					items = os.listdir(confDir)
				except OSError:
					pass
				else:
					for item in items:
						modFile = confDir
						modFile += item
						config = Sword.SWConfig(modFile)
						if config.getSections().find(Sword.SWBuf(modName)) != \
							config.getSections().end():
							targetFile = destMgr.configPath or ""#; //"./mods.d/";
							targetFile = removeTrailingSlash(targetFile)
							targetFile += "/"
							targetFile += item
							FileMgr.copyFile(modFile, targetFile)
							if (cipher):
								if self.getCipherCode(modName, config):
									# An error has occurred with getting
									# cipher code
									# This removes the module
									# Is this wise?
									newDest = Sword.SWMgr(destMgr.prefixPath)
									self.removeModule(newDest, modName)
									aborted = True
								else:
									config.Save()
									FileMgr.copyFile(modFile, targetFile)
						
						del config
			
			if aborted:
				return -1
			
			return 0
		return 1
	


	# override this and provide an input mechanism to allow your users
	# to enter the decipher code for a module.
	# return True you added the cipher code to the config.
	# default to return 'aborted'
	def getCipherCode(self, modName, config):
		return False

		# a sample implementation, roughly taken from the windows installmgr
		#
		#  SectionMap::iterator section;
		#  ConfigEntMap::iterator entry;
		#  SWBuf tmpBuf;
		#  section = config.getSections().find(Sword.SWBufmodName);
		#  if (section != config.getSections().end()) {
		#  	entry = section.value()[1].find(Sword.SWBuf"CipherKey");
		#  	if (entry != section.value()[1].end()) {
		#  		entry.value()[1] = GET_USER_INPUT();
		#  		config.Save();
		#
		#  		// LET'S SHOW THE USER SOME SAMPLE TEXT FROM THE MODULE
		#  		SWMgr *mgr = new SWMgr();
		#  		SWModule *mod = mgr.Modules[modName];
		#  		mod.setKey("Ipet 2:12");
		#  		tmpBuf = mod.StripText();
		#  		mod.setKey("gen 1:10");
		#  		tmpBuf += "\n\n";
		#  		tmpBuf += mod.StripText();
		#  		SOME_DIALOG_CONTROL.SETTEXT(tmpBuf.c_str());
		#  		delete mgr;
		#
		#  		// if USER CLICKS OK means we should return True
		#  		return True;
		#  	}
		#  }
		#  return False;
		#

	def refreshRemoteSource(self, install_source):
		root = self.privatePath + "/" + install_source.source
		root = removeTrailingSlash(root)
		target = root + "/mods.d"
		errorCode = -1 # 0 means successful
		
		FileMgr.removeDir(target)
	
		if not FileMgr.existsDir(target):
			#FileMgr.createPathAndFile(target+"/globals.conf")
			os.makedirs(target)
	
		archive = root + "/mods.d.tar.gz"
		
		errorCode = self.ftpCopy(install_source, "mods.d.tar.gz", 
			archive, False)

		if not errorCode:
			# sucessfully downloaded the tar,gz of module configs
			untargz(archive, root)

		# if the tar.gz download was canceled don't 
		# continue with another download		
		elif not self.term: 
			#copy the whole directory			
			errorCode = self.ftpCopy(install_source, "mods.d", target,
				True, ".conf")

		install_source.flush()
		return errorCode

	def isDefaultModule(self, modName):
		return modName in self.defaultMods
	
	def getModuleStatus(self, base, other):
		"""getModuleStatus - compare the modules of two SWMgrs and return a 
		vector describing the status of each.  See MODSTAT_*"""
		
		retVal = {}

		for (modname, mod) in other.getModules().keys():
			modStat = 0

			cipher = False
			keyPresent = False
			
			v = mod.getConfigEntry("CipherKey")
			if v:
				cipher = True
				keyPresent = v
			
			targetVersion = "0.0"
			sourceVersion = "1.0"
			softwareVersion = Sword.cvar.SWVersion_currentVersion
			
			v = mod.getConfigEntry("Version")
			if v:
				sourceVersion = v

			v = mod.getConfigEntry("MinimumVersion")
			if v:
				softwareVersion = v

			baseMod = base.getModule(modname)
			if baseMod:
				targetVersion = "1.0"
				v = baseMod.getConfigEntry("Version")
				if v:
					targetVersion = v
				
				source_v, target_v = (
					Sword.SWVersion(sourceVersion),
					Sword.SWVersion(targetVersion)
				)

				if source_v > target_v:
					modStat |= self.MODSTAT_UPDATED
				elif source_v < target_v:
					modStat |= self.MODSTAT_OLDER
				else:
					modStat |= self.MODSTAT_SAMEVERSION
			else:
				modStat |= self.MODSTAT_NEW

			if cipher: 
				modStat |= self.MODSTAT_CIPHERED

			if keyPresent:
				modStat |= self.MODSTAT_CIPHERKEYPRESENT
			
			retVal[mod] = modStat

		return retVal



	
if __name__ == '__main__':
	i = InstallMgr("/afs/monash/users/b/p/bpmor3/.sword/InstallMgr")
	print i.sources, i.defaultMods
