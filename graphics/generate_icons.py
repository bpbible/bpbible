import sys, os
import wx
inkscape = "inkscape"
if sys.argv[1:]:
	inkscape = sys.argv[1]
path = os.getcwd()

for item in "16 24 32 48 64 127 128 256".split():
	
	dim = item
	
	str = r'"%(inkscape)s" -e %(path)s\bible-%(dim)sx%(dim)s.png -w %(dim)s -h'\
		  r"%(dim)s %(path)s\bible.svg"%locals()

	
	print str

	os.system(str)

# just use www.converticon.com instead of this
# app = wx.App(0)
# icon = wx.Image("bible-32x32.png")
# assert icon.IsOk()
# #icon.SetMask()
# print icon.HasAlpha()
# icon.ConvertAlphaToMask()
# 
# print icon.SaveFile("bible.ico", wx.BITMAP_TYPE_ICO)
