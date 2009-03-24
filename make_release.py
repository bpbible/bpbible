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

def handle_args():
	opts, args = getopt.getopt(sys.argv[1:], "r", ["make-release", "compress", "no-splashscreen", "portable"])
	global py2exe_opts
	global show_splashscreen
	if ('--portable', '') in opts:
		global portable_build
		portable_build = True
		py2exe_opts += " compressed "
		show_splashscreen = False

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
	IndexPath = $DATADIR/indexes
	"""
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
				os.system(upx_path + " --best --compress-icons=0 --nrv2e --crp-ms=999999 -k \"%s\"" % file)
				if os.system(upx_path + " -t \"%s\"" % file):
					# Broken/didn't work: rename backup to original filename
					os.rename(file[:-1]+"~", file)
				else:
					# Worked: remove backup
					os.remove(file[:-1]+"~")
		else:
			print "** Please compress this further with the PortableApps.com AppCompactor"
			print "(http://PortableApps.com/AppCompactor) before uploading it **"
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
