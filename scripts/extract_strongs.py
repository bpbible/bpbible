import time
t = time.time()
from swlib.pysw import SW, TOP
from backend.create_module import ModuleCreator
from backend.bibleinterface import biblemgr
import re


sample = u'<entryFree n="G0001|\u0391"> <title>G1</title> <orth>\u0391</orth> <orth rend="bold" type="trans">A</orth> <pron rend="italic">al\'-fah</pron><lb/> <def>Of Hebrew origin; the first letter of the alphabet: figuratively only (from its use as a numeral) the <hi rend="italic">first</hi>. Often used (usually \u201can\u201d before a vowel) also in composition (as a contraction from <ref target="Strong:G0427">G427</ref>) in the sense of <hi rend="italic">privation</hi>; so in many words beginning with this letter; occasionally in the sense of <hi rend="italic">union</hi> (as a contraction of <ref target="Strong:G0260">G260</ref>): - Alpha.</def> </entryFree>'
strongs_real_greek_sample = u'<a name="00212">212</a>   <b>\u1f00\u03bb\u03b1\u03b6\u03bf\u03bd\u03b5\u1f77\u03b1</b> [A)LAZONEI/A] {alazone\xeda}   \\<i>al-ad-zon-i\'-a</i>\\<br /> from <a href="sword://StrongsRealGreek/00213">213</a>; braggadocio, i.e. (by implication) self-confidence:--boasting, pride. <br />See Greek <a href="sword://StrongsRealGreek/00213">213</a>.'

old_strongs_re = re.compile(r" \d+ +([^,;\n]+)")
old_strongs_unused = re.compile(
	' \d+  Not Used'
)


srg_unused = re.compile(
	'<a name="[^"]*">[^<]*</a> *'
	'Not Used'
)

srg_regex = re.compile(
	'<a name="[^"]*">[^<]*</a> *'
	'<b>([^<]*)</b> *'
	'\[[^\]]*\] *'
	'{([^}]*)} *'
	'\\\\<i>([^<]*)</i>\\\\<br />'
)

missed=[]

regex = re.compile(
	'<entryFree n="[GH]\d+\|([^"]*)"> '
	'<title>[GH]\d+</title> '
	'<orth>(.*?)</orth> '
	'<orth rend="bold" type="trans">(.*?)</orth> '
	'<pron rend="italic">(.*?)</pron>'
)


orig_module = ModuleCreator("HeadwordsOriginalLang", 
	driver=SW.RawLD, 
	key_type=SW.Key, 
	extra_attrs=dict(
		DistributionLicense="Public Domain",
		SourceType="ThML",
		Description="Strong's Headwords: Original Language",
		Feature="StrongsHeadwords",
		HeadwordsDesc="Original Language",
	),
	working_directory="resources",
)

transliteration_module = ModuleCreator("HeadwordsTransliterated", 
	driver=SW.RawLD, 
	key_type=SW.Key, 
	extra_attrs=dict(
		DistributionLicense="Public Domain",
		SourceType="ThML",
		Description="Strong's Headwords: Transliterated",
		Feature="StrongsHeadwords",
		HeadwordsDesc="Transliterated",
	),
	working_directory="resources",	
)

pronunciation_module = ModuleCreator("HeadwordsPronunciation", 
	driver=SW.RawLD, 
	key_type=SW.Key, 
	extra_attrs=dict(
		DistributionLicense="Public Domain",
		SourceType="ThML",
		Description="Strong's Headwords: Pronunciation",
		Feature="StrongsHeadwords",
		HeadwordsDesc="Pronunciation",
	),
	working_directory="resources",	
)

module = biblemgr.get_module("Strong")
greek = biblemgr.get_module("StrongsRealGreek")
hebrew = biblemgr.get_module("StrongsRealHebrew")
old_greek = biblemgr.get_module("StrongsGreek")
old_hebrew = biblemgr.get_module("StrongsHebrew")


assert module, "Couldn't read Strong module"
assert greek, "Couldn't read StrongsRealGreek"

# go to the top
module.setPosition(TOP)
old_greek.setPosition(TOP)
old_hebrew.setPosition(TOP)

greek.setPosition(TOP)

