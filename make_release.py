#!/usr/bin/env python
# This module builds a new release of BPBible, updating the version numbers
# and so on.
# It uses the Google Code upload script to upload the release to the BPBible
# Google Code project.

import getopt
import getpass
import os
import re
import sys
from contrib import googlecode_upload

make_release = False
new_version = None

def handle_args():
	opts, args = getopt.getopt(sys.argv[1:], "r", ["make-release"])
	if ('-r', '') in opts or ('--make-release', '') in opts:
		global make_release
		make_release = True

	if len(args) != 1:
		sys.stderr.write("Usage: make_release.py [-r] <version number>")
		sys.exit(1)

	global new_version
	new_version = args[0]

handle_args()

iss_file = os.path.join("installer", "bpbible.iss")
filenames = "mainframe.py make_py2exe.py " + iss_file

svn_base = "https://bpbible.googlecode.com/svn"
svn_trunk = "%s/trunk" % svn_base
svn_release_tag = "%s/tags/release-%s" % (svn_base, new_version)

class DictWrapper(object):
	def __init__(self, **kwargs):
		self.__dict__ = kwargs

src_dist = DictWrapper(
	file="bpbible-%s-src.zip" % new_version,
	summary="BPBible %s source code" % new_version,
	labels=["Type-Source", "OpSys-All", "Featured"],
)

installer = DictWrapper(
	file=os.path.join("installer", "bpbible-%s-setup.zip" % new_version),
	summary="BPBible %s installer" % new_version,
	labels=["Type-Installer", "OpSys-Windows", "Featured"],
)

def find_current_version():
	return [line.replace("AppVersion=", "").strip()
			for line in open(iss_file, "r").xreadlines()
			if line.startswith("AppVersion=")][0]

current_version = find_current_version()

print "Current version:", current_version

def main():
	update_version_numbers(current_version, new_version)
	build_src_dist(src_dist.file)
	build_installer()
	
	if not make_release:
		return

	checkin_release()
	build_src_dist(src_dist.file)
	upload_release()

	print "Make sure you deprecate old releases."
	print "Remember to announce the release."

def update_version_numbers(current_version, new_version):
	print "Updating the version number in files: %s" % filenames
	for filename in filenames.split():
		do_replace(filename, current_version, new_version)

def do_replace(filename, old_string, new_string):
	file = open(filename, "rb")
	contents = file.read()
	file.close()
	file = open(filename, "wb")
	file.write(contents.replace(old_string, new_string))
	file.close()

def checkin_release():
	if not make_release:
		return

	print "Checking in the changes for the release."
	os.system("svn ci -m \"Updated version numbers for %(new_version)s.\" %(filenames)s" % globals())
	print "Tagging the release."
	os.system("svn cp -m \"Tagged release %(new_version)\""
			" %(svn_trunk)s %(svn_release_tag)s" % globals())

def build_src_dist(zip_file):
	print "Building the source distribution."
	if make_release:
		os.system("svn export %s bpbible" % svn_release_tag)
	else:
		os.system("svn export . bpbible")
	os.system("zip -r %s bpbible" % zip_file)

def build_installer():
	print "Building the binary distribution."
	os.system("python make_py2exe.py")

	import wx
	wx_dir = os.path.dirname(wx.__file__)
	os.system("copy %s installer" % os.path.join(wx_dir, "gdiplus.dll"))
	os.system("copy %s installer" % os.path.join(wx_dir, "msvcp71.dll"))

	print "Creating the installer."
	os.system("iscc %s" % iss_file)

def upload_release():
	if not make_release:
		return

	print "Uploading the release to Google Code."
	user_name, password = get_credentials()
	do_upload(user_name, password, options)

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
