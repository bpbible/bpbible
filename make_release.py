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
raw_version_number = None
new_version = None
is_alpha = False
is_beta = False
beta_number = ''
py2exe_opts = ""
show_splashscreen = True
portable_build = False
portable_prerelease_status_number = None

def handle_args():
	opts, args = getopt.getopt(sys.argv[1:], "r", ["make-release", "compress", "no-splashscreen", "portable", "pre-release=", "beta=", "alpha="])
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
		for o, a in opts:
			global is_alpha, is_beta, beta_number
			if o == "--beta":
				is_beta = True
				beta_number = a
			elif o == "--alpha":
				is_alpha = True
				beta_number = a

	global new_version, new_version_long_name, raw_version_number
	if len(args) != 1:
		if make_release:
			sys.stderr.write("Usage: make_release.py [-r] <version number>")
			sys.exit(1)
		else:
			raw_version_number = "0.0"
	else:
		raw_version_number = args[0]

	new_version = new_version_long_name = raw_version_number
	if is_beta:
		new_version = "%sb%s" % (raw_version_number, beta_number)
		new_version_long_name = "%s Beta %s" % (raw_version_number, beta_number)
	elif is_alpha:
		new_version = "%sa%s" % (raw_version_number, beta_number)
		new_version_long_name = "%s Alpha %s" % (raw_version_number, beta_number)

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
	summary="BPBible %s source code" % new_version_long_name,
	labels=["Type-Source", "OpSys-All", "Featured"],
)