bad_source_text = dict(
	# can't handle nested beta codes
	G1490 = (u'<a name="01490">1490</a>  <b>\u03b5\u1f30 \u03b4\u1f72 \u03bc\u1f75(\u03b3\u03b5)</b> [EI) DE\\ MH/[1GE]1] {ei d\xe8 m\u1e17(ge)}  \\<i>i deh may\'-(gheh)</i>\\<br /> from <a href="sword://StrongsRealGreek/01487">1487</a>, <a href="sword://StrongsRealGreek/01161">1161</a>, and <a href="sword://StrongsRealGreek/03361">3361</a> (sometimes with <a href="sword://StrongsRealGreek/01065">1065</a> added); but if not:--(or) else, if (not, otherwise), otherwise. <br />See Greek <a href="sword://StrongsRealGreek/01487">1487</a>. <br />See Greek <a href="sword://StrongsRealGreek/01161">1161</a>. <br />See Greek <a href="sword://StrongsRealGreek/03361">3361</a>. <br />See Greek <a href="sword://StrongsRealGreek/01065">1065</a>.', u'<a name="01490">1490</a>  <b>\u03b5\u1f30 \u03b4\u1f72 \u03bc\u1f75(\u03b3\u03b5)</b> [BM JUNK] {ei d\xe8 m\u1e17(ge)}  \\<i>i deh may\'-(gheh)</i>\\<br /> from <a href="sword://StrongsRealGreek/01487">1487</a>, <a href="sword://StrongsRealGreek/01161">1161</a>, and <a href="sword://StrongsRealGreek/03361">3361</a> (sometimes with <a href="sword://StrongsRealGreek/01065">1065</a> added); but if not:--(or) else, if (not, otherwise), otherwise. <br />See Greek <a href="sword://StrongsRealGreek/01487">1487</a>. <br />See Greek <a href="sword://StrongsRealGreek/01161">1161</a>. <br />See Greek <a href="sword://StrongsRealGreek/03361">3361</a>. <br />See Greek <a href="sword://StrongsRealGreek/01065">1065</a>.'),
	H0026=(u'<entryFree n="H0026|\u05d0\u05d1\u05d9\u05d2\u05dc  \u05d0\u05d1\u05d9\u05d2\u05d9\u05dc"> <title>H26</title> <orth>\u05d0\u05d1\u05d9\u05d2\u05dc  \u05d0\u05d1\u05d9\u05d2\u05d9\u05dc</orth> <orth rend="bold" type="trans">\'\u0103b\xeeygayil  \'\u0103b\xeeygal</orth> <pron rend="italic">ab-ee-gah\'yil ab-ee-gal\'</pron><lb/> <def>From <ref target="Strong:H0001">H1</ref> and <ref target="Strong:H1524">H1524</ref>; <hi rend="italic">father</hi> (that is <hi rend="italic">source</hi>) <hi rend="italic">of joy</hi>;<lb/> <hi rend="italic">Abigail</hi> or <hi rend="italic">Abigal</hi> the name of two Israelitesses: - Abigal.</def> </entryFree>',u'<entryFree n="H0026|\u05d0\u05d1\u05d9\u05d2\u05dc  \u05d0\u05d1\u05d9\u05d2\u05d9\u05dc"> <title>H26</title> <orth>\u05d0\u05d1\u05d9\u05d2\u05dc    \u05d0\u05d1\u05d9\u05d2\u05d9\u05dc</orth> <orth rend="bold" type="trans">\'\u0103b\xeeygayil  \'\u0103b\xeeygal</orth> <pron rend="italic">ab-ee-gah\'yil ab-ee-gal\'</pron><lb/> <def>From <ref target="Strong:H0001">H1</ref> and <ref target="Strong:H1524">H1524</ref>; <hi rend="italic">father</hi> (that is <hi rend="italic">source</hi>) <hi rend="italic">of joy</hi>;<lb/> <hi rend="italic">Abigail</hi> or <hi rend="italic">Abigal</hi> the name of two Israelitesses: - Abigal.</def> </entryFree>'),
	H0381=(u'<entryFree n="H0381|\u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9   \u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9\u05dc"> <title>H381</title> <orth>\u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9   \u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9\u05dc</orth> <orth rend="bold" type="trans">\'\xeeysh-chayil  \'\xeeysh-chay</orth> <pron rend="italic">eesh-khah\'-yil eesh-khah\'ee</pron><lb/> <def>From <ref target="Strong:H0376">H376</ref> and <ref target="Strong:H2428">H2428</ref>; <hi rend="italic">man of might</hi>; (The second form is by defective transcription used in <ref osisRef="2Sam.23.20">2Sam 23:20</ref>); as if from <ref target="Strong:H0376">H376</ref> and <ref target="Strong:H2416">H2416</ref>; <hi rend="italic">living man</hi>;<lb/> <hi rend="italic">Ishchail</hi> (or <hi rend="italic">Ishchai</hi>) an Israelite: - a valiant man.</def> </entryFree>',u'<entryFree n="H0381|\u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9   \u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9\u05dc"> <title>H381</title> <orth>\u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9    \u05d0\u05d9\u05e9\u05c1\u05be\u05d7\u05d9\u05dc</orth> <orth rend="bold" type="trans">\'\xeeysh-chayil  \'\xeeysh-chay</orth> <pron rend="italic">eesh-khah\'-yil eesh-khah\'ee</pron><lb/> <def>From <ref target="Strong:H0376">H376</ref> and <ref target="Strong:H2428">H2428</ref>; <hi rend="italic">man of might</hi>; (The second form is by defective transcription used in <ref osisRef="2Sam.23.20">2Sam 23:20</ref>); as if from <ref target="Strong:H0376">H376</ref> and <ref target="Strong:H2416">H2416</ref>; <hi rend="italic">living man</hi>;<lb/> <hi rend="italic">Ishchail</hi> (or <hi rend="italic">Ishchai</hi>) an Israelite: - a valiant man.</def> </entryFree>'),
	H0401=(u'<entryFree n="H0401|\u05d0\u05db\u05bc\u05dc   \u05d0\u05db\u05dc"> <title>H401</title> <orth>\u05d0\u05db\u05bc\u05dc   \u05d0\u05db\u05dc</orth> <orth rend="bold" type="trans">\'\xfbk\xe2l  \'\xfbkk\xe2l</orth> <pron rend="italic">oo-kawl\' ook-kawl\'</pron><lb/> <def>Apparently from <ref target="Strong:H0398">H398</ref>; <hi rend="italic">devoured</hi>;<lb/> <hi rend="italic">Ucal</hi> a fancy name: - Ucal.</def> </entryFree>',u'<entryFree n="H0401|\u05d0\u05db\u05bc\u05dc   \u05d0\u05db\u05dc"> <title>H401</title> <orth>\u05d0\u05db\u05bc\u05dc    \u05d0\u05db\u05dc</orth> <orth rend="bold" type="trans">\'\xfbk\xe2l  \'\xfbkk\xe2l</orth> <pron rend="italic">oo-kawl\' ook-kawl\'</pron><lb/> <def>Apparently from <ref target="Strong:H0398">H398</ref>; <hi rend="italic">devoured</hi>;<lb/> <hi rend="italic">Ucal</hi> a fancy name: - Ucal.</def> </entryFree>'),
	H0413=(u'<entryFree n="H0413|\u05d0\u05dc   \u05d0\u05dc"> <title>H413</title> <orth>\u05d0\u05dc   \u05d0\u05dc</orth> <orth rend="bold" type="trans">\'\xeal  \'el</orth> <pron rend="italic">ale el</pron><lb/> <def>(Used only in the shortened constructive form (the second form)); a primitive particle properly denoting motion <hi rend="italic">towards</hi> but occasionally used of a quiescent position that is <hi rend="italic">near</hi>6<lb/> <hi rend="italic">with</hi> or <hi rend="italic">among</hi>; often in general <hi rend="italic">to:</hi> - about according to after against among as for at because (-fore -side) both . . . and by concerning for from \xd7 hath in (-to) near (out) of over through6to (-ward) under unto upon whether with(-in).</def> </entryFree>',u'<entryFree n="H0413|\u05d0\u05dc   \u05d0\u05dc"> <title>H413</title> <orth>\u05d0\u05dc    \u05d0\u05dc</orth> <orth rend="bold" type="trans">\'\xeal  \'el</orth> <pron rend="italic">ale el</pron><lb/> <def>(Used only in the shortened constructive form (the second form)); a primitive particle properly denoting motion <hi rend="italic">towards</hi> but occasionally used of a quiescent position that is <hi rend="italic">near</hi>6<lb/> <hi rend="italic">with</hi> or <hi rend="italic">among</hi>; often in general <hi rend="italic">to:</hi> - about according to after against among as for at because (-fore -side) both . . . and by concerning for from \xd7 hath in (-to) near (out) of over through6to (-ward) under unto upon whether with(-in).</def> </entryFree>'),
	H5019=(u'<entryFree n="H5019|\u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e0\u05d0\u05e6\u05bc\u05e8"> <title>H5019</title> <orth>\u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e0\u05d0\u05e6\u05bc\u05e8</orth> <orth rend="bold" type="trans">\u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e8\u05d0 \u05e6\u05bc\u05d5\u05e8    \u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e8\u05d0\u05e6\u05bc\u05e8</orth> <pron rend="italic">n<hi rend="super">e</hi>b\xfbkadne\'tstsar  neb\xfbkadre\'tstsar  neb\xfbkadre\'ts\xf4r</pron><lb/> <def><hi rend="italic">neb-oo-kad-nets-tsar\' neb-oo-kad-rets-tsar\' neb-oo-kad-tsore</hi> <lb/>Of foreign derivation;<lb/> <hi rend="italic">Nebukadnetstsar</hi> (or <hi rend="italic">retstsar</hi> or <hi rend="italic">retstsor</hi>) king of Babylon: - Nebuchadnezzar Nebuchadrezzar.</def> </entryFree>',
	u'<entryFree n="H5019|\u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e0\u05d0\u05e6\u05bc\u05e8"> <title>H5019</title> <orth>\u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e0\u05d0\u05e6\u05bc\u05e8    \u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e8\u05d0 \u05e6\u05bc\u05d5\u05e8    \u05e0\u05d1\u05d5\u05bc\u05db\u05d3\u05e8\u05d0\u05e6\u05bc\u05e8</orth> <orth rend="bold" type="trans">n<hi rend="super">e</hi>b\xfbkadne\'tstsar  neb\xfbkadre\'tstsar  neb\xfbkadre\'ts\xf4r</orth> <pron rend="italic">neb-oo-kad-nets-tsar\' neb-oo-kad-rets-tsar\' neb-oo-kad-tsore</pron><lb/> <def><lb/>Of foreign derivation;<lb/> <hi rend="italic">Nebukadnetstsar</hi> (or <hi rend="italic">retstsar</hi> or <hi rend="italic">retstsor</hi>) king of Babylon: - Nebuchadnezzar Nebuchadrezzar.</def> </entryFree>'),
	H5646=(u'<entryFree n="H5646|\u05e2\u05d1    \u05e2\u05d1"> <title>H5646</title> <orth>\u05e2\u05d1    \u05e2\u05d1</orth> <orth rend="bold" type="trans">\u201b\xe2b \u201b\xf4b</orth> <pron rend="italic">awb obe</pron><lb/> <def>From an unused root meaning to <hi rend="italic">cover</hi>; properly equivalent to <ref target="Strong:H5645">H5645</ref>; but used only as an architectural term an <hi rend="italic">architrave</hi> (as <hi rend="italic">shading</hi> the pillars): - thick (beam plant).</def> </entryFree>',u'<entryFree n="H5646|\u05e2\u05d1    \u05e2\u05d1"> <title>H5646</title> <orth>\u05e2\u05d1    \u05e2\u05d1</orth> <orth rend="bold" type="trans">\u201b\xe2b  \u201b\xf4b</orth> <pron rend="italic">awb obe</pron><lb/> <def>From an unused root meaning to <hi rend="italic">cover</hi>; properly equivalent to <ref target="Strong:H5645">H5645</ref>; but used only as an architectural term an <hi rend="italic">architrave</hi> (as <hi rend="italic">shading</hi> the pillars): - thick (beam plant).</def> </entryFree>'),	
)

	
	
