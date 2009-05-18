BPBIBLE PORTABLE
================
Copyright (C) 2004-2008 John T. Haller of PortableApps.com
Copyright (C) 2008-2009 Chris Morgan of PortableApps.com

Website: http://PortableApps.com/BPBiblePortable

This software is OSI Certified Open Source Software.
OSI Certified is a certification mark of the Open Source Initiative.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

ABOUT BPBIBLE PORTABLE
======================
The BPBible Portable Launcher allows you to run BPBible from a removable drive whose letter changes as you move it to another computer.  The Bible tool and any Bible resources can be entirely self-contained on the drive and then used on any Windows computer.
It also automatically detects SWORD modules (a.k.a. books or resources) from The SWORD Project for Windows (a.k.a. BibleCS) Portable and SwordBible Portable and includes them in BPBible.


LICENSE
=======
This code is released under the GPL.  Within the Other\Source directory you will find the code (BPBiblePortable.nsi) as well as the full GPL license (License.txt).  If you use the launcher or code in your own product, please give proper and prominent attribution.


INSTALLATION / DIRECTORY STRUCTURE
==================================
By default, the program expects this directory structure:

-\ <--- Directory with BPBiblePortable.exe
  +\App\
    +\BPBible\
  +\Data\
    +\settings\
    +\resources\

The automatic detection of other portable Bible programs is this:
-\
  +\BPBiblePortable\ <--- Directory with BPBiblePortable.exe
    +\Data\
      +\resources\
          +\mods.d\
          +\modules\
  +\SwordBiblePortable\ <--- Directory with SwordBiblePortable.exe
    +\Data\
      +\mods.d\
      +\modules\
  +\SWORDProjectPortable\ <--- Directory with SwordBiblePortable.exe
    +\Data\
      +\settings\
        +\mods.d\
        +\modules\


BPBIBLEPORTABLE.INI CONFIGURATION
=================================
The BPBible Portable Launcher will look for an ini file called BPBiblePortable.ini within its directory.  If you are happy with the default options, it is not necessary, though.  There is an example INI included with this package to get you started.  The INI file is formatted as follows:

[BPBiblePortable]
AdditionalParameters=
DisableSplashScreen=false

The AdditionalParameters entry allows you to pass additional commandline parameter entries to bpbible.exe.  Whatever you enter here will be appended to the call to bpbible.exe.

The DisableSplashScreen entry allows you to run the BPBible Portable Launcher without the splash screen showing up.  The default is false.
