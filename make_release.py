#!/usr/bin/env python
# This module builds a new release of BPBible, updating the version numbers
# and so on.
# It uses the Google Code upload script to upload the release to the BPBible
# Google Code project.

import getopt
import getpass
import httplib
import os
import sys
from contrib import googlecode_upload

make_release = False
new_version = None
py2exe_opts = ""
show_splashscreen = True
portable_build = False
portable_prerelease_status_number = None

def handle_args():
	opts, args = getopt.getopt(sys.argv[1:], "r", ["make-release", "compress", "no-splashscreen", "portable", "pre-release="])
	global py2exe_opts
	global show_splashscreen
	if ('--portable', '') in opts:
		global portable_build
		portable_build = True
		py2exe_opts += " compressed "
		show_splashscreen = False
		for o, a in opts:
			if o == "--pre-release":
				global portable_prerelease_status_number
				portable_prerelease_status_number = a
		# make_release is intentionally left False

	else:
		if ('-r', '') in opts or ('--make-release', '') in opts:
			global make_release
			make_release = True

		if ('--compress', '') in opts:
			py2exe_opts += " compressed "

		if ('--no-splashscreen', '') in opts:
			show_splashscreen = False

	global new_version
	if len(args) != 1:
		if make_release:
			sys.stderr.write("Usage: make_release.py [-r] <version number>")
			sys.exit(1)
		else:
			new_version = "0.0"
	else:
		new_version = args[0]

handle_args()

svn_base = "https://bpbible.googlecode.com/svn"
svn_trunk = "%s/trunk" % svn_base
svn_release_tag = "%s/tags/release-%s" % (svn_base, new_version)

class DictWrapper(object):
	def __init__(self, **kwargs):
		self.__dict__ = kwargs

src_dist = DictWrapper(
	file="bpbible-%s-src.zip" % new_version,
	dir="bpbible-%s" % new_version,
	summary="BPBible %s source code" % new_version,
	labels=["Type-Source", "OpSys-All", "Featured"],
)

installer = DictWrapper(
	file=os.path.join("installer", "bpbible-%s-setup.exe" % new_version),
	summary="BPBible %s installer" % new_version,
	labels=["Type-Installer", "OpSys-Windows", "Featured"],
)

def maybe_make_dir(dir):
	if not os.path.exists(dir):
		os.mkdir(dir)

maybe_make_dir("dist")
maybe_make_dir("%s" % src_dist.dir)

if not portable_build:
	paths_conf = """\
[BPBiblePaths]
DataPath = $DATADIR
IndexPath = $DATADIR/indexes"""
	open("%s/paths.ini" % src_dist.dir, "w").write(paths_conf)
	open("dist/paths.ini", "w").write(paths_conf)

from config import bpbible_configuration, release_settings, splashscreen_settings
release_settings["version"] = new_version
release_settings["is_released"] = True
splashscreen_settings["show"] = show_splashscreen
bpbible_configuration.save("%s/bpbible.conf" % src_dist.dir)
bpbible_configuration.save("dist/bpbible.conf")

def main():
	build_src_dist(src_dist.file)
	build_installer()
	
	if not make_release:
		return

	tag_release()
	build_src_dist(src_dist.file)
	upload_release()

def tag_release():
	if not make_release:
		return

	print "Tagging the release."
	os.system("svn cp -m \"Tagged release %(new_version)s\""
			" %(svn_trunk)s %(svn_release_tag)s" % globals())

def build_src_dist(zip_file):
	print "Building the source distribution."
	if make_release:
		os.system("svn export --force %s %s" % (svn_release_tag, src_dist.dir))
	else:
		os.system("svn export --force . %s" % src_dist.dir)
	os.system("zip -r %s %s" % (zip_file, src_dist.dir))