old_bad_source_text = dict(
	H0530=(" 530  'emuwnah  em-oo-naw'); or (shortened) >emunah {em-oo-naw'\n\n\n feminine of 529; literally firmness; figuratively security;\n morally fidelity:--faith(-ful, -ly, -ness, (man)), set\n office, stability, steady, truly, truth, verily.\n see HEBREW for 0529",
	" 530  'emuwnah  em-oo-naw'\n); or (shortened) >emunah {em-oo-naw'\n\n\n feminine of 529; literally firmness; figuratively security;\n morally fidelity:--faith(-ful, -ly, -ness, (man)), set\n office, stability, steady, truly, truth, verily.\n see HEBREW for 0529"),
	G3379=(u" 3379  mepote   may'-pot-eh or\n       me pote  may pot'-eh\n\n\n from 3361 and 4218; not ever; also if (or lest) ever (or perhaps):--if\n peradventure, lest (at any time, haply), not at all, whether or not.\n see GREEK for 3361\n see GREEK for 4218",u" 3379  mepote   may'-pot-eh\n or\n       me pote  may pot'-eh\n\n\n from 3361 and 4218; not ever; also if (or lest) ever (or perhaps):--if\n peradventure, lest (at any time, haply), not at all, whether or not.\n see GREEK for 3361\n see GREEK for 4218"),
	G3381=(u" 3381  mepos   may'-pos or\n       me pos  may poce\n\n\n from 3361 and 4458; lest somehow:--lest (by any means, by some means,\n haply, perhaps).\n see GREEK for 3361\n see GREEK for 4458",u" 3381  mepos   may'-pos\n or\n       me pos  may poce\n\n\n from 3361 and 4458; lest somehow:--lest (by any means, by some means,\n haply, perhaps).\n see GREEK for 3361\n see GREEK for 4458"),
	G3387=(u" 3387  metis   may'-tis or\n       me tis  may tis\n\n\n from 3361 and 5100; whether any:--any (sometimes unexpressed except by\n the simple interrogative form of the sentence).\n see GREEK for 3361\n see GREEK for 5100",u" 3387  metis   may'-tis\nor\n       me tis  may tis\n\n\n from 3361 and 5100; whether any:--any (sometimes unexpressed except by\n the simple interrogative form of the sentence).\n see GREEK for 3361\n see GREEK for 5100"),
	G3569=(u" 3569  tanun    tan-oon' or\n       ta nun   tah noon\n\n\n from neuter plural of 3588 and 3568; the things now, i.e.\n (adverbially) at present:--(but) now.\n see GREEK for 3588\n see GREEK for 3568",u" 3569  tanun    tan-oon'\n or\n       ta nun   tah noon\n\n\n from neuter plural of 3588 and 3568; the things now, i.e.\n (adverbially) at present:--(but) now.\n see GREEK for 3588\n see GREEK for 3568"),
	G3627=(u" 3627  oikteiro  oyk-ti'-ro also (in certain tenses) prolonged\n             oiktereo  oyk-ter-eh'-o\n from oiktos (pity); to exercise pity:--have compassion on.",u" 3627  oikteiro  oyk-ti'-ro\n also (in certain tenses) prolonged\n             oiktereo  oyk-ter-eh'-o\n from oiktos (pity); to exercise pity:--have compassion on."),
	G3801=(u" 3801  ho on  kai   ho en  kai   ho erchomenos\n       ho own kahee ho ane kahee ho er-khom'-en-os\n\n\n a phrase combining 3588 with the present participle and imperfect of\n 1510 and the present participle of 2064 by means of 2532; the one\n being and the one that was and the one coming, i.e. the Eternal, as a\n divine epithet of Christ:--which art (is, was), and (which) wast (is,\n was), and art (is) to come (shalt be).\n see GREEK for 1510\n see GREEK for 2532\n see GREEK for 3588\n see GREEK for 2064",u" 3801  ho on kai ho en kai ho erchomenos  ho own kahee ho ane kahee ho er-khom'-en-os\n\n\n a phrase combining 3588 with the present participle and imperfect of\n 1510 and the present participle of 2064 by means of 2532; the one\n being and the one that was and the one coming, i.e. the Eternal, as a\n divine epithet of Christ:--which art (is, was), and (which) wast (is,\n was), and art (is) to come (shalt be).\n see GREEK for 1510\n see GREEK for 2532\n see GREEK for 3588\n see GREEK for 2064"),
	G4486=(u' 4486  rhegnumi  hrayg\'-noo-mee or\n       rhesso    hrace\'-so\n\n\n both prolonged forms of rheko (which appears only in certain forms,\n and is itself probably a strengthened form of agnumi (see in 2608)) to\n "break," "wreck" or "crack", i.e. (especially) to sunder (by\n separation of the parts; 2608 being its intensive (with the\n preposition in composition), and 2352 a shattering to minute\n fragments; but not a reduction to the constituent particles, like\n 3089) or disrupt, lacerate; by implication, to convulse (with spasms);\n figuratively, to give vent to joyful emotions:--break (forth), burst,\n rend, tear.\n see GREEK for 2608\n see GREEK for 2608\n see GREEK for 2352\n see GREEK for 3089',u' 4486  rhegnumi  hrayg\'-noo-mee\n or\n       rhesso    hrace\'-so\n\n\n both prolonged forms of rheko (which appears only in certain forms,\n and is itself probably a strengthened form of agnumi (see in 2608)) to\n "break," "wreck" or "crack", i.e. (especially) to sunder (by\n separation of the parts; 2608 being its intensive (with the\n preposition in composition), and 2352 a shattering to minute\n fragments; but not a reduction to the constituent particles, like\n 3089) or disrupt, lacerate; by implication, to convulse (with spasms);\n figuratively, to give vent to joyful emotions:--break (forth), burst,\n rend, tear.\n see GREEK for 2608\n see GREEK for 2608\n see GREEK for 2352\n see GREEK for 3089'),
	G4766=(u' 4766  stronnumi strone\'-noo-mee,  or simpler\n       stronnuo  strone-noo\'-o, prolongation from a still simpler\n       stroo     stro\'-o, (used only as an alternate in certain tenses)\n\n\n (probably akin to 4731 through the idea of positing); to "strew," i.e.\n spread (as a carpet or couch):--make bed, furnish, spread, strew.\n see GREEK for 4731',u' 4766  stronnumi  strone\'-noo-mee,  or simpler\n       stronnuo  strone-noo\'-o, prolongation from a still simpler\n       stroo     stro\'-o, (used only as an alternate in certain tenses)\n\n\n (probably akin to 4731 through the idea of positing); to "strew," i.e.\n spread (as a carpet or couch):--make bed, furnish, spread, strew.\n see GREEK for 4731'),
	H1782=(u" 1782  dayan ,  dah-yawn'\n\n\n (Aramaic) corresp. to 1781:--judge.\n see HEBREW for 01781",u" 1782  dayan  dah-yawn'\n\n\n (Aramaic) corresp. to 1781:--judge.\n see HEBREW for 01781"),
	H2869=(u' 2869  tab ,  tawb\n\n\n (Aramaic) from 2868; the same as 2896; good:--fine, good.\n see HEBREW for 02868\n see HEBREW for 02896',u' 2869  tab  tawb\n\n\n (Aramaic) from 2868; the same as 2896; good:--fine, good.\n see HEBREW for 02868\n see HEBREW for 02896'),	
	H3248=(u" 3248  ycuwdah,  yes-oo-daw'\n\n\n feminine of 3246; a foundation:--foundation.\n see HEBREW for 03246",u" 3248  ycuwdah  yes-oo-daw'\n\n\n feminine of 3246; a foundation:--foundation.\n see HEBREW for 03246"),	
	H3253=(u" 3253  Yicmakyahuw,  yis-mak-yaw-hoo'\n\n\n from 5564 and 3050; Jah will sustain; Jismakjah, an\n Israelite:--Ismachiah.\n see HEBREW for 05564\n see HEBREW for 03050",u" 3253  Yicmakyahuw  yis-mak-yaw-hoo'\n\n\n from 5564 and 3050; Jah will sustain; Jismakjah, an\n Israelite:--Ismachiah.\n see HEBREW for 05564\n see HEBREW for 03050"),
	H3272=(u" 3272  y`at ,  yeh-at'\n\n\n (Aramaic) corresponding to 3289; to counsel; reflexively, to\n consult:--counsellor, consult together.\n see HEBREW for 03289",u" 3272  y`at  yeh-at'\n\n\n (Aramaic) corresponding to 3289; to counsel; reflexively, to\n consult:--counsellor, consult together.\n see HEBREW for 03289"),	
	H5516=(u" 5516  Ciycra';  see-ser-aw'\n\n\n of uncertain derivation; Sisera, the name of a Canaanitish\n king and of one of the Nethinim:--Sisera.",u" 5516  Ciycra'  see-ser-aw'\n\n\n of uncertain derivation; Sisera, the name of a Canaanitish\n king and of one of the Nethinim:--Sisera."),
	H5874=(u" 5874  `Eyn-Do'r,  ane-dore'\n\n\n or mEyn Dowr {ane dore}; or  Eyn-Dor {ane-dore'}; from 5869\n and 1755; fountain of dwelling; En-Dor, a place in\n Palestine:--En-dor.\n see HEBREW for 01755",u" 5874  `Eyn-Do'r  ane-dore'\n\n\n or mEyn Dowr {ane dore}; or  Eyn-Dor {ane-dore'}; from 5869\n and 1755; fountain of dwelling; En-Dor, a place in\n Palestine:--En-dor.\n see HEBREW for 01755"),
	H6074=(u" 6074  `ophiy ,  of-ee'\n\n\n (Aramaic) corresponding to 6073; a twig; bough, i.e.\n (collectively) foliage:--leaves.\n see HEBREW for 06073",u" 6074  `ophiy  of-ee'\n\n\n (Aramaic) corresponding to 6073; a twig; bough, i.e.\n (collectively) foliage:--leaves.\n see HEBREW for 06073"),
	H6088=(u" 6088  `atsab ,  ats-ab'\n\n\n (Aramaic) corresponding to 6087; to afflict:--lamentable.\n see HEBREW for 06087",u" 6088  `atsab  ats-ab'\n\n\n (Aramaic) corresponding to 6087; to afflict:--lamentable.\n see HEBREW for 06087"),
	H6221=(u" 6221  `Asiy'el,  as-ee-ale'\n\n\n from 6213 and 410; made of God; Asiel, an Israelite:--Asiel.\n see HEBREW for 06213\n see HEBREW for 0410",u" 6221  `Asiy'el  as-ee-ale'\n\n\n from 6213 and 410; made of God; Asiel, an Israelite:--Asiel.\n see HEBREW for 06213\n see HEBREW for 0410"),
	H6236=(u" 6236  `asar ,  as-ar'\n\n\n (Aramaic) masculine aasrah (Aramaic). {as-raw'};\n corresponding to 6235; ten:--ten, + twelve.\n see HEBREW for 06235",u" 6236  `asar   as-ar'\n\n\n (Aramaic) masculine aasrah (Aramaic). {as-raw'};\n corresponding to 6235; ten:--ten, + twelve.\n see HEBREW for 06235"),
	H6913=(u" 6913  qeber,  keh'-ber\n\n\n or (feminine) qibrah {kib-raw'}; from 6912; a\n sepulchre:--burying place, grave, sepulchre.\n see HEBREW for 06912",u" 6913  qeber  keh'-ber\n\n\n or (feminine) qibrah {kib-raw'}; from 6912; a\n sepulchre:--burying place, grave, sepulchre.\n see HEBREW for 06912"),
	H6959=(u" 6959  qowba`  ko'-bah or ko-bah'\n\n\n a form collateral to 3553; a helmet:--helmet.\n see HEBREW for 03553",u" 6959  qowba`  ko'-bah\n or ko-bah'\n\n\n a form collateral to 3553; a helmet:--helmet.\n see HEBREW for 03553"),
	H5967=(u" 5967  `ala` ;  al-ah'\n\n\n (Aramaic) corresponding to 6763; a rib:--rib.\n see HEBREW for 06763",u" 5967  `ala`  al-ah'\n\n\n (Aramaic) corresponding to 6763; a rib:--rib.\n see HEBREW for 06763"),
	
)

