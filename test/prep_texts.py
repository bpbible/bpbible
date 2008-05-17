import os

encodings = dict(cp1252="Latin-1", utf8="UTF-8")
text = """\
$$$Key1
First key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la 
lumi\xe8re d'avec les t\xe9n\xe8bres.
$$$Key1/lumi\xe8re
Second key:
Et Dieu vit la lumi\xe8re, qu'elle \xe9tait bonne; et Dieu s\xe9para la
lumi\xe8re d'avec les t\xe9n\xe8bres."""

items = dict(genbook=(
"imp2gbs %(filename)s.imp -o modules/%(filename)s/%(filename)s",
"""\
[%(filename)s]
DataPath=./modules/%(filename)s/%(filename)s
Description=A test of %(filename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawGenBook
""", text),
dictionary=(
"imp2ld %(filename)s.imp modules/%(filename)s/%(filename)s",
"""\
[%(filename)s]
DataPath=./modules/%(filename)s/%(filename)s
Description=A test of %(filename)s - lumi\xe8re
SourceType=Plaintext
Encoding=%(sword_encoding)s
ModDrv=RawLD4
""", text),
)

if not os.path.exists("mods.d"):
	os.mkdir("mods.d")

for item, (importer, conf, text) in items.items():
	for encoding, sword_encoding in encodings.items():
		filename = "%s%s" % (encoding, item)
		f = open(filename + ".imp", "w")
		f.write(text.decode("cp1252").encode(encoding))
		f.close()
		f2 = open("mods.d/%s.conf" % filename, "w")
		f2.write((conf % locals()).decode("cp1252").encode(encoding))
		f2.close()

		if not os.path.exists("modules/%s" % filename):
			os.makedirs("modules/%s" % filename)

		assert not os.system(importer % locals()), "%s failed" % (
			importer % locals())
