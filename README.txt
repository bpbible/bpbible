BPBible

BPBible is a flexible Bible Study tool made using the SWORD project, Python 
and wxPython. This is the fourth release of the software, so there may be a 
few problems still hanging around.

Website: bpbible.com

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

To run the binaries under Windows, download the BPBible installer (bpbible-x.x-setup.exe). For the installer, run it and follow the prompts. Now run bpbible.exe in the application directory, or use the Start Menu, Desktop and Quick Launch shortcuts, if you chose to create them.

Running from source

To build from source, you will need to have the following:

1. wxPython 2.8 (preferably at least 2.8.7) 
2. Python 2.5 (though older versions may work)
3. SWORD 1.6
4. Windows, Linux or Mac

BPBible works mostly under Mac. Certain features, like the quickselectors, do not appear correctly. Also, users must compile it themselves - there is no binary distribution yet.

Using the binaries under Linux

There are at present no binaries available for Linux.

Building the SWIG bindings

The SWIG bindings are located in the bindings/swig directory of the SWORD
source code. Instructions on how to build are supplied in the README file in
that directory.

If you want to install them under Linux, the procedure will probably be:
<change into the bindings/swig directory of the SWORD source code>
cd package
./configure
make pythonswig
make python_make
cd python
python setup.py install

If you try running BPBible and it gives errors about a missing symbol
uncompress, you need to modify the setup.py. Replace the line 
libraries=[('sword')],

with 
libraries=['sword', 'z', 'curl'],

Then run "python setup.py install" again.

Running BPBible

Once the SWIG bindings are installed, unzip the BPBible source. From there, run python bpbible.py.

Installing Books

The main download point for books is at http://www.crosswire.org/sword/modules/index.jsp.
When you download books, it is best to download the raw zip version (though
the others will work). 

Now do one of the following:
 # Drag the zip file onto BPBible.
 # In the file menu, select Install Books..., and locate the zip file.

You can now select the installation directory to install it to somewhere
different, or view the information associated with the module before
installing it. Now press OK to install the book. The book should show up in
the list of available books.

You can install multiple files at once. Just drag them all onto BPBible, or
select them all in the file selector.

For more help, or to submit issues, visit the project webpage at bpbible.googlecode.com