OK_ones = (
	"H0033", "H0062", "H0358", "H0634", "H0885", "H1019",
	"H2657", "H2693", "H2701", "H3304", "H3430", "H3565", "H5419",
	"H5875", "H6100", "H6152", "H6364", "H7256", "H7610",
)
	

# check that we can pre-increment as we know the first entry is bad...
assert module.getKeyText()[0] not in "GH", "First entry wasn't bad?!? :("

def read_from_strongs_real_greek():
	while greek.Error() == '\x00':
		entry = greek.getRawEntry().decode("utf8")
		key = "G" + greek.getKeyText()[1:]
		if entry == "" and key.startswith("G56"):
			break
		
		if entry.startswith("@LINK"): continue
		m = srg_unused.match(entry)
		if m: 
			greek.increment()
			continue

		if key in bad_source_text:
			if entry != bad_source_text[key][0]:
				print "AAARGGHHH - expected bad but wasn't", key

			a, b = bad_source_text[key]
			if a == b:
				print "AARRGGHHH - forgot to fix a against b", key

			entry = bad_source_text[key][1]

		m = srg_regex.match(entry)
		if not m:
			print "Did not match on entry", key
			greek.increment()
			missed.append((key, entry))
			continue
		
		orig, trans, pron = m.group(1, 2, 3)
		pron = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', pron)
		trans = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', trans)
		orig = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', orig)
	
		# multiple entries, split with , not space
		count = trans.count("  ")
	
		# hmm, this isn't quite so easy... :(
		if count and False:
			# pronunciation can have only one for more than one form...
			# so only check whether there are more parts, not fewer
			pron, cnt = re.subn("\s+", ", ", pron)
			if cnt > count: 
				print "Pron Counts wrong", key
			
			trans, cnt = re.subn("\s+", ", ", trans)
			if cnt > count:
				print "Trans Counts wrong", key
			
			
			#if pron.count(" ") > count or orig.count(" ") > count:
			#	if " -" not in pron:
			#else:
			trans = trans.replace("  ", ", ")	
			
			#pron = pron.replace(" ", ", ")
			#orig = orig.replace(" ", ", ")
		
		#pronunciation_module.add_entry(key, pron)
		#transliteration_module.add_entry(key, trans)
		orig_module.add_entry(key, orig)
		greek.increment()
		