installer = DictWrapper(
	file=os.path.join("installer", "bpbible-%s-setup.exe" % new_version),
	summary="BPBible %s installer" % new_version_long_name,
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
IndexPath = $DATADIR/indexes
SwordPath = $DATADIR"""
	open("%s/paths.ini" % src_dist.dir, "w").write(paths_conf)
	open("dist/paths.ini", "w").write(paths_conf)

from config import bpbible_configuration, release_settings, splashscreen_settings
release_settings["version"] = new_version_long_name
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
	os.system("svn cp -m \"Tagged release %(new_version_long_name)s\""
			" %(svn_trunk)s %(svn_release_tag)s" % globals())

def build_src_dist(zip_file):
	global portable_build
	print "Building the source distribution."
	if make_release:
		os.system("svn export --force %s %s" % (svn_release_tag, src_dist.dir))
	else:
		os.system("svn export --force . %s" % src_dist.dir)
	if not portable_build:
		os.system("zip -r %s %s" % (zip_file, src_dist.dir))

def build_installer():
	global portable_build
	portable_apps_dir = "\\PortableApps"
	if not os.path.isdir(portable_apps_dir):
		portable_apps_dir = "C:\\PortableApps"

	if portable_build:
		upx_path = os.path.join(portable_apps_dir, "PortableApps.comAppCompactor\\App\\bin\\upx.exe")
		pai_path = os.path.join(portable_apps_dir, "PortableApps.comInstaller\\PortableApps.comInstaller.exe")
		palg_path = os.path.join(portable_apps_dir, "PortableApps.comLauncher\\PortableApps.comLauncherGenerator.exe")

		if not (os.path.exists(pai_path) and os.path.exists(palg_path) and os.path.exists(upx_path) and os.path.exists("BPBiblePortable\\Data\\resources\\mods.d")):
			sys.stderr.write("\n*** UNABLE TO BUILD BPBIBLE PORTABLE ***\n")
			sys.stderr.write("One or more dependancies for compiling BPBible Portable have not been met.\nPlease install them to the standard locations and then try again.\n")
			if not os.path.exists(pai_path):
				sys.stderr.write(" - PortableApps.com Installer: http://portableapps.com/installer\n")
			if not os.path.exists(palg_path):
				sys.stderr.write(" - PortableApps.com Launcher: http://portableapps.com/apps/development/portableapps.com_launcher\n")
			if not os.path.exists(upx_path):
				sys.stderr.write(" - PortableApps.com AppCompactor: http://portableapps.com/apps/utilities/portableapps.com_appcompactor\n")
			if not os.path.exists("BPBiblePortable\\Data\\resources\\mods.d"):
				maybe_make_dir("BPBiblePortable")
				sys.stderr.write(" - Additional resources: get a previous copy of BPBible Portable, copy BPBiblePortable\\Data\\resources\n")
			sys.exit(1)

	print "Building the binary distribution."
	os.system("python make_py2exe.py %s %s" % (py2exe_opts, new_version))

	import wx
	wx_dir = os.path.dirname(wx.__file__)

	if portable_build:
		os.system("copy %s dist" % os.path.join(wx_dir, "gdiplus.dll"))
		os.system("copy %s dist" % os.path.join(wx_dir, "msvcp71.dll"))
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
		if os.path.exists("BPBiblePortable\\App"):
			import shutil
			shutil.rmtree("BPBiblePortable\\App")
		if os.path.exists("BPBiblePortable\\Other"):
			import shutil
			shutil.rmtree("BPBiblePortable\\Other")
		if os.path.exists("BPBiblePortable\\help.html"):
			os.remove("BPBiblePortable\\help.html")

		maybe_make_dir("BPBiblePortable")

		# help.html - no version numbering in here, just copy it.
		os.system("copy %s %s" % ("make_portable\\help.html", "BPBiblePortable"))

		# App
		os.mkdir("BPBiblePortable\\App")
		# App\readme.txt
		os.system("copy %s %s" % ("make_portable\\App-readme.txt", "BPBiblePortable\\App\\readme.txt"))

		# App\AppInfo
		os.mkdir("BPBiblePortable\\App\\AppInfo")
		# App\AppInfo\appicon.ico
		os.system("copy %s %s" % ("graphics\\bpbible.ico", "BPBiblePortable\\App\\AppInfo\\appicon.ico"))
		os.system("copy %s %s" % ("graphics\\bible-16x16.png", "BPBiblePortable\\App\\AppInfo\\appicon_16.png"))
		os.system("copy %s %s" % ("graphics\\bible-32x32.png", "BPBiblePortable\\App\\AppInfo\\appicon_32.png"))
		# App\AppInfo\appinfo.ini
		appinfo_contents = open("%s.template" % "make_portable\\appinfo.ini", "r").read()
		if portable_prerelease_status_number:
			appinfo_display_version = "%s Pre-Release %s" % (new_version, portable_prerelease_status_number)
		else:
			appinfo_display_version = new_version

		# Make an X.X.X.X-format version number out of the version number
		new_version_four_part = ".".join((new_version.split(".") + ["0", "0", "0"])[:4])

		appinfo_contents = appinfo_contents.replace("$APPVERSION", new_version_four_part)
		appinfo_contents = appinfo_contents.replace("$APPDISPLAYVERSION", appinfo_display_version)
		open("BPBiblePortable\\App\\AppInfo\\appinfo.ini", "w").write(appinfo_contents)
		# App\AppInfo\installer.ini
		os.system("copy %s %s" % ("make_portable\\installer.ini", "BPBiblePortable\\App\\AppInfo"))

		# App\AppInfo\Launcher
		os.mkdir("BPBiblePortable\\App\\AppInfo\\Launcher")
		os.system("copy %s\\*.* %s" % ("make_portable\\launcher", "BPBiblePortable\\App\\AppInfo\\Launcher"))

		# App\DefaultData
		os.mkdir("BPBiblePortable\\App\\DefaultData")
		os.mkdir("BPBiblePortable\\App\\DefaultData\\settings")
		os.system("copy %s %s" % ("make_portable\\sword.conf", "BPBiblePortable\\DefaultData\\settings"))
		os.system("copy %s %s" % ("make_portable\\BPBiblePortableSettings.ini", "BPBiblePortable\\DefaultData\\settings"))

		# App\BPBible
		os.rename("dist", "BPBiblePortable\\App\\BPBible")

		# Other
		# Other\Help
		os.makedirs("BPBiblePortable\\Other\\Help\\images")
		os.system("copy %s\\*.* %s" % ("make_portable\\help_images", "BPBiblePortable\\Other\\Help\\images"))
		# Other\Source
		os.mkdir("BPBiblePortable\\Other\\Source")
		os.system("copy %s\\*.* %s" % ("make_portable\\source", "BPBiblePortable\\Other\\Source"))

		print "Compiling the BPBible Portable launcher..."
		os.system("%s %s" % (palg_path, os.path.abspath("BPBiblePortable")))
		if not os.path.exists("BPBiblePortable\\BPBiblePortable.exe"):
			sys.stderr.write("\n*** UNABLE TO BUILD BPBIBLE PORTABLE ***\n")
			sys.stderr.write("Compiling the BPBible Portable launcher failed for some reason!\nPlease sort that out and then try again.\n(File not found: BPBiblePortable\\BPBiblePortable.exe)")
			sys.exit(1)


		print "Compiling the BPBible Portable installer..."
		os.system("%s %s" % (pai_path, os.path.abspath("BPBiblePortable")))

		if portable_prerelease_status_number:
			installer_filename = "BPBiblePortable_%s_Pre-Release_%s.paf.exe" % (new_version, portable_prerelease_status_number)
		else:
			installer_filename = "BPBiblePortable_%s.paf.exe" % new_version

		if not os.path.exists(installer_filename):
			sys.stderr.write("\n*** UNABLE TO BUILD BPBIBLE PORTABLE ***\n")
			sys.stderr.write("Compiling the BPBible Portable installer failed for some reason!\nPlease sort that out and then try again.\n(File not found: %s)" % installer_filename)
			sys.exit(1)

		print "\n\nAll done!  Please verify that everything works."

	else:
		os.system("copy %s installer" % os.path.join(wx_dir, "gdiplus.dll"))
		os.system("copy %s installer" % os.path.join(wx_dir, "msvcp71.dll"))

		print "Creating the installer."
		iss_file = os.path.join("installer", "bpbible.iss")
		iss_contents = open("%s.template" % iss_file, "r").read().replace("$APP_VERSION_RAW_NUMBER", raw_version_number).replace("$APP_VERSION_LONG_NAME", new_version_long_name).replace("$APP_VERSION_SHORT_NAME", new_version)
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
	if ("Featured" in options.labels) and (is_alpha or is_beta):
		# Beta releases should not be featured.
		options.labels.remove("Featured")
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