def build_installer():
	print "Building the binary distribution."
	os.system("python make_py2exe.py %s %s" % (py2exe_opts, new_version))

	import wx
	wx_dir = os.path.dirname(wx.__file__)
	global portable_build
	if portable_build:
		os.system("copy %s dist" % os.path.join(wx_dir, "gdiplus.dll"))
		os.system("copy %s dist" % os.path.join(wx_dir, "msvcp71.dll"))
		if os.path.exists("\\PortableApps\\AppCompactor\\App\\bin\\upx.exe"):
			upx_path = "\\PortableApps\\AppCompactor\\App\\bin\\upx.exe"
		else:
			for path in os.environ["PATH"].split(os.pathsep):
				tmppath = os.path.join(path, "upx.exe")
				if os.path.exists(tmppath) and os.access(tmppath, os.X_OK):
					upx_path = tmppath
					break

		if os.path.exists(upx_path):
			print "Compressing further with UPX..."
			os.chdir("dist")
			import glob
			for file in glob.glob("*.exe")+glob.glob("*.dll"):
				os.system("%s --best --compress-icons=0 --nrv2e --crp-ms=999999 -k %s" % (upx_path, file))
				if os.system("%s -t %s" % (upx_path, file)):
					# Broken/didn't work: rename backup to original filename
					os.rename(file[:-1]+"~", file)
				else:
					# Worked: remove backup
					if os.path.exists(file[:-1]+"~"):
						os.remove(file[:-1]+"~")
			os.chdir("..")

		# Put together the BPBible Portable package for distribution
		if os.path.exists("BPBiblePortable"):
			# Remove an old copy of the directory
			import shutil
			shutil.rmtree("BPBiblePortable")

		os.mkdir("BPBiblePortable")

		# help.html - no version numbering in here, just copy it.
		os.system("copy %s %s" % (os.path.join("make_portable", "help.html"), "BPBiblePortable"))

		# App
		os.mkdir(os.path.join("BPBiblePortable", "App"))
		# App\readme.txt
		open(os.path.join("BPBiblePortable", "App", "readme.txt"), "w").write("The files in this directory are necessary for BPBible Portable to function.  There is normally no need to directly access or alter any of the files within these directories.")

		# App\AppInfo
		os.mkdir(os.path.join("BPBiblePortable", "App", "AppInfo"))
		# App\AppInfo\appicon.ico
		os.system("copy %s %s" % (os.path.join("graphics", "bpbible.ico"), os.path.join("BPBiblePortable", "App", "AppInfo", "appicon.ico")))
		# App\AppInfo\appinfo.ini
		appinfo_contents = open("%s.template" % os.path.join("make_portable", "appinfo.ini"), "r").read()
		if portable_prerelease_status_number:
			appinfo_display_version = "%s Pre-Release %s" % (new_version, portable_prerelease_status_number)
		else:
			appinfo_display_version = new_version

		# Make an X.X.X.X-format version number out of the version number
		new_version_four_part = new_version.split(".")
		while len(new_version_four_part) < 4:
			new_version_four_part.append("0")
		new_version_four_part = ".".join(new_version_four_part)

		appinfo_contents = appinfo_contents.replace("$APPVERSION", new_version_four_part)
		appinfo_contents = appinfo_contents.replace("$APPDISPLAYVERSION", appinfo_display_version)
		open(os.path.join("BPBiblePortable", "App", "AppInfo", "appinfo.ini"), "w").write(appinfo_contents)

		# App\BPBible
		os.rename("dist", os.path.join("BPBiblePortable", "App", "BPBible"))

		# Other
		# Other\Help
		os.makedirs(os.path.join("BPBiblePortable", "Other", "Help", "images"))
		os.system("copy %s\\*.* %s" % (os.path.join("make_portable", "help_images"), os.path.join("BPBiblePortable", "Other", "Help", "images")))
		# Other\Source
		os.mkdir(os.path.join("BPBiblePortable", "Other", "Source"))
		os.system("copy %s\\*.* %s" % (os.path.join("make_portable", "source"), os.path.join("BPBiblePortable", "Other", "Source")))
		installerconfig_contents = open("%s.template" % os.path.join("make_portable", "PortableApps.comInstallerConfig.nsh"), "r").read()
		if portable_prerelease_status_number:
			installerconfig_installer_version = "%s_PRERELEASE%s" % (new_version, portable_prerelease_status_number)
		else:
			installerconfig_installer_version = new_version

		installerconfig_contents = installerconfig_contents.replace("$APPVERSION", new_version_four_part)
		installerconfig_contents = installerconfig_contents.replace("$APPINSTALLERFILENAMEVERSION", installerconfig_installer_version)
		open(os.path.join("BPBiblePortable", "Other", "Source", "PortableApps.comInstallerConfig.nsh"), "w").write(installerconfig_contents)

		if os.path.exists("\\PortableApps\\NSISPortable\\App\\NSIS\\makensis.exe"):
			nsis_path = "\\PortableApps\\NSISPortable\\App\\NSIS\\makensis.exe"
		else:
			for path in os.environ["PATH"].split(os.pathsep):
				tmppath = os.path.join(path, "makensis.exe")
				if os.path.exists(tmppath) and os.access(tmppath, os.X_OK):
					nsis_path = tmppath
					break

		print "Compiling the BPBible Portable launcher..."
		if os.path.exists(nsis_path):
			os.system("%s %s" % (nsis_path, os.path.abspath(os.path.join("BPBiblePortable", "Other", "Source", "BPBiblePortable.nsi"))))

		nocompileinstaller = False
		if not os.path.exists(upx_path):
			sys.stderr.write("Can't find UPX: you will need to compress BPBiblePortable\App\BPBible with the\nPortableApps.com AppCompactor (http://PortableApps.com/AppCompactor) before\ncompiling BPBiblePortable\Other\Source\PortableApps.comInstaller.nsi with NSIS.")
			nocompileinstaller = True

		if not os.path.exists(os.path.join("BPBiblePortableOptional1", "Data", "resources", "mods.d")):
			os.mkdir("BPBiblePortableOptional1")
			sys.stderr.write("You don't have the additional resources package!\nInstall a previous copy of BPBible Portable with the additional resources and\nthen copy from its installation directory the Data directory to\n./BPBiblePortableOptional1 (/Data/resources/...)")
			nocompileinstaller = True

		if not nocompileinstaller and os.path.exists(nsis_path):
			# Everything there!
			print "Compiling the BPBible Portable installer..."
			os.system("%s %s" % (nsis_path, os.path.abspath(os.path.join("BPBiblePortable", "Other", "Source", "PortableApps.comInstaller.nsi"))))

	else:
		os.system("copy %s installer" % os.path.join(wx_dir, "gdiplus.dll"))
		os.system("copy %s installer" % os.path.join(wx_dir, "msvcp71.dll"))

		print "Creating the installer."
		iss_file = os.path.join("installer", "bpbible.iss")
		iss_contents = open("%s.template" % iss_file, "r").read().replace("$APP_VERSION", new_version)
		open(iss_file, "w").write(iss_contents)
		os.system("iscc %s" % iss_file)