def gather_from_strong():
	# start from here, as StrongsRealGreek for me tails off there.
	module.KeyText("G5610")
	while module.increment() or module.Error() == '\x00':
		entry = module.getRawEntry().decode("utf8")
		key = module.getKeyText()	
		if key in bad_source_text:
			if entry != bad_source_text[key][0]:
				print "AAARGGHHH - expected bad but wasn't", key

			a, b = bad_source_text[key]
			if a == b:
				print "AARRGGHHH - forgot to fix a against b"

			entry = bad_source_text[key][1]
		
		if entry.startswith("@LINK"): continue
		m = regex.match(entry)
		if not m:
			print "Did not match on entry", key
			continue
		
		orig, trans, pron = m.group(2, 3, 4)
		pron = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', pron)
		trans = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', trans)
		orig = re.sub('<hi rend="super">([^>]*)</hi>', r'<sup>\1</sup>', orig)
	
		# multiple entries, split with , not space
		count = trans.count("  ")
		orig_count = orig.count("    ")
		if orig_count != count:
			print key, orig_count, count, "AARGGGHHH"
			missed.append((key, entry))

		orig = orig.split("    ")[0]
		trans = trans.split("  ")[0]
		
		
	
		# hmm, this isn't quite so easy... :(
		# we'll ignore this for now
		if count and False:
			# pronunciation can have only one for more than one form...
			# so only check whether there are more parts, not fewer
			pron, cnt = re.subn("\s+", ", ", pron)
			if cnt > count: 
				print "Pron Counts wrong", key
			
			trans, cnt = re.subn("\s+", ", ", trans)
			if cnt > count:
				print "Trans Counts wrong", key
			
			
			#if pron.count(" ") > count or orig.count(" ") > count:
			#	if " -" not in pron:
			#else:
			trans = trans.replace("  ", ", ")	
			
			#pron = pron.replace(" ", ", ")
			#orig = orig.replace(" ", ", ")
		
		#pronunciation_module.add_entry(key, pron)
		#transliteration_module.add_entry(key, trans)
		orig_module.add_entry(key, orig)

