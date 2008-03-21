BPBible

BPBible is a flexible Bible Study tool made using the SWORD project, Python 
and wxPython. This is the second release of the software, so there are probably a few problems still hanging around.

Website: bpbible.googlecode.com

Features
    * Bible application
      BPBible has many of the features you would expect in a Bible 
	  application - Bible, Commentary, and Dictionary support, Bible Search, 
	  Scripture tooltips, etc.

    * Cross verse searching
      BPBible uses a proximity based search, rather than a verse-based search. 
	  This means that a search can cross verse boundaries, giving a more 
	  natural search. It also supports regular expressions and phrases.

    * Flexible layout
	  BPBible lets you rearrange your layout, and will remember your layout 
	  for you.

    * Good module support
	  Due to the use of the SWORD libraries, BPBible can read many modules. 
	  The main module repository is at 
	  http://www.crosswire.org/sword/modules/index.jsp

    * Free
	  BPBible is licensed under the GPL and is absolutely free. 

Running binaries under Windows

To run the binaries under Windows, download the BPBible self-extracting executable. Open it, and extract it to the path of your choice. Now run bpbible.exe in the application directory.

Running from source

To build from source, you will need to have the following:

   1. wxPython 2.8 (preferably 2.8.7)
   2. Python 2.5 (though older versions may work)
   3. SWORD 1.5.10 (though older versions will probably work). Note that the latest SVN version of SWORD may crash on invalid verse ranges.
   4. Windows or Linux 

BPBible has not been tested under Mac, so it is unlikely to work. Any help with getting it working under Mac would be appreciated.

Building the SWIG bindings

If you are not using the SVN version of SWORD, download the SWIG bindings (sword-swig-r2147.zip). These contain a slightly modified version of the bindings from the SVN version of SWORD, which are needed. This should be compatible with SWORD 1.5.10 and earlier. Instructions on how to build are supplied in the README file.

Running BPBible

Once the SWIG bindings are installed, unzip the BPBible source. From there, run python bpbible.py. You do not need to run setup.py, which is used for building the Windows binaries. 

Installing Books

The main download point for books is at http://www.crosswire.org/sword/modules/index.jsp. When you download books, make sure you download the raw zip version.

Using WinZip, or a similar program, unzip these zip files into a directory of your choice. Now go File > Set Sword Paths and click the Add Item button (it has a green plus sign on it). Navigate to the directory you unzipped to, and click OK. It should now load the books you have downloaded. 


For more help, or to submit issues, visit the project webpage at bpbible.googlecode.com