def upload_release():
	if not make_release:
		return

	print "Uploading the release to Google Code."
	user_name, password = get_credentials()
	do_upload(user_name, password, installer)
	do_upload(user_name, password, src_dist)

	print "Make sure you deprecate old releases."
	print "Remember to announce the release."

def do_upload(user_name, password, options):
	status, reason, url = googlecode_upload.upload(options.file, "bpbible", user_name, password,
			options.summary, options.labels)

	# Returns 403 Forbidden instead of 401 Unauthorized for bad
	# credentials as of 2007-07-17.
	if status in [httplib.FORBIDDEN, httplib.UNAUTHORIZED]:
		print "Upload of %s failed: %s" % (options.file, reason)
	else:
		print "%s uploaded to %s" % (options.file, url)

def get_credentials():
	"""Find credentials for Google Code.

	Copied from the Google Code file uploader.
	"""
	user_name = None
	password = None

	if user_name is None:
		sys.stdout.write('Please enter your googlecode.com username: ')
		sys.stdout.flush()
		user_name = sys.stdin.readline().rstrip()
	if password is None:
		print 'Please enter your googlecode.com password.'
		print '** Note that this is NOT your Gmail account password! **'
		print 'It is the password you use to access Subversion repositories,'
		print 'and can be found here: http://code.google.com/hosting/settings'
		password = getpass.getpass()
	return user_name, password

if __name__ == "__main__":
	main()