def gather_from_old_strongs(module, prefix):
	# start from here, as StrongsRealGreek for me tails off there.
	#module.KeyText("G5610")
	while module.increment() or module.Error() == '\x00':
		entry = module.getRawEntry().decode("utf8")
		key = prefix + module.getKeyText()[1:]
		m = old_strongs_unused.match(entry)
		if m:
			continue
		
		if key in old_bad_source_text:
			if entry != old_bad_source_text[key][0]:
				print "AAARGGHHH - expected bad but wasn't", key

			a, b = old_bad_source_text[key]
			if a == b:
				#print "AARRGGHHH - forgot to fix a against b"
				print "AARRGGHHH - forgot to fix a against b", key
				

			entry = old_bad_source_text[key][1]
		
		#if entry.startswith("@LINK"): continue
		m = old_strongs_re.match(entry)
		if not m:
			print "Did not match on entry", key, repr(entry)
			continue
		
		text = m.group(1)
		splits = re.split("  +", text)
		if len(splits) != 2:
			print "BAD BAD BAD", key, `entry`
			continue

		elif splits[0].count(" ") != splits[1].count(" ") \
			and key not in OK_ones:
			print "AARRGGHH - wasn't even!!!!! :(", key, `text`
			missed.append((key, entry))

			continue

		trans = splits[0]
		pron = splits[1]
		
		pronunciation_module.add_entry(key, pron)
		transliteration_module.add_entry(key, trans)

gather_from_old_strongs(old_greek, "G")
gather_from_old_strongs(old_hebrew, "H")
read_from_strongs_real_greek()
gather_from_strong()
print "Done in %.2f seconds" % (time.time() - t)


# Pron Counts wrong G3367
# Pron Counts wrong G3379
# Trans Counts wrong G3379
# Pron Counts wrong G3381
# Trans Counts wrong G3381
# Pron Counts wrong G3387
# Trans Counts wrong G3387
# Pron Counts wrong G3569
# Trans Counts wrong G3569
# Trans Counts wrong G3753
# Pron Counts wrong G5204

